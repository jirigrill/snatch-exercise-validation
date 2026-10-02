"""Angles, phases and across-rep SD from raw pose output; overlays for checking.

usage: uv run python scripts/analyze.py ../vids/IMG_4584.MOV out/4584 [spread]
       (spread: also write the across-rep values and SD, spread.md and the
       "values"/"sd" keys of phases.json. Only 4584 (#12) has them; for the
       other clips SD is left to #15, so it is not seen before #15 runs)
reads  out/<clip>/raw_pose.npz; plate.npz and hold.json if present
writes angles.csv, phases.json, angles.png, phase_sheet.jpg, grabs/*.jpg
       (pose and v1 marks only, as in #12), overlay.mp4 (gitignored: pose plus
       plate outline and hub, bar path, v1 and v2 phase marks, scale, hold)
"""

import csv
import json
import math
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import cv2
import matplotlib
import numpy as np

from snatch.angles import COCO, JOINTS, mid_y, sagittal_angles
from snatch.phases import find_reps, find_reps_v2
from snatch.signals import smooth, smooth_keypoints
from snatch.spread import PHASES, phase_values, spread_table
from snatch.video import frames, probe

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

SIDE = "r"  # camera on the lifter's right -> right side is the near side
SKELETON = [("shoulder", "elbow"), ("elbow", "wrist"), ("shoulder", "hip"),
            ("hip", "knee"), ("knee", "ankle")]
NAMES = {v: k for k, v in COCO.items()}

clip, out = sys.argv[1], Path(sys.argv[2])
with_spread = sys.argv[3:] == ["spread"]
raw = np.load(out / "raw_pose.npz")
kps, scores, fps = raw["keypoints"], raw["scores"], float(raw["fps"])
n = len(kps)

kps_s = smooth_keypoints(kps, fps)
ang_raw = sagittal_angles(kps, SIDE)
ang_s = sagittal_angles(kps_s, SIDE)

reps = find_reps(
    wrist_y=mid_y(kps_s, "wrist"),
    nose_y=mid_y(kps_s, "nose"),
    hip_y=mid_y(kps_s, "hip"),
    knee=ang_s["knee"], fps=fps,
    knee_y=mid_y(kps_s, "knee"),
)

# --- per-frame series with raw model output -------------------------------
with open(out / "angles.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["frame", "t_s"]
               + [f"{j}_raw" for j in JOINTS] + [f"{j}_smooth" for j in JOINTS]
               + [f"{NAMES[k]}_{c}" for k in range(17) for c in ("x", "y", "score")]
               + ["n_people"])
    for i in range(n):
        w.writerow([i, f"{i / fps:.5f}"]
                   + [f"{ang_raw[j][i]:.3f}" for j in JOINTS]
                   + [f"{ang_s[j][i]:.3f}" for j in JOINTS]
                   + [v for k in range(17) for v in
                      (f"{kps[i, k, 0]:.2f}", f"{kps[i, k, 1]:.2f}",
                       f"{scores[i, k]:.3f}")]
                   + [int(raw["n_people"][i])])

# --- phases and spread ---------------------------------------------------
vals = {"raw": phase_values(ang_raw, reps), "smooth": phase_values(ang_s, reps)}
sds = {k: spread_table(v) for k, v in vals.items()}
near = [COCO[f"{SIDE}_{p}"] for p in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")]
(out / "phases.json").write_text(json.dumps({
    "fps": fps, "side": SIDE,
    "reps": [asdict(r) | {f"{k}_s": (None if v is None else round(v / fps, 3))
                          for k, v in asdict(r).items()} for r in reps],
    **({"values": vals, "sd": sds} if with_spread else {}),
    "near_side_score_at_phase": {
        ph: [float(scores[getattr(r, ph), near].mean())
             if getattr(r, ph) is not None else None for r in reps]
        for ph in PHASES},
}, indent=1, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x))


def fmt(x: float) -> str:
    return "—" if math.isnan(x) else f"{x:.1f}"


if with_spread:
    lines = [f"# {Path(clip).stem} — SD across {len(reps)} reps (degrees)", ""]
    for kind in ("smooth", "raw"):
        lines += [f"## {kind}", "", "| joint | " + " | ".join(PHASES) + " |",
                  "|---" * (len(PHASES) + 1) + "|"]
        lines += [f"| {j} | " + " | ".join(fmt(sds[kind][j][p]) for p in PHASES) + " |"
                  for j in JOINTS]
        lines += [""]
    lines += ["## values per rep (smooth)", "",
              "| joint | phase | " + " | ".join(f"rep {i + 1}" for i in range(len(reps))) + " |",
              "|---|---|" + "---|" * len(reps)]
    lines += [f"| {j} | {p} | " + " | ".join(fmt(v) for v in vals["smooth"][j][p]) + " |"
              for j in JOINTS for p in PHASES]
    (out / "spread.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
print(json.dumps([asdict(r) for r in reps]))

# --- angle plot with phase marks ------------------------------------------
t = np.arange(n) / fps
fig, axes = plt.subplots(len(JOINTS) + 1, 1, figsize=(14, 12), sharex=True)
for ax, j in zip(axes, JOINTS):
    ax.plot(t, ang_raw[j], lw=0.4, color="0.7", label="raw")
    ax.plot(t, ang_s[j], lw=1, color="k", label="smoothed")
    ax.set_ylabel(f"{j} (deg)")
ax = axes[-1]
for part in ("wrist", "nose", "hip"):
    ax.plot(t, mid_y(kps_s, part), label=f"{part} y")
ax.invert_yaxis()
ax.set_ylabel("image y (px)")
ax.legend(loc="upper right", fontsize=8)
colors = dict(zip(PHASES, ("tab:blue", "tab:orange", "tab:red", "tab:green")))
for r in reps:
    for ph in PHASES:
        fr = getattr(r, ph)
        if fr is not None:
            for a in axes:
                a.axvline(fr / fps, color=colors[ph], lw=1)
axes[0].legend(handles=[Line2D([], [], color=c, label=p) for p, c in colors.items()],
               loc="upper right", fontsize=8, ncol=4)
axes[-1].set_xlabel("time (s)")
fig.suptitle(f"{Path(clip).stem} — RTMPose-x, near ({SIDE}) side")
fig.tight_layout()
fig.savefig(out / "angles.png", dpi=110)

# --- overlays ----------------------------------------------------------------


def draw(img: np.ndarray, i: int, label: str = "") -> np.ndarray:
    img = img.copy()
    for side, col in (("l", (160, 160, 160)), (SIDE, (0, 255, 255))):
        for a, b in SKELETON:
            pa, pb = kps[i, COCO[f"{side}_{a}"]], kps[i, COCO[f"{side}_{b}"]]
            if not (np.isnan(pa).any() or np.isnan(pb).any()):
                cv2.line(img, tuple(map(int, pa)), tuple(map(int, pb)), col, 4)
    for k in range(17):
        if not np.isnan(kps[i, k]).any():
            c = (0, 0, 255) if scores[i, k] < 0.3 else (0, 255, 0)
            cv2.circle(img, tuple(map(int, kps[i, k])), 7, c, -1)
    boxes = [("bbox", (255, 128, 0))]  # detector box: blue
    if "pose_bbox" in raw:
        boxes.append(("pose_bbox", (255, 0, 255)))  # tracked crop: magenta
    for key, col in boxes:
        if not np.isnan(raw[key][i]).any():
            x1, y1, x2, y2 = map(int, raw[key][i])
            cv2.rectangle(img, (x1, y1), (x2, y2), col, 2)
    txt = f"f{i} {label} " + " ".join(f"{j[0]}{ang_s[j][i]:.0f}" for j in JOINTS)
    cv2.putText(img, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 8)
    cv2.putText(img, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
    return img


# --- video-only markers: plate, bar path, v1/v2 marks, scale, hold -----------
# v2 only where the plate track passed its sanity check (#14); 4585/4586 keep
# v1 (decision for #15), 4578 has no plate. Their outline is still drawn, in
# orange, so the failure stays visible.
plate = np.load(out / "plate.npz") if (out / "plate.npz").exists() else None
plate_ok = plate is not None and str(plate["status"]) == "ok"
reps_v2 = []
if plate_ok:
    assert plate is not None and len(plate["hub_y"]) == n, "plate/pose frame counts differ"
    reps_v2 = find_reps_v2(
        hub_y=smooth(plate["hub_y"], fps), nose_y=mid_y(kps_s, "nose"),
        hip_y=mid_y(kps_s, "hip"), knee=ang_s["knee"], fps=fps,
        knee_y=mid_y(kps_s, "knee"))
hold = json.loads((out / "hold.json").read_text()) if (out / "hold.json").exists() else None
events = [(getattr(r, ph), v, ph) for v, rs in (("v1", reps), ("v2", reps_v2))
          for r in rs for ph in PHASES if getattr(r, ph) is not None]
HOLD_BANNER = round(0.25 * fps)  # the video keeps every 4th frame only
TRAIL = round(2 * fps)
EVENT_COL = {"v1": (0, 255, 255), "v2": (0, 255, 0)}


def text(img: np.ndarray, s: str, org: tuple[int, int], scale: float = 1.4,
         col: tuple[int, int, int] = (255, 255, 255)) -> None:
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 8)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, col, 3)


def markers(img: np.ndarray, i: int) -> np.ndarray:
    h, w = img.shape[:2]
    if plate is not None:
        pcol = (0, 255, 0) if plate_ok else (0, 165, 255)
        lo = max(i - TRAIL, 0)
        seg = np.c_[plate["hub_x"][lo:i + 1], plate["hub_y"][lo:i + 1]]
        ok = plate["found"][lo:i + 1]
        for a, b, fa, fb in zip(seg[:-1], seg[1:], ok[:-1], ok[1:]):
            if fa and fb:
                cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), (255, 255, 0), 3)
        if plate["found"][i]:
            cx, cy, a, b, ang = (plate[k][i] for k in ("hub_x", "hub_y", "a", "b", "angle"))
            cv2.ellipse(img, ((cx, cy), (2 * a, 2 * b), ang), pcol, 3)
            cv2.circle(img, (int(cx), int(cy)), 8, (0, 0, 255), -1)
            el = kps[i, COCO[f"{SIDE}_elbow"]]
            if not np.isnan(el).any():  # elbow-to-hub segment (#15 row)
                cv2.line(img, tuple(map(int, el)), (int(cx), int(cy)), (255, 0, 255), 2)
        if not plate_ok:
            text(img, "plate: check (not used for v2)", (20, 120), 1.0, (0, 165, 255))
        px_m = float(np.nanmedian(plate["px_per_m"]))
        x0, y0 = 30, h - 200
        cv2.line(img, (x0, y0), (x0 + int(0.1 * px_m), y0), (255, 255, 255), 6)
        text(img, "10 cm", (x0, y0 - 15), 1.0)
    banner = [f"{v} {ph.upper()}" for f, v, ph in events if f <= i < f + HOLD_BANNER]
    if hold and hold["first_frame"] <= i <= hold["last_frame"]:
        banner.append("HOLD")
    for k, s in enumerate(banner):
        text(img, s, (20, 200 + 70 * k), 1.8,
             EVENT_COL.get(s.split()[0], (255, 255, 255)))
    # timeline: v1 ticks above (yellow), v2 below (green), playhead red
    y = h - 90
    band = img[y - 45:y + 45]
    band[:] = band // 3
    cv2.line(img, (0, y), (w, y), (160, 160, 160), 2)
    for f, v, _ in events:
        x = int(f / n * w)
        cv2.line(img, (x, y - 30 if v == "v1" else y), (x, y if v == "v1" else y + 30),
                 EVENT_COL[v], 4)
    x = int(i / n * w)
    cv2.line(img, (x, y - 40), (x, y + 40), (0, 0, 255), 4)
    return img


grab_at = {getattr(r, ph): f"rep{k + 1}_{ph}" for k, r in enumerate(reps)
           for ph in PHASES if getattr(r, ph) is not None}
(out / "grabs").mkdir(exist_ok=True)
info = probe(clip)
half = (info.width // 2, info.height // 2)
enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
     "-s", f"{half[0]}x{half[1]}", "-r", "60", "-i", "-", "-c:v", "libx264",
     "-pix_fmt", "yuv420p", "-crf", "26", str(out / "overlay.mp4")],
    stdin=subprocess.PIPE)
assert enc.stdin is not None
tiles = {}
for i, img in enumerate(frames(clip, info)):
    if i % 4 and i not in grab_at:
        continue
    base = draw(img, i, grab_at.get(i, ""))
    if i % 4 == 0:
        enc.stdin.write(cv2.resize(markers(base.copy(), i), half).tobytes())
    o = cv2.resize(base, half)
    if i in grab_at:
        cv2.imwrite(str(out / "grabs" / f"{grab_at[i]}_f{i}.jpg"), o,
                    [cv2.IMWRITE_JPEG_QUALITY, 80])
        tiles[grab_at[i]] = cv2.resize(o, (360, 640))
enc.stdin.close()
enc.wait()

blank = np.zeros((640, 360, 3), np.uint8)
rows = [np.hstack([tiles.get(f"rep{k + 1}_{ph}", blank) for ph in PHASES])
        for k in range(len(reps))]
if rows:  # 4579 has no reps
    cv2.imwrite(str(out / "phase_sheet.jpg"), np.vstack(rows),
                [cv2.IMWRITE_JPEG_QUALITY, 80])
print("wrote", sorted(p.name for p in out.iterdir()))
