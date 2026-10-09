"""Near-plate tracking for oblique views, with a pose prior (D1 diagnostic only).

usage: uv run python scripts/studies/d1_near_plate.py ../vids/spike/<clip>.MOV out/<clip> --radius LO:HI
reads  out/<clip>/raw_pose.npz
writes out/<clip>/plate_near.npz (same fields as plate.npz), plate_near_check.jpg

In the 30 and 45 deg views both plates are in the image, and plate.detect
(shape and darkness only, no prior) follows the far plate or a round dark
object behind the lifter (sandbags at 45 deg) for long stretches
(docs/results/33-d1-views.md). This script runs the same plate.detect on
masked frames: inside each lift (v1 reps from the wrists, 1 s before liftoff
to the end of the overhead run) only pixels within R = 3.5 x r_hi of the
near wrist and on the near wrist's side of the bisector between the two
wrists are kept; the rest is painted grey. Outside the lifts the whole frame
is grey, so nothing is tracked there. The prior is the near wrist, which
breaks the "never from the wrists" rule of snatch.plate, so this is a
diagnostic for D1, not a pipeline step; plate.npz is left as it is.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from snatch import plate
from snatch.angles import COCO, mid_y, sagittal_angles
from snatch.phases import find_reps
from snatch.signals import smooth_keypoints
from snatch.video import frame_times, frames, mean_rate, probe

args = sys.argv[1:]
i = args.index("--radius")
r_lo, r_hi = (float(x) for x in args[i + 1].split(":"))
del args[i:i + 2]
clip, out = args[0], Path(args[1])
info = probe(clip)
raw = np.load(out / "raw_pose.npz")
t = frame_times(raw)
fps = mean_rate(t)
kps_s = smooth_keypoints(raw["keypoints"], fps)
reps = find_reps(wrist_y=mid_y(kps_s, "wrist"), nose_y=mid_y(kps_s, "nose"),
                 hip_y=mid_y(kps_s, "hip"), knee=sagittal_angles(kps_s, "r")["knee"],
                 fps=fps, knee_y=mid_y(kps_s, "knee"), t=t)
n = info.n_frames
span = np.zeros(n, bool)
for r in reps:
    span[max(r.setup - int(1.0 * fps), 0):r.overhead_end] = True
nw, fw = kps_s[:, COCO["r_wrist"]], kps_s[:, COCO["l_wrist"]]
R = 3.5 * r_hi
yy, xx = np.mgrid[0:info.height, 0:info.width].astype(np.float32)
GREY = 110


def masked():
    for k, img in enumerate(frames(clip, info)):
        o = np.full_like(img, GREY)
        if k < n and span[k]:
            keep = (xx - nw[k, 0]) ** 2 + (yy - nw[k, 1]) ** 2 < R ** 2
            d = fw[k] - nw[k]  # near side of the bisector: (p - mid) . d < 0
            mid = (nw[k] + fw[k]) / 2
            keep &= (xx - mid[0]) * d[0] + (yy - mid[1]) * d[1] < 0
            o[keep] = img[keep]
        yield o


res = plate.detect(masked, n, r_min=r_lo, r_max=r_hi, model="ellipse",
                   max_step_px=plate.MAX_STEP_PX * 240 / info.fps * info.width / 1080)
found = res["found"]
idx = np.flatnonzero(found)
step = np.hypot(np.diff(res["hub_x"][idx]), np.diff(res["hub_y"][idx]))
jumps = idx[1:][step > plate.MAX_STEP_PX * np.diff(idx) + 15]
status = (f"near-plate prior; found {found[span].mean():.1%} of lift frames, "
          f"{len(jumps)} jumps")
print(status, flush=True)
np.savez_compressed(out / "plate_near.npz", allow_pickle=False, **(res | {
    k: np.asarray(v) for k, v in dict(
        fps=info.fps, t=t, width=info.width, height=info.height, clip=Path(clip).name,
        plate_diameter_m=plate.PLATE_DIAMETER_M, status=status, model="ellipse",
        travel_m=0.0, jumps=jumps, lift_span=span).items()}))

# check image: 18 frames evenly spread over the lifts, full resolution crops
picks = [int(idx_) for idx_ in np.flatnonzero(span)[
    np.linspace(0, span.sum() - 1, 18).round().astype(int)]]
half = int(1.6 * r_hi)
tiles = {}
for k, img in enumerate(frames(clip, info)):
    if k > picks[-1]:
        break
    if k not in picks:
        continue
    o = img.copy()
    if found[k]:
        cx, cy, a, b, ang = (res[f][k] for f in ("hub_x", "hub_y", "a", "b", "angle"))
        cv2.ellipse(o, ((cx, cy), (2 * a, 2 * b), ang), (0, 255, 0), 2)
        label = f"f{k} a{a:.0f} b{b:.0f}"
    else:
        cx, cy = nw[k]
        label = f"f{k} NOT FOUND"
    cv2.circle(o, (int(nw[k, 0]), int(nw[k, 1])), 6, (0, 230, 255), -1)
    x0, y0 = int(cx) - half, int(cy) - half
    crop = cv2.copyMakeBorder(o, half, half, half, half, cv2.BORDER_CONSTANT)[
        y0 + half:y0 + 3 * half, x0 + half:x0 + 3 * half]
    crop = cv2.resize(crop, (360, 360))
    for th, c in ((5, (0, 0, 0)), (2, (255, 255, 255))):
        cv2.putText(crop, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, th)
    tiles[k] = crop
row = [tiles[k] for k in sorted(tiles)]
while len(row) % 6:
    row.append(np.zeros((360, 360, 3), np.uint8))
cv2.imwrite(str(out / "plate_near_check.jpg"),
            np.vstack([np.hstack(row[k:k + 6]) for k in range(0, len(row), 6)]),
            [cv2.IMWRITE_JPEG_QUALITY, 85])
print("wrote", out / "plate_near.npz")
