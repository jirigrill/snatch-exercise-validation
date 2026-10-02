"""Track the near plate per frame; bar path and check images.

usage: uv run python scripts/track_plate.py ../vids/IMG_4584.MOV out/4584
writes plate.npz (per-frame arrays, indexed like raw_pose.npz), plate.csv,
       plate_check.jpg (outline + hub at a few frames), bar_path.png
"""

import csv
import sys
import time
from pathlib import Path

import cv2
import matplotlib
import numpy as np

from snatch import plate
from snatch.video import frames, probe

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

clip, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
info = probe(clip)
t0 = time.time()


def progress(stage, i):
    if i % 500 == 0:
        print(f"{stage} {i}/{info.n_frames} {time.time() - t0:.0f}s", flush=True)


res = plate.detect(lambda: frames(clip, info), info.n_frames, progress=progress)
n, fps = info.n_frames, info.fps
found = res["found"]
print(f"found {found.sum()}/{n} frames ({found.mean():.1%}), ellipse fit "
      f"{res['ellipse_fit'].sum()}, r0 {float(res['r0']):.1f} px, "
      f"{time.time() - t0:.0f}s", flush=True)
# Sanity check, not proof: the bar must travel (every clip lifts it at least
# to the hips) and be found almost everywhere. A static look-alike circle
# (wall logo, shelf) fails the first test.
# A jump (track restart away from the previous position) means one side of
# it followed something else; the plate itself never teleports.
idx = np.flatnonzero(found)
travel_m, jumps = 0.0, np.empty(0, int)
if len(idx):
    travel_m = float(np.ptp(res["hub_y"][found]) / np.nanmedian(res["px_per_m"]))
    step = np.hypot(np.diff(res["hub_x"][idx]), np.diff(res["hub_y"][idx]))
    jumps = idx[1:][step > plate.MAX_STEP_PX * np.diff(idx) + 15]
reasons = []
if found.mean() < 0.9:
    reasons.append(f"found in only {found.mean():.0%} of frames")
if travel_m < 0.4:
    reasons.append(f"hub travels only {travel_m:.2f} m")
if len(jumps):
    reasons.append(f"{len(jumps)} jumps (frames {', '.join(map(str, jumps[:12]))})")
status = "ok" if not reasons else "check: " + "; ".join(reasons)
print(f"status {status} (vertical travel {travel_m:.2f} m)", flush=True)
meta = dict(fps=fps, width=info.width, height=info.height, clip=Path(clip).name,
            plate_diameter_m=plate.PLATE_DIAMETER_M, status=status,
            travel_m=travel_m, jumps=jumps)
arrays: dict[str, np.ndarray] = res | {k: np.asarray(v) for k, v in meta.items()}
np.savez_compressed(out / "plate.npz", allow_pickle=False, **arrays)

with open(out / "plate.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["frame", "t_s", *plate.FIELDS])
    for i in range(n):
        w.writerow([i, f"{i / fps:.5f}"] + [
            int(res[k][i]) if res[k].dtype == bool else
            ("" if np.isnan(res[k][i]) else f"{res[k][i]:.2f}")
            for k in plate.FIELDS])

# --- check image: outline + hub at evenly spaced found frames, plus the
# highest and lowest hub positions -----------------------------------------
picks = set()
if len(idx):
    picks = {int(idx[k]) for k in np.linspace(0, len(idx) - 1, 6).round().astype(int)}
    picks |= {int(idx[np.nanargmin(res["hub_y"][idx])]),
              int(idx[np.nanargmax(res["hub_y"][idx])])}
missing = np.flatnonzero(~found)
picks |= {int(missing[k]) for k in
          np.linspace(0, len(missing) - 1, min(2, len(missing))).round().astype(int)}
tiles, background = {}, None
for i, img in enumerate(frames(clip, info)):
    if i == 0:
        background = img.copy()
    if i not in picks:
        if i > max(picks, default=0):
            break
        continue
    o = img.copy()
    if found[i]:
        cx, cy, a, b, ang = (res[k][i] for k in ("hub_x", "hub_y", "a", "b", "angle"))
        col = (0, 255, 0) if res["ellipse_fit"][i] else (0, 255, 255)
        cv2.ellipse(o, ((cx, cy), (2 * a, 2 * b), ang), col, 4)
        cv2.circle(o, (int(cx), int(cy)), 8, (0, 0, 255), -1)
        label = f"f{i} hub ({cx:.0f},{cy:.0f}) {res['px_per_m'][i]:.0f} px/m"
    else:
        label = f"f{i} NOT FOUND"
    for th, c in ((8, (0, 0, 0)), (3, (255, 255, 255))):
        cv2.putText(o, label, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.3, c, th)
    tiles[i] = cv2.resize(o, (360, 640))
row = [tiles[i] for i in sorted(tiles)]
while len(row) % 5:
    row.append(np.zeros((640, 360, 3), np.uint8))
cv2.imwrite(str(out / "plate_check.jpg"),
            np.vstack([np.hstack(row[k:k + 5]) for k in range(0, len(row), 5)]),
            [cv2.IMWRITE_JPEG_QUALITY, 80])

# --- bar path ----------------------------------------------------------------
t = np.arange(n) / fps
fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(14, 9),
                               gridspec_kw={"width_ratios": [1, 1.6]})
if background is not None:
    ax0.imshow(background[..., ::-1], alpha=0.5)
sc = ax0.scatter(res["hub_x"], res["hub_y"], c=t, s=1, cmap="viridis")
ax0.set_xlim(0, info.width)
ax0.set_ylim(info.height, 0)
ax0.set_title("hub path (rotated frame px), colour = time")
fig.colorbar(sc, ax=ax0, label="t (s)", shrink=0.6)
ax1.plot(t, res["hub_y"], lw=0.8, label="hub y")
ax1.plot(t, res["hub_x"], lw=0.8, label="hub x")
ax1.invert_yaxis()
ax1.set_xlabel("time (s)")
ax1.set_ylabel("px")
ax1.legend()
ax1.set_title(f"found {found.mean():.1%} of frames")
fig.suptitle(f"{Path(clip).stem} — near plate hub")
fig.tight_layout()
fig.savefig(out / "bar_path.png", dpi=100)
print("wrote", out / "plate.npz", flush=True)
