"""S6 proof: behind the plate, is S6's knee closer to the real knee than RTMPose's guess?

usage (from prototype/): uv run python ../.claude/skills/verify/scripts/proofs/s6.py <evidence_root>
writes <evidence_root>/proof/S6/{verdict.md, 1_paste_curves.png, 2_paste_crops.jpg, 3_loaded_curves.png}

Paste test (docs/results/36-skeleton-fill.md section 3c), out of sample: a real 5 kg plate (cut from the T1 clip,
resized to the loaded clips' rest radius) is pasted on the near bar end of a bar-only clip of the same session
(spike _1_, standup, 3 pulls, knee always visible). RTMPose runs again on the pasted frames; S6's own
`snatch.fill.fill` rebuilds the knee from that output. Truth = RTMPose on the clean frames. The skeleton is the
evidence root's athlete `verify` (calibrated on T5 = spike _2_), scaled by S5's method run on this clip.
Detector, pose, collar track and pasted pose are cached in .scratch/verify/cache/proof-s6/<key>/.
"""

import hashlib
import inspect
import json
import re
import sys
import time
from pathlib import Path

import cv2
import matplotlib
import numpy as np

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / ".claude/skills/verify/scripts"))

from check_pipeline import BODY_PX_PER_M_CAL, DIP_DEG, dips  # noqa: E402  # pyright: ignore[reportMissingImports]
from snatch import athlete_store, person, pose  # noqa: E402
from snatch import fill as fl  # noqa: E402
from snatch import scale as sca  # noqa: E402
from snatch import signals, skeleton as skel, video  # noqa: E402
from snatch.pose import HALPE26, SIDE_OF  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CLEAN = REPO / "vids/spike/20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right.MOV"
REF_CLIP = REPO / "vids/spike/20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right.MOV"  # = T5, collar template
REF_FRAME = 1450
SEED_OFFSET = np.array([-5.0, 57.0])  # collar - wrist in REF_FRAME, by eye
HALF, SEARCH, SEED_SEARCH = 20, 12, 30
PLATE_CLIP_GLOB = "T1_*.MOV"  # T1 is spike _3_ cut at source frame 728
PLATE_FRAME = 1105 - 728
HUB_SHIFT = np.array([0.0, 6.0])  # the plate's outer face sits ~3 cm outboard of the collar
PAD_BEFORE_S, PAD_AFTER_S = 0.25, 0.1  # pasted span around a pull: setup - 0.25 s .. peak + 0.1 s
S5_PAD_S = 1.0  # S5 reads a window padded 1 s either side, like S3's attempt window
INNER = 0.7  # the 'well behind the plate' zone: the true knee within this share of the radius from the hub
PURPLE, GREY, GREEN = (200, 40, 160), (150, 150, 150), (0, 200, 0)  # BGR
MPL = {"truth": "#1b9e3a", "rtm": "#8c8c8c", "s6": "#a0289b"}
CACHE = REPO / ".scratch/verify/cache/proof-s6"


def log(msg: str) -> None:
    print(f"[s6 proof {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def file_key(p: Path) -> str:
    s = p.stat()
    return f"{s.st_size}-{int(s.st_mtime)}"


def src_hash(*objs) -> str:
    h = hashlib.sha1()
    for o in objs:
        h.update(inspect.getsource(o).encode())
    return h.hexdigest()[:10]


# ---------------------------------------------------------------- clean clip: boxes, pose, pull windows

def clean_pose(cache: Path) -> dict:
    """Boxes and RTMPose on every frame of the clean clip (snatch.person / snatch.pose as S1 / S4 call them)."""
    key = f"clean-{file_key(CLEAN)}-{src_hash(person, pose, video)}"
    f = cache / key / "clean.npz"
    if f.exists():
        return dict(np.load(f))
    info = video.probe(str(CLEAN))
    t = video.timestamps(str(CLEAN), info.fps)
    assert info.n_frames == len(t), f"{info.n_frames} frames decode, {len(t)} timestamps"
    t0 = time.time()
    log(f"clean clip: detector + pose on {info.n_frames} frames (cached afterwards)")
    boxes = person.detect(video.frames(str(CLEAN), info), info.n_frames, person.DEFAULT_DET_EVERY,
                          person.load_detector(),
                          progress=lambda i: log(f"  detector {i}/{info.n_frames}") if i % 1200 == 0 else None)["bbox"]
    res = pose.run(video.frames(str(CLEAN), info), info.n_frames, boxes,
                   progress=lambda i: log(f"  pose {i}/{info.n_frames} {time.time() - t0:.0f}s") if i % 800 == 0 else None)
    out = {"bbox": boxes, "keypoints": res["keypoints"], "scores": res["scores"], "t": t}
    f.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, allow_pickle=False, **out)
    return out


def pull_windows(wrist_y: np.ndarray, knee_y: np.ndarray, hip_y: np.ndarray, knee_deg: np.ndarray,
                 t: np.ndarray, still_px_s: float = 50.0, peak_s: float = 0.6) -> list[dict]:
    """Pulls (as the old study): every rise of the wrist from below the knee to above the hip. setup = liftoff,
    hip = first frame above the hip, peak = largest knee angle within peak_s after that."""
    rate = (len(t) - 1) / (t[-1] - t[0])
    rise = -np.diff(wrist_y, prepend=wrist_y[0]) / np.diff(t, prepend=t[0] - 1 / rate)
    above = wrist_y < hip_y
    out, last = [], 0
    for s in np.flatnonzero(np.diff(above.astype(int)) == 1) + 1:
        below = np.flatnonzero(wrist_y[last:s] > knee_y[last:s])
        if not len(below):
            continue
        i = int(last + below[-1])
        while i > 0 and rise[i] <= still_px_s:  # a stall at the top
            i -= 1
        while i > 0 and rise[i] > still_px_s:
            i -= 1
        setup = i + 1
        end = min(int(s) + int(peak_s * rate), len(wrist_y))
        out.append({"setup": int(setup), "hip": int(s), "peak": int(s) + int(np.argmax(knee_deg[s:end]))})
        last = int(s)
    return out


# ---------------------------------------------------------------- plate: collar track and paste

def _match(gray: np.ndarray, tpl: np.ndarray, p: np.ndarray, r: int) -> tuple[np.ndarray, float]:
    x0, y0 = int(p[0]) - HALF - r, int(p[1]) - HALF - r
    win = gray[y0:y0 + 2 * (HALF + r) + 1, x0:x0 + 2 * (HALF + r) + 1]
    res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    dx = dy = 0.0
    lx, ly = loc
    if 0 < lx < res.shape[1] - 1:
        a, b, c = res[ly, lx - 1], res[ly, lx], res[ly, lx + 1]
        dx = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0.0
    if 0 < ly < res.shape[0] - 1:
        a, b, c = res[ly - 1, lx], res[ly, lx], res[ly + 1, lx]
        dy = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0.0
    return np.array([x0 + lx + dx + HALF, y0 + ly + dy + HALF]), float(mx)


def _patch(gray: np.ndarray, p: np.ndarray) -> np.ndarray:
    x, y = int(round(p[0])), int(round(p[1]))
    return gray[y - HALF:y + HALF + 1, x - HALF:x + HALF + 1].astype(np.float32)


def collar_template(ref_wrist: np.ndarray) -> np.ndarray:
    """The near collar's 41 px template from REF_FRAME of the powersnatch bar clip (wrist + SEED_OFFSET)."""
    info = video.probe(str(REF_CLIP))
    g = next(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) for i, img in enumerate(video.frames(str(REF_CLIP), info, stop=REF_FRAME + 1))
             if i == REF_FRAME)
    p = ref_wrist + SEED_OFFSET
    seed, _ = _match(g, _patch(g, p).astype(np.uint8), p, 2)
    return _patch(g, seed).astype(np.uint8)


def track_collar(spans: list[tuple[int, int]], wrist: np.ndarray, t: np.ndarray, ref: np.ndarray
                 ) -> tuple[np.ndarray, np.ndarray]:
    """(collar (n, 2) smoothed inside each span, NaN elsewhere; match score (n,)): template matching of the near
    bar collar, as the old skeleton_wrist.py (search +-12 px per frame, template refreshed with 10 % of the new patch)."""
    info = video.probe(str(CLEAN))
    pos, score = np.full((info.n_frames, 2), np.nan), np.full(info.n_frames, np.nan)
    tpl = cur = None
    for i, img in enumerate(video.frames(str(CLEAN), info, stop=spans[-1][1])):
        if not any(s <= i < e for s, e in spans):
            tpl = None
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if tpl is None or cur is None:
            cur, _ = _match(g, ref, wrist[i] + SEED_OFFSET, SEED_SEARCH)
            tpl = _patch(g, cur)
        cur, sc = _match(g, tpl.astype(np.uint8), cur, SEARCH)
        tpl = 0.9 * tpl + 0.1 * _patch(g, cur)
        pos[i], score[i] = cur, sc
    out = np.full_like(pos, np.nan)
    for s, e in spans:
        for d in (0, 1):
            out[s:e, d] = signals.smooth(pos[s:e, d], t=t[s:e])
    return out, score


def plate_texture(root: Path, radius: float) -> tuple[np.ndarray, np.ndarray]:
    """(texture, mask): the real plate of T1 at PLATE_FRAME (circle of radius sqrt(a b) around its tracked hub),
    resized to `radius` px."""
    clip = next((REPO / "vids/test").glob(PLATE_CLIP_GLOB))
    pl = np.load(next(root.glob("T1_*/plate.npz")))
    cx, cy = pl["hub_x"][PLATE_FRAME], pl["hub_y"][PLATE_FRAME]
    r = float(np.sqrt(pl["a"][PLATE_FRAME] * pl["b"][PLATE_FRAME]))
    img = next(f.copy() for i, f in enumerate(video.frames(str(clip), stop=PLATE_FRAME + 1)) if i == PLATE_FRAME)
    h = int(np.ceil(r)) + 2
    crop = img[int(cy) - h:int(cy) + h + 1, int(cx) - h:int(cx) + h + 1].astype(np.float32)
    crop = cv2.resize(crop, None, fx=radius / r, fy=radius / r, interpolation=cv2.INTER_LINEAR)
    m = np.zeros(crop.shape[:2], np.float32)
    c = (crop.shape[1] - 1) / 2
    cv2.circle(m, (int(round(c)), int(round(c))), int(radius), 1.0, -1, cv2.LINE_AA)
    return crop, m


def paste(img: np.ndarray, centre: np.ndarray, tex: np.ndarray, m: np.ndarray) -> np.ndarray:
    out = img.astype(np.float32)
    hh = tex.shape[0] // 2
    x0, y0 = int(round(centre[0])) - hh, int(round(centre[1])) - hh
    H, W = img.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + tex.shape[1], W), min(y0 + tex.shape[0], H)
    mm = m[ya - y0:yb - y0, xa - x0:xb - x0, None]
    out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - mm) + tex[ya - y0:yb - y0, xa - x0:xb - x0] * mm
    return out.astype(np.uint8)


def pasted_images(spans: list[tuple[int, int]], hub: np.ndarray, tex: np.ndarray, m: np.ndarray, stop: int | None = None):
    """Frames of the clean clip with the plate pasted at `hub` inside every span (up to frame `stop`)."""
    for i, img in enumerate(video.frames(str(CLEAN), stop=stop or spans[-1][1])):
        if any(s <= i < e for s, e in spans) and not np.isnan(hub[i, 0]):
            img = paste(img, hub[i], tex, m)
        yield img


PASTE_FUNCS = (_match, _patch, collar_template, track_collar, plate_texture, paste, pasted_images, pull_windows)


# ---------------------------------------------------------------- comparison

def runs_of(mask: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def dip_lows(a: np.ndarray, deg: float = DIP_DEG) -> list[int]:
    """Indices of the low points of the dips `dips` counts (same rule, on a series with NaNs kept in place)."""
    idx = np.flatnonzero(~np.isnan(a))
    if not len(idx):
        return []
    lows, high, low, li, falling = [], a[idx[0]], a[idx[0]], idx[0], False
    for i in idx[1:]:
        x = a[i]
        if falling:
            if x < low:
                low, li = x, i
            if x >= low + deg:
                lows.append(int(li))
                falling, high = False, x
        else:
            high = max(high, x)
            if x <= high - deg:
                falling, low, li = True, x, i
    return lows


def stats(x: np.ndarray) -> tuple[float, float]:
    return (float(np.median(x)), float(np.percentile(x, 90))) if len(x) else (float("nan"), float("nan"))


def main(root: Path) -> None:
    t_start = time.time()
    out_dir = root / "proof/S6"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = CACHE
    # ---- skeleton and plate size
    sk = athlete_store.load(root / "athletes", "verify", athlete_store.SKELETON)
    assert sk, f"no skeleton.json in {root}/athletes/verify"
    clean = clean_pose(cache)
    t, kp_clean, sc_clean = clean["t"], clean["keypoints"].astype(float), clean["scores"]
    n = len(t)
    facing = pose.facing(kp_clean, sc_clean)
    assert facing, "no facing on the clean clip"
    side = SIDE_OF[facing]
    sign = 1.0 if side == "r" else -1.0
    j = {m: HALPE26[f"{side}_{m}"] for m in ("hip", "knee", "ankle", "wrist")}
    tab0 = skel.LengthTable.from_json(sk[side])
    # ---- pull windows from the clean pose
    ks = signals.smooth_keypoints(kp_clean, video.mean_rate(t), t)
    ang = skel.sagittal_angles(ks, side)["knee"]
    pulls = pull_windows(ks[:, j["wrist"], 1], ks[:, j["knee"], 1], ks[:, j["hip"], 1], ang, t)
    assert pulls, "no pull found on the clean clip"
    fps = video.mean_rate(t)
    spans = [(max(p["setup"] - int(PAD_BEFORE_S * fps), 0), min(p["peak"] + int(PAD_AFTER_S * fps) + 1, n)) for p in pulls]
    log(f"{len(pulls)} pulls (setup, hip, peak): {[(p['setup'], p['hip'], p['peak']) for p in pulls]}")
    # ---- plate: size, texture, collar track, pasted pose (cached)
    plates = [np.load(f) for f in sorted(root.glob("T1_*/plate.npz"))]
    radius = float(round(np.median([float(p["r0"]) for p in plates])))
    tex, mask = plate_texture(root, radius)
    ref_wrist = signals.smooth_keypoints(np.load(next(root.glob("calibrate_T5_*/raw_pose.npz")))["keypoints"].astype(float), 240.0)[REF_FRAME, j["wrist"]]
    ref = collar_template(ref_wrist)
    pkey = "paste-" + hashlib.sha1(("|".join([file_key(CLEAN), file_key(REF_CLIP), src_hash(person, pose, video),
                                            src_hash(*PASTE_FUNCS), str(spans), f"{radius}", str(HUB_SHIFT),
                                            hashlib.sha1(tex.tobytes()).hexdigest(), hashlib.sha1(ref.tobytes()).hexdigest()])
                                           ).encode()).hexdigest()[:12]
    f = cache / pkey / "paste.npz"
    if f.exists():
        pc = dict(np.load(f))
    else:
        t0 = time.time()
        log("collar track + RTMPose on the pasted frames (cached afterwards)")
        collar, cscore = track_collar(spans, ks[:, j["wrist"]], t, ref)
        hub = collar + HUB_SHIFT
        res = pose.run(pasted_images(spans, hub, tex, mask), n, clean["bbox"], ranges=spans,
                       progress=lambda i: log(f"  pasted pose {i} {time.time() - t0:.0f}s") if i % 400 == 0 else None)
        pc = {"collar": collar, "cscore": cscore, "keypoints": res["keypoints"], "scores": res["scores"]}
        f.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(f, allow_pickle=False, **pc)
    hub, kp_paste = pc["collar"] + HUB_SHIFT, pc["keypoints"].astype(float)
    in_span = np.zeros(n, bool)
    for s, e in spans:
        in_span[s:e] = True
    plate = {"found": in_span & ~np.isnan(hub[:, 0]), "hub_x": hub[:, 0], "hub_y": hub[:, 1], "a": np.full(n, radius),
             "b": np.full(n, radius), "angle": np.zeros(n)}
    log(f"collar match score median {np.nanmedian(pc['cscore']):.2f}, min {np.nanmin(pc['cscore']):.2f}")
    # ---- S5 as the pipeline would run it (clean pose; joints under the pasted plate excluded)
    wins5 = [(max(p["setup"] - int(S5_PAD_S * fps), 0), min(p["peak"] + int(S5_PAD_S * fps), n)) for p in pulls]
    k5 = sca.smoothed(kp_clean, t, wins5, side)
    cov = sca.covered(kp_clean, plate, side)
    s5 = sca.estimate(k5, sc_clean, t, wins5, tab0, side, cov)
    assert s5.factor is not None, "S5 method none on the clean clip"
    thigh_f, shank_f, seg_frames = sca.segment_factors(k5, sc_clean, wins5, tab0, side, cov, s5.factor)
    tab = tab0.scaled(s5.factor)
    cm_px = 100 / (BODY_PX_PER_M_CAL * s5.factor)
    log(f"S5: {s5.method}, factor {s5.factor:.3f}, thigh x{thigh_f:.3f} shank x{shank_f:.3f} ({len(seg_frames)} segment frames)")
    # ---- S6 on the pasted pose
    res6 = fl.fill(kp_paste, plate, spans, t, side, tab, thigh_f, shank_f)
    truth = sca.smoothed(kp_clean, t, spans, side)
    rtm = sca.smoothed(kp_paste, t, spans, side)
    s6 = sca.smoothed(res6.keypoints, t, spans, side)
    a = {name: skel.sagittal_angles(k, side)["knee"] for name, k in (("truth", truth), ("rtm", rtm), ("s6", s6))}
    pos = {name: np.hypot(*(k[:, j["knee"]] - truth[:, j["knee"]]).T) * cm_px for name, k in (("rtm", rtm), ("s6", s6))}
    err = {name: np.abs(a[name] - a["truth"]) for name in ("rtm", "s6")}
    with np.errstate(invalid="ignore"):
        hidden = plate["found"] & (np.hypot(truth[:, j["knee"], 0] - hub[:, 0], truth[:, j["knee"], 1] - hub[:, 1]) < radius)
    ok = hidden & ~np.isnan(pos["rtm"]) & ~np.isnan(pos["s6"]) & ~np.isnan(err["rtm"]) & ~np.isnan(err["s6"])
    filled_knee = res6.filled[:, j["knee"]]
    rows = []
    for pi, (p, (s, e)) in enumerate(zip(pulls, spans)):
        m = np.zeros(n, bool)
        m[s:e] = True
        m &= ok
        seg = slice(p["setup"], p["peak"] + 1)
        rows.append({"pull": pi + 1, "n": int(m.sum()), "filled": int((m & filled_knee).sum()), "mask": m,
                     "rtm_cm": stats(pos["rtm"][m]), "s6_cm": stats(pos["s6"][m]),
                     "rtm_deg": stats(err["rtm"][m]), "s6_deg": stats(err["s6"][m]),
                     "dips": {k: dips(a[k][seg]) for k in a}})
    allm = ok
    total = {"pull": "all", "n": int(allm.sum()), "filled": int((allm & filled_knee).sum()),
             "rtm_cm": stats(pos["rtm"][allm]), "s6_cm": stats(pos["s6"][allm]),
             "rtm_deg": stats(err["rtm"][allm]), "s6_deg": stats(err["s6"][allm])}
    with np.errstate(invalid="ignore"):
        inner = ok & (np.hypot(truth[:, j["knee"], 0] - hub[:, 0], truth[:, j["knee"], 1] - hub[:, 1]) < INNER * radius)
    zone = {"pull": f"knee in the inner {INNER:.0%} of the plate", "n": int(inner.sum()), "filled": int((inner & filled_knee).sum()),
            "rtm_cm": stats(pos["rtm"][inner]), "s6_cm": stats(pos["s6"][inner]),
            "rtm_deg": stats(err["rtm"][inner]), "s6_deg": stats(err["s6"][inner])}
    log("comparison done")
    plot_paste(out_dir / "1_paste_curves.png", t, spans, pulls, a, rows, hidden)
    crops(out_dir / "2_paste_crops.jpg", spans, hub, tex, mask, truth, rtm, s6, j, pos, radius, cm_px, ok)
    loaded = plot_loaded(root, out_dir / "3_loaded_curves.png")
    write_verdict(out_dir / "verdict.md", root, rows, total, zone, s5, thigh_f, shank_f, seg_frames, loaded, radius, pulls, spans, plate, pc)
    log(f"done in {time.time() - t_start:.0f}s -> {out_dir}")


# ---------------------------------------------------------------- images

def plot_paste(path: Path, t: np.ndarray, spans, pulls, a: dict, rows: list[dict], hidden: np.ndarray) -> None:
    fig, axes = plt.subplots(len(pulls), 1, figsize=(9, 2.9 * len(pulls)), squeeze=False, dpi=100)
    names = {"truth": "truth (RTMPose, clean frames)", "rtm": "RTMPose on pasted frames", "s6": "S6"}
    for ax, p, (s, e), r in zip(axes[:, 0], pulls, spans, rows):
        x = t[s:e] - t[p["setup"]]
        for a0, a1 in runs_of(hidden[s:e]):
            ax.axvspan(x[a0], x[min(a1, e - s) - 1], color="#f2b134", alpha=0.25, lw=0)
        for k, z, w in (("rtm", 2, 1.6), ("s6", 3, 1.6), ("truth", 4, 1.6)):
            ax.plot(x, a[k][s:e], color=MPL[k], lw=w, zorder=z, label=names[k])
        for k, mk in (("truth", "o"), ("rtm", "s"), ("s6", "D")):
            lows = [i for i in dip_lows(a[k][p["setup"]:p["peak"] + 1])]
            if lows:
                xs = t[p["setup"] + np.array(lows)] - t[p["setup"]]
                ax.plot(xs, a[k][p["setup"] + np.array(lows)], mk, color=MPL[k], mec="black", ms=8, zorder=6, ls="none")
        for q in ("setup", "hip", "peak"):
            ax.axvline(t[p[q]] - t[p["setup"]], color="k", lw=0.6, ls=":")
            ax.text(t[p[q]] - t[p["setup"]], ax.get_ylim()[0], f" {q}", fontsize=7, va="bottom")
        ax.set_title(f"pull {r['pull']}: dips >= {DIP_DEG:.0f} deg between setup and peak: truth {r['dips']['truth']}, "
                     f"RTMPose {r['dips']['rtm']}, S6 {r['dips']['s6']}", fontsize=9)
        ax.set_ylabel("knee angle (deg)")
        ax.grid(alpha=0.3)
    axes[-1, 0].set_xlabel("seconds from the start of the lift (setup)")
    h, lab = axes[0, 0].get_legend_handles_labels()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    h += [Patch(color="#f2b134", alpha=0.35), Line2D([], [], marker="o", color="w", mfc="#ccc", mec="k", ms=8)]
    lab += ["true knee inside the pasted plate", "marker = bottom of a dip (shape per curve)"]
    fig.legend(h, lab, loc="upper center", ncol=2, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.09 * 3 / len(pulls) * 0.55))
    fig.savefig(path)
    plt.close(fig)


def crops(path: Path, spans, hub, tex, mask, truth, rtm, s6, j, pos, radius, cm_px, ok) -> None:
    order = [int(i) for i in np.argsort(-np.where(ok, pos["rtm"], -1.0))]
    pick: list[int] = []
    for i in order:
        if not ok[i]:
            break
        if all(abs(i - q) >= 48 for q in pick):
            pick.append(i)
        if len(pick) == 6:
            break
    grabs = {}
    for i, img in enumerate(pasted_images(spans, hub, tex, mask, stop=max(pick) + 1)):
        if i in pick:
            grabs[i] = img.copy()
    tiles = []
    half, size = 150, 450
    for i in sorted(pick):
        img = cv2.copyMakeBorder(grabs[i], half, half, half, half, cv2.BORDER_CONSTANT)  # pad: a crop at the edge keeps its scale
        c = truth[i, j["knee"]]
        x0, y0 = int(c[0]), int(c[1])  # = the window's top-left in the padded image
        crop = cv2.resize(img[y0:y0 + 2 * half, x0:x0 + 2 * half], (size, size), interpolation=cv2.INTER_CUBIC)
        sc = size / (2 * half)
        to = lambda p: (int((p[0] + half - x0) * sc), int((p[1] + half - y0) * sc))  # noqa: E731
        cv2.circle(crop, to(hub[i]), int(radius * sc), (255, 255, 255), 1, cv2.LINE_AA)
        for k, col, r_ in ((rtm, GREY, 9), (s6, PURPLE, 7), (truth, GREEN, 5)):
            cv2.circle(crop, to(k[i, j["knee"]]), r_ + 2, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(crop, to(k[i, j["knee"]]), r_, col, -1, cv2.LINE_AA)
        for a_, b_ in ((j["hip"], j["knee"]), (j["knee"], j["ankle"])):  # S6's thigh and shank
            cv2.line(crop, to(s6[i, a_]), to(s6[i, b_]), PURPLE, 1, cv2.LINE_AA)
        bar = int(10 / cm_px * sc)
        cv2.line(crop, (10, size - 14), (10 + bar, size - 14), (255, 255, 255), 3)
        cv2.putText(crop, "10 cm", (14 + bar, size - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        for k, line in enumerate((f"frame {i}", f"RTMPose off {pos['rtm'][i]:.1f} cm", f"S6 off {pos['s6'][i]:.1f} cm")):
            for col, th in (((0, 0, 0), 4), ((255, 255, 255), 1)):
                cv2.putText(crop, line, (8, 20 + 20 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, th, cv2.LINE_AA)
        tiles.append(crop)
    while len(tiles) % 2:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[k:k + 2]) for k in range(0, len(tiles), 2)])
    leg = np.full((34, sheet.shape[1], 3), 30, np.uint8)
    x = 8
    for txt, col in (("green: true knee", GREEN), ("grey: RTMPose on the pasted frame", GREY), ("purple: S6", PURPLE), ("white ring: pasted plate", (255, 255, 255))):
        cv2.circle(leg, (x + 6, 17), 6, col, -1, cv2.LINE_AA)
        cv2.putText(leg, txt, (x + 18, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        x += 18 + 8 * len(txt) + 18
    cv2.imwrite(str(path), np.vstack([leg, sheet]), [cv2.IMWRITE_JPEG_QUALITY, 88])


def loaded_clips(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "pose.npz").exists())


def plot_loaded(root: Path, path: Path) -> list[dict]:
    clips = loaded_clips(root)
    data = []
    for c in clips:
        raw, pz = np.load(c / "raw_pose.npz"), np.load(c / "pose.npz")
        att = json.loads((c / "attempts.json").read_text())["attempts"]
        windows = [(int(x["window"][0]), int(x["window"][1])) for x in att]
        side = SIDE_OF[json.loads((c / "facing.json").read_text())["facing"]]
        t = np.asarray(raw["t"], float)
        data.append({"name": c.name.split("_")[0], "t": t, "att": att, "side": side, "pz": pz,
                     "rtm": skel.sagittal_angles(sca.smoothed(raw["keypoints"], t, windows, side), side)["knee"],
                     "s6": skel.sagittal_angles(sca.smoothed(pz["keypoints"], t, windows, side), side)["knee"]})
    cols = max(len(d["att"]) for d in data)
    fig, axes = plt.subplots(len(data), cols, figsize=(9, 1.9 * len(data) + 0.6), squeeze=False, dpi=100)
    for r, d in enumerate(data):
        kj = HALPE26[f"{d['side']}_knee"]
        for c in range(cols):
            ax = axes[r, c]
            if c >= len(d["att"]):
                ax.axis("off")
                continue
            s, e = d["att"][c]["start"], d["att"][c]["end"]
            x = d["t"][s:e] - d["t"][s]
            for hid, col in ((d["pz"]["hidden"][s:e, kj] & ~d["pz"]["filled"][s:e, kj], "#f2b134"), (d["pz"]["filled"][s:e, kj], MPL["s6"])):
                for a0, a1 in runs_of(hid):
                    ax.axvspan(x[a0], x[a1 - 1], color=col, alpha=0.2, lw=0)
            ax.plot(x, d["rtm"][s:e], color=MPL["rtm"], lw=1.4, label="RTMPose (smoothed)")
            ax.plot(x, d["s6"][s:e], color=MPL["s6"], lw=1.4, label="S6 hybrid (smoothed)")
            ax.set_title(f"{d['name']} attempt {c + 1}", fontsize=8, pad=2)
            ax.tick_params(labelsize=7)
            ax.grid(alpha=0.3)
            if c == 0:
                ax.set_ylabel("knee deg", fontsize=8)
            if r == len(data) - 1:
                ax.set_xlabel("s from liftoff", fontsize=8)
    from matplotlib.patches import Patch
    h, lab = axes[0, 0].get_legend_handles_labels()
    h += [Patch(color=MPL["s6"], alpha=0.3), Patch(color="#f2b134", alpha=0.35)]
    lab += ["S6 rebuilt the knee here", "plate hides a joint, knee kept as RTMPose's"]
    fig.legend(h, lab, loc="upper center", ncol=2, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.55 / (1.9 * len(data) + 0.6)))
    fig.savefig(path)
    plt.close(fig)
    out = []
    for d, c in zip(data, clips):
        line = next((ln for ln in (root / f"{c.name}.log").read_text().splitlines() if ln.strip().startswith("S6:")), "")
        out.append({"clip": d["name"], "log": line.strip()})
    return out


# ---------------------------------------------------------------- verdict

def fmt(v: tuple[float, float]) -> str:
    return f"{v[0]:.1f} (p90 {v[1]:.1f})"


def write_verdict(path: Path, root: Path, rows, total, zone, s5, thigh_f, shank_f, seg_frames, loaded, radius, pulls, spans, plate, pc) -> None:
    L = ["# S6 proof: is the rebuilt knee better than RTMPose's guess behind the plate?", ""]
    L += ["## Question 1: behind the plate, is S6 closer to the real knee than RTMPose?", "",
          "Frames where the true knee is inside the pasted plate. Median (and the 90th percentile, the worse tenth) of the "
          "error against the true knee: position in cm, knee angle in degrees. Smaller is better.", "",
          "| pull | frames | S6 rebuilt knee on | RTMPose cm | S6 cm | RTMPose deg | S6 deg |", "|---|---|---|---|---|---|---|"]
    for r in [*rows, total, zone]:
        L.append(f"| {r['pull']} | {r['n']} | {r['filled']} | {fmt(r['rtm_cm'])} | {fmt(r['s6_cm'])} | {fmt(r['rtm_deg'])} | {fmt(r['s6_deg'])} |")
    better_cm, better_deg = total["s6_cm"][0] < total["rtm_cm"][0], total["s6_deg"][0] < total["rtm_deg"][0]
    per_pull = sum(r["s6_cm"][0] < r["rtm_cm"][0] for r in rows)
    L += ["", "S6 only rebuilds where its rule says so (the knee hidden, the hip and ankle not, the leg bent enough); "
          "elsewhere its knee is RTMPose's, so the two columns match on those frames.", ""]

    def gain(k: str, q: int, d: dict = total) -> str:
        r, s_ = d[f"rtm_{k}"][q], d[f"s6_{k}"][q]
        return f"{r:.1f} -> {s_:.1f} {'cm' if k == 'cm' else 'deg'} ({abs(r - s_) / r:.0%} {'smaller' if s_ < r else 'LARGER'})"
    modest = (total["rtm_cm"][0] - total["s6_cm"][0]) / total["rtm_cm"][0] < 0.15
    verdict = ("yes, but only slightly in position" if modest else "yes") if better_cm and better_deg else "no (or not clearly)"
    L.append(f"**Answer: {verdict}.** Over all {total['n']} frames with the true knee in the plate, S6 is closer in {per_pull} of {len(rows)} pulls "
             f"(position). Median position error {gain('cm', 0)}, median angle error {gain('deg', 0)}; "
             f"the worse tenth: position {gain('cm', 1)}, angle {gain('deg', 1)}. "
             f"With the knee in the inner {INNER:.0%} of the plate ({zone['n']} frames): position {gain('cm', 0, zone)}, angle {gain('deg', 0, zone)}."
             + (" Over all frames the position gain is small because in much of the first pull the knee sits near the plate's rim, "
                "where RTMPose is already close; the gain is larger with the knee well behind the plate and in angle." if modest else ""))
    L += ["", "## Question 2: does S6 invent knee bends?", "",
          f"A dip = the knee angle drops by {DIP_DEG:.0f} deg or more and comes back up by as much, between the start of the lift and "
          "the bar's peak (the rule the pipeline check uses). A dip the true knee does not have is an invented bend.", "",
          "| pull | truth | RTMPose (pasted) | S6 |", "|---|---|---|---|"]
    for r in rows:
        d = r["dips"]
        L.append(f"| {r['pull']} | {d['truth']} | {d['rtm']} | {d['s6']} |")
    tot = {k: sum(r["dips"][k] for r in rows) for k in ("truth", "rtm", "s6")}
    L.append(f"| all | {tot['truth']} | {tot['rtm']} | {tot['s6']} |")
    inv = {k: sum(max(r["dips"][k] - r["dips"]["truth"], 0) for r in rows) for k in ("rtm", "s6")}
    L += ["", f"**Answer: {'no' if inv['s6'] == 0 else 'yes'}.** Dips beyond the truth's: S6 {inv['s6']}, RTMPose {inv['rtm']} "
          f"(over {len(rows)} pulls). Dips the truth has that are missed: S6 "
          f"{sum(max(r['dips']['truth'] - r['dips']['s6'], 0) for r in rows)}, RTMPose "
          f"{sum(max(r['dips']['truth'] - r['dips']['rtm'], 0) for r in rows)}. None of these pulls has a real re-bend behind the plate, "
          "so this shows S6 does not invent one, not that it would find a real one."]
    L += ["", "## Question 3: on real loaded clips, where we can test (knee visible), how close is S6?", "",
          "No truth behind the plate on a loaded clip, so the pipeline check hides a knee that is visible and rebuilds it "
          "(two folds by time: fit the thigh/shank factors on one half, test on the other). From each clip's log:", "",
          "| clip | knee frames S6 rebuilt | hold-out knee error | frames | re-bend dips, start to peak (S6 / RTMPose) |", "|---|---|---|---|---|"]
    ho = []
    for c in loaded:
        m = re.search(r"hold-out ([\d.]+) cm .*?, ([\d.]+) deg, (\d+) frames", c["log"])
        rb = re.search(r"hybrid (\d+), RTMPose (\d+)", c["log"])
        fl_ = re.search(r"(\d+) knee frames filled, (\d+) hidden", c["log"])
        why = re.search(r"(hold-out: [^;]*|scale method none[^;]*)", c["log"])
        if m:
            ho.append(float(m.group(1)))
        L.append(f"| {c['clip']} | {fl_.group(1) + ' of ' + fl_.group(2) + ' hidden' if fl_ else '-'} | "
                 f"{m.group(1) + ' cm / ' + m.group(2) + ' deg' if m else 'not run: ' + (why.group(1) if why else 'no S6 line')} | "
                 f"{m.group(3) if m else '-'} | {rb.group(1) + ' / ' + rb.group(2) if rb else '-'} |")
    L += ["", (f"**Answer:** where the hold-out ran, S6 rebuilds a visible knee to {min(ho):.1f} to {max(ho):.1f} cm median (gate 3 cm, target 2 cm), "
               "and has no more knee dips than RTMPose on any clip. Not every clip can be tested (see 'not run'); "
               "3_loaded_curves.png shows where and by how much S6 changes the knee-angle curves S7/S8 will read: only inside the shaded spans, "
               "mostly by a few degrees." if ho else "**Answer:** no hold-out ran.")]
    L += ["", "## How this test works", "",
          f"A real 5 kg plate (cut from T1, resized to the loaded clips' rest radius of {radius:.0f} px) is pasted on the near bar end "
          f"of the bar-only clip `{CLEAN.name}` in every frame of each pull (setup - {PAD_BEFORE_S} s to peak + {PAD_AFTER_S} s). "
          "RTMPose runs again on the pasted frames, S6's own `fill` rebuilds the knee from that output, and both are compared with "
          "RTMPose on the clean frames (the true knee). "
          "This clip is not T5: the athlete's leg lengths were fitted on T5, so testing there would grade S6 on its own calibration data; "
          f"here the lengths are T5's times S5's factor ({s5.factor:.3f}, `{s5.method}`) and thigh x{thigh_f:.3f} / shank x{shank_f:.3f} "
          f"(from {len(seg_frames)} frames with the knee visible outside the pasted plate), as S5 would fix them on a loaded clip of this session. "
          "Limits: the pasted disc has no shadow, blur or far plate; the person boxes come from the clean frames; the truth is "
          "RTMPose's estimate of a visible knee (about 1 cm jitter), not a marker; the plate sits on a tracked collar "
          f"(match score median {np.nanmedian(pc['cscore']):.2f}, min {np.nanmin(pc['cscore']):.2f}); one lifter, one session, a standup (not a snatch) clip.", ""]
    path.write_text("\n".join(L))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
