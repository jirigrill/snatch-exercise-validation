"""D1 camera-view numbers: keypoints at the transition and in the pull, plate
tracking, and rectified bar-path markers per view (docs/results/33-d1-views.md).

usage: uv run python scripts/d1_views.py [--v1|--v2] [--near] out/<clip> [out/<clip> ...]
       (--v1: v1 phases (wrists) for every clip, so views compare like for like;
        --v2: v2 phases even where the plate check failed;
        --near: read plate_near.npz from scripts/d1_near_plate.py where present)
reads  out/<clip>/raw_pose.npz, out/<clip>/plate.npz
writes out/<clip>/d1_views.json (per clip), out/d1_views.md (all clips given)

Reps and phases: definition v2 (hub), as compare_phases.py; v1 (wrists) if
the plate check failed. Windows per rep:
- transition: +-0.1 s around the v2 transition (knee re-bend), or around the
  frame the hub passes above the knees if no re-bend is found;
- pull: setup (liftoff) -> peak knee extension before the overhead run.
"Behind plate" = the keypoint lies inside the plate outline (snatch.views.
ellipse_dist < 1): the plate is the nearest thing to the camera, so the
joint is hidden and its keypoint a guess, whatever its score.
Bar markers (snatch.markers) are computed on the hub path rectified to the
plate plane with the clip's resting outline (snatch.views.rectify).
"""

import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from snatch import views
from snatch.angles import COCO, mid_y, sagittal_angles
from snatch.markers import bar_markers
from snatch.phases import find_reps, find_reps_v2
from snatch.plate import PLATE_DIAMETER_M
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frame_times, mean_rate

NEAR, FAR = "r", "l"  # camera on the lifter's right
JOINTS = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")
SEGMENTS = {"thigh": ("hip", "knee"), "shank": ("knee", "ankle"),
            "upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist")}
HALF_WIN_S = 0.1
MARKERS = ("x1_cm", "x2_cm", "xloop_cm", "xnet_cm", "drop_cm", "peak_v_m_s")


def nanmean(x):
    x = np.asarray(x, float)
    return float(np.nanmean(x)) if np.isfinite(x).any() else math.nan


def rnd(x, d=2):
    if isinstance(x, dict):
        return {k: rnd(v, d) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, d) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(x) else round(float(x), d)
    return x


def safe_markers(hub, ppm, fps, rep, t) -> dict:
    """snatch.markers.bar_markers, or all NaN where its windows are empty
    (a hub track that is wrong, e.g. a failed plate check)."""
    try:
        return asdict(bar_markers(hub[:, 0], hub[:, 1], ppm, fps, rep, t))
    except ValueError:
        return {"peak_frame": None, "bar_catch_frame": None} | {
            m: math.nan for m in MARKERS + ("turnover_s", "turnover_to_bar_catch_s")}


def resting_outline(plate, rest):
    """Median outline over resting frames: (minor, major, major-axis angle
    from image vertical in deg, ang of the a axis to feed views.rectify)."""
    a, b, ang = plate["a"][rest], plate["b"][rest], plate["angle"][rest]
    major_dir = np.where(a >= b, ang, ang + 90) % 180  # direction of the major axis
    tilt = float(np.median(major_dir - 90))  # 0 = vertical
    return (float(np.median(np.fmin(a, b))), float(np.median(np.fmax(a, b))),
            tilt)


def analyse(out: Path, force_v2: bool = False, near: bool = False,
            force_v1: bool = False) -> dict:
    pfile = out / "plate_near.npz"
    if not (near and pfile.exists()):
        pfile = out / "plate.npz"
    raw, plate = np.load(out / "raw_pose.npz"), np.load(pfile)
    kps, scores = raw["keypoints"].astype(float), raw["scores"]
    t = frame_times(raw)
    fps = mean_rate(t)
    n = len(kps)
    kps_s = smooth_keypoints(kps, fps)
    found_raw = plate["found"].astype(bool)
    hub = np.column_stack([plate["hub_x"], plate["hub_y"]]).astype(float)
    status = str(plate["status"])
    knee = sagittal_angles(kps_s, NEAR)["knee"]
    common = dict(nose_y=mid_y(kps_s, "nose"), hip_y=mid_y(kps_s, "hip"),
                  knee=knee, fps=fps, knee_y=mid_y(kps_s, "knee"), t=t)
    reps_v1 = find_reps(wrist_y=mid_y(kps_s, "wrist"), **common)

    # near-plate gate inside the lifts (v1 spans, wrists): in oblique views
    # the tracker also follows the far plate or round objects behind
    span = np.zeros(n, bool)
    pre = np.zeros(n, bool)  # up to 1 s before each v1 liftoff
    for r in reps_v1:
        span[max(r.setup - int(0.5 * fps), 0):r.overhead_end] = True
        pre[max(r.setup - int(1.0 * fps), 0):r.setup] = True
    major0 = float(np.nanmedian(np.fmax(plate["a"], plate["b"])[found_raw]))
    nw, fw = kps_s[:, COCO[f"{NEAR}_wrist"]], kps_s[:, COCO[f"{FAR}_wrist"]]
    near_ok = (views.near_plate_mask(hub, nw, fw)
               & (np.linalg.norm(hub - nw, axis=1) < 4 * major0))
    if str(plate["model"]) != "ellipse":  # side-on: the far plate is hidden
        near_ok[:] = True
    found = found_raw & (near_ok | ~span)
    hub[~found] = np.nan
    hub_s = np.column_stack([smooth(hub[:, 0], fps), smooth(hub[:, 1], fps)])
    # v2 reps matched to the v1 ones by overhead overlap (an extra v2 "rep"
    # from a wrong hub stretch is dropped); v1 where no v2 rep matches
    reps_v2 = find_reps_v2(hub_y=hub_s[:, 1], **common)
    reps, defs = [], []
    for r1 in reps_v1:
        m = [r2 for r2 in reps_v2 if r2.overhead_start < r1.overhead_end
             and r1.overhead_start < r2.overhead_end]
        use_v2 = (status == "ok" or force_v2) and len(m) == 1 and not force_v1
        reps.append(m[0] if use_v2 else r1)
        defs.append("v2" if use_v2 else "v1")
    definition = "/".join(defs)

    # --- plate --------------------------------------------------------------
    rest = views.rest_mask(hub_s[:, 1], found & pre, fps)
    minor, major, tilt = resting_outline(plate, rest)
    ratio_all = views.axis_ratio(plate["a"][found], plate["b"][found])
    ppm = 2 * major / PLATE_DIAMETER_M
    mm = 1000 / ppm
    jit = hub - hub_s
    plate_out = {
        "status": status, "model": str(plate["model"]),
        "found_pct": 100 * found_raw.mean(), "ellipse_fit_pct": 100 * plate["ellipse_fit"].mean(),
        "near_plate_in_lifts_pct": 100 * float(found[span].mean()),
        "far_or_other_in_lifts_pct": 100 * float((found_raw & ~near_ok)[span].mean()),
        "jumps": int(len(plate["jumps"])),
        "rest_frames": int(rest.sum()),
        "axis_ratio_rest": minor / major, "view_deg_rest": float(views.view_angle_deg(minor, major)),
        "view_deg_all_median": float(np.degrees(np.arccos(np.median(ratio_all)))),
        "view_deg_all_p10_p90": [float(np.degrees(np.arccos(np.percentile(ratio_all, q))))
                                 for q in (90, 10)],
        "major_tilt_deg": tilt, "major_px": major, "px_per_m": ppm,
        "px_per_m_cv_pct": 100 * float(np.nanstd(plate["px_per_m"][found])
                                       / np.nanmedian(plate["px_per_m"][found])),
        "hub_jitter_rest_px": [float(np.std(jit[rest, 0])), float(np.std(jit[rest, 1]))],
        "hub_jitter_lift_px": [float(np.nanstd(jit[found & span, 0])),
                               float(np.nanstd(jit[found & span, 1]))],
    }
    plate_out["hub_jitter_rest_mm"] = [v * mm for v in plate_out["hub_jitter_rest_px"]]
    plate_out["hub_jitter_lift_mm"] = [v * mm for v in plate_out["hub_jitter_lift_px"]]

    # rectified hub path, origin at the first resting frame: x stretched by
    # major / minor of the resting outline (= 1 / cos(view angle)), y as is.
    # Axis-aligned (phone level, protocol step 4): the resting outline's tilt
    # (up to -46 deg here) comes from looking down at the plate and changes
    # with the plate's height, so it is not used
    o = hub_s[np.flatnonzero(rest)[0]] if rest.any() else hub_s[0]
    dx, dy = views.rectify(hub_s[:, 0] - o[0], hub_s[:, 1] - o[1], minor, major, 0.0)
    hub_r = np.column_stack([o[0] + dx, o[1] + dy])

    # --- per rep ------------------------------------------------------------
    p = {(s, j): COCO[f"{s}_{j}"] for s in (NEAR, FAR) for j in JOINTS}
    sep_px = 0.05 * ppm  # near/far tracks 5 cm apart before a swap counts
    rep_out = []
    for k, r in enumerate(reps):
        peak = r.setup + int(np.argmax(knee[r.setup:r.overhead_start + 1]))
        above = np.flatnonzero(hub_s[r.setup:peak + 1, 1]
                               < mid_y(kps_s, "knee")[r.setup:peak + 1])
        hub_at_knee = r.setup + int(above[0]) if len(above) else None
        centre = r.transition if r.transition is not None else hub_at_knee
        h = int(HALF_WIN_S * fps)
        wins = {"pull": (r.setup, peak + 1)}
        if centre is not None:
            wins["transition"] = (max(centre - h, 0), min(centre + h + 1, n))
        kp: dict = {}
        for wname, (w0, w1) in wins.items():
            sl = slice(w0, w1)
            fw = found[sl]
            for j in JOINTS:
                ni, fi = p[NEAR, j], p[FAR, j]
                pts = kps[sl, ni]
                d = views.ellipse_dist(pts[:, 0], pts[:, 1], plate["hub_x"][sl],
                                       plate["hub_y"][sl], plate["a"][sl],
                                       plate["b"][sl], plate["angle"][sl])
                behind = (d < 1)[fw]
                kp.setdefault(j, {})[wname] = {
                    "near_score_mean": float(scores[sl, ni].mean()),
                    "near_score_min": float(scores[sl, ni].min()),
                    "far_score_mean": float(scores[sl, fi].mean()),
                    "near_jitter_mm": views.jitter_px(pts, kps_s[sl, ni]) * mm,
                    "behind_plate_pct": 100 * float(behind.mean()) if len(behind) else math.nan,
                    "swap_pct": 100 * float(views.swap_frames(
                        pts, kps[sl, fi], kps_s[sl, ni], kps_s[sl, fi], sep_px).mean()),
                    "near_far_sep_cm": float(np.median(np.linalg.norm(
                        kps_s[sl, ni] - kps_s[sl, fi], axis=1))) * 100 / ppm,
                }
            for sname, (j1, j2) in SEGMENTS.items():
                L = np.linalg.norm(kps[sl, p[NEAR, j1]] - kps[sl, p[NEAR, j2]], axis=1)
                Ls = np.linalg.norm(kps_s[sl, p[NEAR, j1]] - kps_s[sl, p[NEAR, j2]], axis=1)
                kp.setdefault("seg_" + sname, {})[wname] = {
                    "len_cm": float(np.median(L)) * 100 / ppm,
                    "len_cv_pct": 100 * float(np.std(L) / np.mean(L)),
                    "len_jitter_mm": float(np.std(L - Ls)) * mm,
                }
        bm_r = safe_markers(hub_r, ppm, fps, r, t)
        bm_u = safe_markers(hub_s, ppm, fps, r, t)
        before = slice(max(r.setup - int(0.25 * fps), 0), r.setup)
        # first pull: horizontal hub position (rectified, cm from setup) when
        # the hub first reaches 25 / 50 / 75 cm above its setup height
        h_cm = (hub_r[r.setup, 1] - hub_r[r.setup:peak + 1, 1]) * 100 / ppm
        x_cm = (hub_r[r.setup:peak + 1, 0] - hub_r[r.setup, 0]) * 100 / ppm
        xu_cm = (hub_s[r.setup:peak + 1, 0] - hub_s[r.setup, 0]) * 100 / ppm
        x_at = {}
        for h in (25, 50, 75):
            up = np.flatnonzero(h_cm >= h)
            x_at[str(h)] = ([float(x_cm[up[0]]), float(xu_cm[up[0]]),
                             100 * float(found[r.setup:r.setup + up[0] + 1].mean())]
                            if len(up) else [math.nan, math.nan, math.nan])
        rep_out.append({
            "x_at_height_cm": x_at,
            "rep": k + 1, "definition": defs[k], "setup": r.setup, "hub_at_knee": hub_at_knee,
            "transition": r.transition, "peak_ext": peak, "catch": r.catch,
            "lockout": r.lockout, "overhead_start": r.overhead_start,
            "hub_found_pull_pct": 100 * float(found[r.setup:peak + 1].mean()),
            "keypoints": kp,
            "bar_rect": bm_r | {"peak_height_cm": math.nan if bm_r["peak_frame"] is None else
                                float(hub_r[r.setup, 1] - hub_r[bm_r["peak_frame"], 1]) * 100 / ppm},
            "bar_unrect": bm_u,
            "rest_before_cm": [float(np.median(hub_r[before, 0]) - o[0]) * 100 / ppm,
                               float(np.median(hub_r[before, 1]) - o[1]) * 100 / ppm],
        })
    paths = [(hub_r[r.setup:r.lockout + 1] - hub_r[r.setup]) * 100 / ppm for r in reps]
    return {"_paths": paths, "clip": out.name, "plate_file": pfile.name, "fps": fps, "definition": definition,
            "n_reps": len(reps), "plate": plate_out, "reps": rep_out}


def summary(res: dict) -> dict:
    """Mean over reps of the per-rep numbers used in the doc tables."""
    s: dict = {}
    for j in JOINTS:
        for w in ("transition", "pull"):
            vals = [r["keypoints"][j][w] for r in res["reps"] if w in r["keypoints"][j]]
            s[f"{j}/{w}"] = {k: nanmean([v[k] for v in vals]) for k in vals[0]} if vals else {}
    for seg in SEGMENTS:
        vals = [r["keypoints"]["seg_" + seg]["pull"] for r in res["reps"]]
        s[f"seg_{seg}/pull"] = {k: nanmean([v[k] for v in vals]) for k in vals[0]} if vals else {}
    bars = [r["bar_rect"] for r in res["reps"]]
    for m in MARKERS + ("peak_height_cm",):
        xs = [b[m] for b in bars]
        s[f"bar/{m}"] = {"mean": nanmean(xs), "sd": float(np.nanstd(xs, ddof=1)) if len(xs) > 1 else math.nan,
                         "values": xs}
    for m in ("x1_cm", "x2_cm", "xloop_cm", "xnet_cm"):
        xs = [r["bar_unrect"][m] for r in res["reps"]]
        s[f"bar_unrect/{m}"] = {"mean": nanmean(xs), "values": xs}
    for h in ("25", "50", "75"):
        xs = [r["x_at_height_cm"][h] for r in res["reps"]]
        s[f"x_at_{h}"] = {"mean": nanmean([x[0] for x in xs]),
                          "sd": float(np.nanstd([x[0] for x in xs], ddof=1)),
                          "unrect_mean": nanmean([x[1] for x in xs]),
                          "found_pct": nanmean([x[2] for x in xs])}
    rest = np.array([r["rest_before_cm"] for r in res["reps"]])
    s["rest_spread_cm"] = (np.std(rest, axis=0, ddof=1).tolist() if len(rest) > 1
                           else [math.nan, math.nan])
    return s


def plot_paths(results: list[dict]) -> None:
    """Rectified hub path per rep, setup -> lockout, origin at setup (cm)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, len(results), figsize=(4 * len(results), 6),
                            sharex=True, sharey=True, squeeze=False)
    for ax, r in zip(axs[0], results):
        for k, pth in enumerate(r["_paths"]):
            ax.plot(pth[:, 0], -pth[:, 1], label=f"rep {k + 1}")
        ax.set_title(r["clip"].split("_success_")[-1] + f" ({r['definition']})", fontsize=9)
        ax.set_xlabel("x rectified (cm), + = lifter's front")
        ax.axvline(0, color="grey", lw=0.5)
        ax.set_aspect("equal")
        ax.legend(fontsize=7)
    axs[0][0].set_ylabel("height above setup (cm)")
    fig.suptitle("hub path, setup -> lockout, rectified to the plate plane")
    fig.tight_layout()
    fig.savefig("out/d1_paths.png", dpi=110)


def md(results: list[dict]) -> str:
    names = [r["clip"] for r in results]
    L = ["# D1 views — numbers (scripts/d1_views.py)", "",
         "Clips: " + ", ".join(f"`{c}`" for c in names), ""]
    L += ["## Plate", "", "| clip | status | found % | near plate in lifts % (other) | jumps | view° rest (all p10–p90) | "
          "major tilt° | px/m | px/m CV % | hub jitter rest x/y (mm) | hub jitter in lifts x/y (mm) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        p = r["plate"]
        L.append(f"| {r['clip']} ({r['plate_file']}) | {p['status'][:40]} | {p['found_pct']:.1f} | "
                 f"{p['near_plate_in_lifts_pct']:.1f} ({p['far_or_other_in_lifts_pct']:.1f}) | {p['jumps']} | "
                 f"{p['view_deg_rest']:.1f} ({p['view_deg_all_p10_p90'][0]:.0f}–{p['view_deg_all_p10_p90'][1]:.0f}) | "
                 f"{p['major_tilt_deg']:+.1f} | {p['px_per_m']:.0f} | {p['px_per_m_cv_pct']:.1f} | "
                 f"{p['hub_jitter_rest_mm'][0]:.1f}/{p['hub_jitter_rest_mm'][1]:.1f} | "
                 f"{p['hub_jitter_lift_mm'][0]:.1f}/{p['hub_jitter_lift_mm'][1]:.1f} |")
    L += ["", "## Near keypoints (mean over reps)", "",
          "behind = % of window frames inside the plate outline; score near (far); jitter mm; swap %", ""]
    for w in ("transition", "pull"):
        L += [f"### {w}", "", "| clip | " + " | ".join(JOINTS) + " |",
              "|---|" + "---|" * len(JOINTS)]
        for r in results:
            s = r["summary"]
            cells = []
            for j in JOINTS:
                v = s[f"{j}/{w}"]
                cells.append(f"beh {v['behind_plate_pct']:.0f}, s {v['near_score_mean']:.2f} "
                             f"({v['far_score_mean']:.2f}), j {v['near_jitter_mm']:.1f}, "
                             f"sw {v['swap_pct']:.0f}")
            L.append(f"| {r['clip']} | " + " | ".join(cells) + " |")
        L.append("")
    L += ["### near segment length in the pull (median cm, CV %, jitter mm)", "",
          "| clip | " + " | ".join(SEGMENTS) + " |", "|---|" + "---|" * len(SEGMENTS)]
    for r in results:
        s = r["summary"]
        L.append(f"| {r['clip']} | " + " | ".join(
            f"{s[f'seg_{g}/pull']['len_cm']:.1f}, {s[f'seg_{g}/pull']['len_cv_pct']:.1f}, "
            f"{s[f'seg_{g}/pull']['len_jitter_mm']:.1f}" for g in SEGMENTS) + " |")
    L += ["", "## Rectified bar markers (mean ± SD over reps; unrectified mean)", "",
          "| clip | def | reps | peak height cm | X1 | X2 | Xloop | Xnet | drop | peak v m/s | rest spread x/y cm |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        s = r["summary"]

        def c(m, unrect=True):
            v = s[f"bar/{m}"]
            u = f" [{s[f'bar_unrect/{m}']['mean']:.1f}]" if unrect and f"bar_unrect/{m}" in s else ""
            return f"{v['mean']:.1f} ± {v['sd']:.1f}{u}"
        L.append(f"| {r['clip']} | {r['definition']} | {r['n_reps']} | {c('peak_height_cm', False)} | "
                 f"{c('x1_cm')} | {c('x2_cm')} | {c('xloop_cm')} | {c('xnet_cm')} | "
                 f"{c('drop_cm', False)} | {s['bar/peak_v_m_s']['mean']:.2f} ± {s['bar/peak_v_m_s']['sd']:.2f} | "
                 f"{s['rest_spread_cm'][0]:.1f}/{s['rest_spread_cm'][1]:.1f} |")
    L += ["", "## First pull: hub x (cm from setup, rectified; [unrectified]) when the hub "
          "first reaches 25 / 50 / 75 cm above setup; mean ± SD over reps, hub found % up to there", "",
          "| clip | 25 cm | 50 cm | 75 cm |", "|---|---|---|---|"]
    for r in results:
        s = r["summary"]
        L.append(f"| {r['clip']} | " + " | ".join(
            f"{s[f'x_at_{h}']['mean']:+.1f} ± {s[f'x_at_{h}']['sd']:.1f} "
            f"[{s[f'x_at_{h}']['unrect_mean']:+.1f}], {s[f'x_at_{h}']['found_pct']:.0f}%"
            for h in ("25", "50", "75")) + " |")
    L += ["", "## Phase frames", "", "| clip | rep | setup | hub at knee | transition | peak ext | catch | lockout |",
          "|---|---|---|---|---|---|---|---|"]
    for r in results:
        for x in r["reps"]:
            L.append(f"| {r['clip']} | {x['rep']} | {x['setup']} | {x['hub_at_knee']} | "
                     f"{x['transition']} | {x['peak_ext']} | {x['catch']} | {x['lockout']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    results = []
    args = sys.argv[1:]
    force = "--v2" in args  # v2 phases even where the plate check failed
    near = "--near" in args  # plate_near.npz (scripts/d1_near_plate.py) where present
    v1 = "--v1" in args  # v1 phases (wrists) for every clip
    for d in [a for a in args if not a.startswith("--")]:
        res = analyse(Path(d), force, near, v1)
        res["summary"] = summary(res)
        paths = res.pop("_paths")
        (Path(d) / "d1_views.json").write_text(json.dumps(rnd(res, 3), indent=1))
        results.append(res | {"_paths": paths})
    plot_paths(results)
    text = md(results)
    Path("out/d1_views.md").write_text(text)
    print(text)
