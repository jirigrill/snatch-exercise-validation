"""S7: joint angles and snatch phases (snatch.phases; rules in docs/results/37-s7-phases.md).

Reads S6's pose.npz (keypoints, `t`, `filled`, `hidden`), the plate track (hub, outline), attempts.json
(the windows) and facing.json (the near side). Per attempt window: smooth the near side, take hip, knee
and elbow angles, find the borders and the phases.

- angles.csv: one row per posed frame: frame, t, attempt, hip, knee, elbow (deg), hip_filled, knee_filled,
  elbow_filled (S6's mask), wrist_hidden (near wrist inside the plate outline x HIDDEN_DIST), hub_y (smoothed).
- phases.json: per attempt the window, the bar_overhead marker, the 7 borders ({frame, t, filled, hidden} or
  null; filled / hidden = S6's mask at the near hip, knee or ankle on that frame) and the 8 phases
  ({name, start, end}); `params` = the thresholds.
- angles.png: per attempt, hip / knee / elbow against time, the hub height on a twin axis, a line per border,
  the phases shaded, spans where S6 filled the knee in red.
- grabs/a<k>_<border>.jpg: the frame at each border, cropped around the lifter, name and frame number on it;
  phase_sheet.jpg tiles them, one row per attempt in border order.
- overlays/7_phases.mp4 (attempt windows, every 4th frame plus the border frames, zoomed): the near-side
  skeleton, the hub, the phase name and the angles as text, a coloured banner at each border frame.
"""

import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from snatch import overlay  # noqa: E402
from snatch.fill import HIDDEN_DIST  # noqa: E402
from snatch.phases import BORDERS, PARAMS, PHASES, find_phases  # noqa: E402
from snatch.plate import ellipse_dist  # noqa: E402
from snatch.pose import HALPE26, SIDE_OF  # noqa: E402
from snatch.signals import smooth  # noqa: E402
from snatch.skeleton import joint_angle  # noqa: E402
from snatch.stage import CLIP, Context, Stage  # noqa: E402
from snatch.video import frames, probe  # noqa: E402

OVERLAY = "overlays/7_phases.mp4"
SHADE = ("#bbbbbb", "#9ecae1", "#a1d99b", "#fdd0a2", "#fcbba1", "#d4b9da", "#c7e9c0", "#dadaeb")  # one per phase
BORDER_COLOR = (0, 140, 255)  # BGR banner
CROP_MARGIN = 0.25
TILE = (260, 340)  # sheet tile, w x h
JOINTS = ("nose", "shoulder", "elbow", "wrist", "hip", "knee", "ankle")


def _pt(p: np.ndarray) -> tuple[int, int]:
    return int(p[0]), int(p[1])


def _smooth_joint(kp: np.ndarray, t: np.ndarray) -> np.ndarray:
    return np.stack([smooth(kp[:, d], t=t) for d in (0, 1)], -1)


def _attempt(a: dict, kp: np.ndarray, plate: dict, t: np.ndarray, side: str, filled: np.ndarray, hidden: np.ndarray) -> dict:
    """Signals, angles and phases of one attempt window (global frame numbers in the result)."""
    s, e = int(a["window"][0]), int(a["window"][1])
    tw = t[s:e]
    j = {n: HALPE26[n if n == "nose" else f"{side}_{n}"] for n in JOINTS}
    sm = {n: _smooth_joint(kp[s:e, j[n]], tw) for n in JOINTS}
    hub = smooth(np.asarray(plate["hub_y"], float)[s:e], t=tw)
    hip = joint_angle(sm["shoulder"], sm["hip"], sm["knee"])
    knee = joint_angle(sm["hip"], sm["knee"], sm["ankle"])
    elbow = joint_angle(sm["shoulder"], sm["elbow"], sm["wrist"])
    ppm = float(np.nanmedian(np.asarray(plate["px_per_m"], float)[s:e]))
    found = find_phases(knee=knee, hub_y=hub, hip_y=sm["hip"][:, 1], knee_y=sm["knee"][:, 1], nose_y=sm["nose"][:, 1],
                        t=tw, px_per_m=ppm,
                        px_per_m_frame=np.asarray(plate["px_per_m"], float)[s:e])
    w = kp[s:e, j["wrist"]]
    with np.errstate(invalid="ignore"):
        d = ellipse_dist(w[:, 0], w[:, 1], plate["hub_x"][s:e], plate["hub_y"][s:e], plate["a"][s:e], plate["b"][s:e],
                         plate["angle"][s:e])
    wrist_hidden = np.asarray(plate["found"], bool)[s:e] & (d < HIDDEN_DIST)
    legs = [j["hip"], j["knee"], j["ankle"]]

    def border(i: int | None) -> dict | None:
        if i is None:
            return None
        g = s + i
        return dict(frame=g, t=float(t[g]), filled=bool(filled[g, legs].any()), hidden=bool(hidden[g, legs].any()))

    def glob(i: int | None) -> int | None:
        return None if i is None else s + i

    return dict(attempt=int(a["attempt"]), window=[s, e], sm=sm, hip=hip, knee=knee, elbow=elbow, hub=hub,
                wrist_hidden=wrist_hidden, filled=filled[s:e][:, [j["hip"], j["knee"], j["elbow"]]],
                bar_overhead=None if found.bar_overhead is None else dict(start=s + found.bar_overhead[0], end=s + found.bar_overhead[1]),
                borders={k: border(v) for k, v in found.borders.items()},
                phases=[dict(name=n, start=glob(x), end=glob(y)) for n, x, y in found.phases])


def write_csv(path: Path, atts: list[dict], t: np.ndarray) -> None:
    rows = ["frame,t,attempt,hip,knee,elbow,hip_filled,knee_filled,elbow_filled,wrist_hidden,hub_y"]
    for a in atts:
        s = a["window"][0]
        for i in range(a["window"][1] - s):
            f = a["filled"][i]
            rows.append(f"{s + i},{t[s + i]:.6f},{a['attempt']},{a['hip'][i]:.2f},{a['knee'][i]:.2f},{a['elbow'][i]:.2f},"
                        f"{int(f[0])},{int(f[1])},{int(f[2])},{int(a['wrist_hidden'][i])},{a['hub'][i]:.2f}")
    path.write_text("\n".join(rows) + "\n")


def write_plot(path: Path, atts: list[dict], t: np.ndarray) -> None:
    fig, axes = plt.subplots(len(atts), 1, figsize=(9, 4.2 * len(atts)), dpi=100, squeeze=False)
    for ax, a in zip(axes[:, 0], atts):
        s, e = a["window"]
        tw = t[s:e]
        for p in a["phases"]:
            if p["start"] is not None and p["end"] is not None:
                k = [n for n, *_ in PHASES].index(p["name"])
                ax.axvspan(t[p["start"]], t[min(p["end"], len(t) - 1)], color=SHADE[k], alpha=0.45, lw=0)
        ax.plot(tw, a["hip"], color="tab:blue", label="hip (deg)")
        ax.plot(tw, a["knee"], color="tab:green", label="knee (deg)")
        ax.plot(tw, a["elbow"], color="tab:purple", label="elbow (deg)")
        kf = a["filled"][:, 1]
        if kf.any():
            ax.fill_between(tw, 0, 8, where=kf, color="red", alpha=0.8, step="mid", label="knee filled by S6")
        ax.set_ylim(0, 200)
        ax.set_ylabel("angle (deg)")
        ax.set_xlabel("time (s)")
        tw2 = ax.twinx()
        tw2.plot(tw, -a["hub"], color="tab:orange", lw=2, label="hub height (px, up)")
        tw2.set_ylabel("hub height (px, up)")
        for n, (name, b) in enumerate((k, v) for k, v in a["borders"].items() if v):
            ax.axvline(b["t"], color="k", lw=1, ls="--")
            ax.text(b["t"], 196 - 14 * (n % 4), name, rotation=0, fontsize=8, va="top", ha="left",
                    bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.5))
        oh = a["bar_overhead"]
        if oh:
            ax.axvline(t[oh["start"]], color="tab:orange", lw=1, ls=":", label="bar_overhead start / end")
            ax.axvline(t[min(oh["end"], len(t) - 1)], color="tab:orange", lw=1, ls=":")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = tw2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8, ncol=2)
        ax.set_title(f"attempt {a['attempt']}: frames {s}-{e}, phases shaded, dashed = borders")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _crop_box(pts: np.ndarray, width: int, height: int) -> tuple[int, int, int, int]:
    (x0, y0), (x1, y1) = np.nanmin(pts, 0), np.nanmax(pts, 0)
    mx, my = (x1 - x0) * CROP_MARGIN, (y1 - y0) * CROP_MARGIN
    return max(0, int(x0 - mx)), max(0, int(y0 - my)), min(width, int(x1 + mx)), min(height, int(y1 + my))


def write_grabs(clip: str, tmp: Path, atts: list[dict], kp: np.ndarray, plate: dict, side: str) -> None:
    """One jpg per non-null border; one crop per attempt (the union of the lifter's boxes at its borders)."""
    info = probe(clip)
    want: dict[int, list[tuple[int, str]]] = {}
    boxes = {}
    for a in atts:
        fr = [(b["frame"], k) for k, b in a["borders"].items() if b]
        for f, k in fr:
            want.setdefault(f, []).append((a["attempt"], k))
        if fr:
            pts = []
            for f, _ in fr:
                r = max(float(plate["a"][f]), float(plate["b"][f]))
                pts += [kp[f].reshape(-1, 2), [[plate["hub_x"][f] - r, plate["hub_y"][f] - r], [plate["hub_x"][f] + r, plate["hub_y"][f] + r]]]
            boxes[a["attempt"]] = _crop_box(np.concatenate(pts), info.width, info.height)
    (tmp / "grabs").mkdir(parents=True, exist_ok=True)
    if not want:
        return
    for i, img in enumerate(frames(clip, info, stop=max(want) + 1)):
        for k, name in want.get(i, ()):
            x0, y0, x1, y1 = boxes[k]
            g = img[y0:y1, x0:x1].copy()
            cv2.circle(g, (int(plate["hub_x"][i] - x0), int(plate["hub_y"][i] - y0)), 8, (0, 0, 255), -1)
            leg = [_pt(kp[i, HALPE26[f"{side}_{n}"]] - (x0, y0)) for n in ("shoulder", "hip", "knee", "ankle")]
            cv2.polylines(g, [np.array(leg).reshape(-1, 1, 2)], False, (0, 255, 255), 3)
            s = f"a{k} {name}  f{i}"
            sc = max(0.8, g.shape[1] / 450)
            cv2.putText(g, s, (10, int(40 * sc)), cv2.FONT_HERSHEY_SIMPLEX, sc, (0, 0, 0), int(5 * sc))
            cv2.putText(g, s, (10, int(40 * sc)), cv2.FONT_HERSHEY_SIMPLEX, sc, (255, 255, 255), int(2 * sc))
            cv2.imwrite(str(tmp / "grabs" / f"a{k}_{name}.jpg"), g, [cv2.IMWRITE_JPEG_QUALITY, 90])


def write_sheet(path: Path, tmp: Path, atts: list[dict]) -> None:
    w, h = TILE
    rows = []
    for a in atts:
        row = []
        for name in BORDERS:
            tile = np.full((h, w, 3), 40, np.uint8)
            g = cv2.imread(str(tmp / "grabs" / f"a{a['attempt']}_{name}.jpg"))
            if g is not None:
                sc = min(w / g.shape[1], h / g.shape[0])
                g = cv2.resize(g, (max(1, int(g.shape[1] * sc)), max(1, int(g.shape[0] * sc))), interpolation=cv2.INTER_AREA)
                tile[:g.shape[0], :g.shape[1]] = g
            else:
                cv2.putText(tile, f"a{a['attempt']} {name}", (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(tile, "none", (8, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            row.append(tile)
        rows.append(np.hstack(row))
    cv2.imwrite(str(path), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])


def run(ctx: Context, tmp: Path) -> None:
    pose = np.load(ctx.path("pose.npz"))
    plate = dict(np.load(ctx.path("plate.npz")))
    side = SIDE_OF[json.loads(ctx.path("facing.json").read_text())["facing"]]
    entries = json.loads(ctx.path("attempts.json").read_text())["attempts"]
    t = np.asarray(pose["t"], float)
    kp = np.asarray(pose["keypoints"], float)
    atts = [_attempt(a, kp, plate, t, side, pose["filled"], pose["hidden"]) for a in entries]

    write_csv(tmp / "angles.csv", atts, t)
    write_plot(tmp / "angles.png", atts, t)
    (tmp / "phases.json").write_text(json.dumps(
        dict(attempts=[{k: a[k] for k in ("attempt", "window", "bar_overhead", "borders", "phases")} for a in atts],
             params=PARAMS), indent=2) + "\n")
    write_grabs(str(ctx.clip), tmp, atts, kp, plate, side)
    write_sheet(tmp / "phase_sheet.jpg", tmp, atts)

    n = len(t)
    angles = np.full((n, 3), np.nan)
    which = np.zeros(n, int)
    phase_at: list[str] = [""] * n
    banner: dict[int, list[str]] = {}
    for a in atts:
        s, e = a["window"]
        angles[s:e] = np.column_stack([a["hip"], a["knee"], a["elbow"]])
        which[s:e] = a["attempt"]
        for p in a["phases"]:
            if p["start"] is not None and p["end"] is not None:
                for i in range(p["start"], min(p["end"], e)):
                    phase_at[i] = p["name"]
        for k, b in a["borders"].items():
            if b:
                banner.setdefault(b["frame"], []).append(k)
    far = "l" if side == "r" else "r"
    view = kp.copy()
    view[:, [v for k, v in HALPE26.items() if k.startswith(f"{far}_")]] = np.nan

    def labels(i: int) -> list[str]:
        hip, knee, elbow = angles[i]
        return [f"attempt {which[i]}: {phase_at[i] or 'outside phases'}", f"hip {hip:.0f}  knee {knee:.0f}  elbow {elbow:.0f} deg",
                *(f"BORDER {k}" for k in banner.get(i, ()))]

    def annotate(img: np.ndarray, i: int) -> None:
        if i in banner:
            x, y = _pt(np.nan_to_num(kp[i, HALPE26["nose"]], nan=100.0))
            text = " + ".join(banner[i])
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 5)
            x0, y0 = max(0, x - tw // 2), max(th + 20, y - 160)
            cv2.rectangle(img, (x0 - 12, y0 - th - 14), (x0 + tw + 12, y0 + 14), BORDER_COLOR, -1)
            cv2.putText(img, text, (x0, y0), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 5)

    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), poses=[{"keypoints": view}], plate=plate, step=4, zoom=True,
                   extra=sorted(banner), frame_labels=labels, annotate=annotate)


STAGE = Stage("S7", (CLIP, "pose.npz", "plate.npz", "attempts.json", "facing.json"),
              ("angles.csv", "angles.png", "phases.json", "phase_sheet.jpg", "grabs", OVERLAY), run)
