"""Angles, phases and across-rep SD from raw pose output; overlays for checking.

usage: uv run python scripts/analyze.py ../vids/IMG_4584.MOV out/4584
reads  out/<clip>/raw_pose.npz
writes angles.csv, phases.json, spread.md, angles.png, phase_sheet.jpg,
       grabs/*.jpg, overlay.mp4 (gitignored)
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
from snatch.phases import find_reps
from snatch.signals import smooth
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
raw = np.load(out / "raw_pose.npz")
kps, scores, fps = raw["keypoints"], raw["scores"], float(raw["fps"])
n = len(kps)

kps_s = np.stack([np.stack([smooth(kps[:, j, d], fps) for d in (0, 1)], -1)
                  for j in range(17)], 1)
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
    "values": vals, "sd": sds,
    "near_side_score_at_phase": {
        ph: [float(scores[getattr(r, ph), near].mean())
             if getattr(r, ph) is not None else None for r in reps]
        for ph in PHASES},
}, indent=1, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x))


def fmt(x: float) -> str:
    return "—" if math.isnan(x) else f"{x:.1f}"


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
    o = cv2.resize(draw(img, i, grab_at.get(i, "")), half)
    if i % 4 == 0:
        enc.stdin.write(o.tobytes())
    if i in grab_at:
        cv2.imwrite(str(out / "grabs" / f"{grab_at[i]}_f{i}.jpg"), o,
                    [cv2.IMWRITE_JPEG_QUALITY, 80])
        tiles[grab_at[i]] = cv2.resize(o, (360, 640))
enc.stdin.close()
enc.wait()

blank = np.zeros((640, 360, 3), np.uint8)
rows = [np.hstack([tiles.get(f"rep{k + 1}_{ph}", blank) for ph in PHASES])
        for k in range(len(reps))]
cv2.imwrite(str(out / "phase_sheet.jpg"), np.vstack(rows),
            [cv2.IMWRITE_JPEG_QUALITY, 80])
print("wrote", sorted(p.name for p in out.iterdir()))
