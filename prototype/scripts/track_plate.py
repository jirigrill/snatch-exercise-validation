"""Track the near plate per frame; bar path and check images.

usage: uv run python scripts/track_plate.py ../vids/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg.MOV out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg [ellipse]
       (ellipse: outline model for off-axis clips, 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg and 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg)
writes plate.npz (per-frame arrays, indexed like raw_pose.npz), plate.csv,
       plate_check.jpg (outline + hub, zoomed, at ~18 frames), bar_path.png
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
model = sys.argv[3] if len(sys.argv) > 3 else "circle"
out.mkdir(parents=True, exist_ok=True)
info = probe(clip)
t0 = time.time()


def progress(stage, i):
    if i % 500 == 0:
        print(f"{stage} {i}/{info.n_frames} {time.time() - t0:.0f}s", flush=True)


res = plate.detect(lambda: frames(clip, info), info.n_frames, progress=progress,
                   model=model)
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
            plate_diameter_m=plate.PLATE_DIAMETER_M, status=status, model=model,
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

# --- check image: zoomed on the plate at full resolution, so a fit that is
# off the rim by a few px is visible (thumbnails hid this). Evenly spaced
# found frames, the highest and lowest hub, up to 2 missed frames ---------
picks = set()
if len(idx):
    picks = {int(idx[k]) for k in np.linspace(0, len(idx) - 1, 14).round().astype(int)}
    picks |= {int(idx[np.nanargmin(res["hub_y"][idx])]),
              int(idx[np.nanargmax(res["hub_y"][idx])])}
missing = np.flatnonzero(~found)
picks |= {int(missing[k]) for k in
          np.linspace(0, len(missing) - 1, min(2, len(missing))).round().astype(int)}
half = int(1.45 * float(res["r0"]))  # crop half-size around the hub
tile = 360
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
        cv2.ellipse(o, ((cx, cy), (2 * a, 2 * b), ang), col, 2)
        cv2.circle(o, (int(cx), int(cy)), 4, (0, 0, 255), -1)
        label = f"f{i} a{a:.0f} b{b:.0f}"
    else:  # centre on the nearest found frame's hub
        k = int(idx[np.argmin(np.abs(idx - i))]) if len(idx) else 0
        cx, cy = (res["hub_x"][k], res["hub_y"][k]) if len(idx) else (
            info.width / 2, info.height / 2)
        label = f"f{i} NOT FOUND"
    x0, y0 = int(cx) - half, int(cy) - half
    crop = cv2.copyMakeBorder(o, half, half, half, half, cv2.BORDER_CONSTANT)[
        y0 + half:y0 + 3 * half, x0 + half:x0 + 3 * half]
    crop = cv2.resize(crop, (tile, tile))
    for th, c in ((5, (0, 0, 0)), (2, (255, 255, 255))):
        cv2.putText(crop, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, th)
    tiles[i] = crop
row = [tiles[i] for i in sorted(tiles)]
while len(row) % 6:
    row.append(np.zeros((tile, tile, 3), np.uint8))
cv2.imwrite(str(out / "plate_check.jpg"),
            np.vstack([np.hstack(row[k:k + 6]) for k in range(0, len(row), 6)]),
            [cv2.IMWRITE_JPEG_QUALITY, 85])

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
