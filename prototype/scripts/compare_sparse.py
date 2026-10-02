"""Does running the detector only every Nth frame change the results?

Reuses the saved every-frame detector boxes, keeps every Nth, tracks the crop
from the previous frame's keypoints in between, reruns pose, and compares
angles, phase frames and the SD table with the every-frame run.

usage: uv run python scripts/compare_sparse.py ../vids/IMG_4584.MOV out/4584 8 24
"""

import sys
from pathlib import Path

import numpy as np

from snatch import pose
from snatch.angles import JOINTS, mid_y, sagittal_angles
from snatch.phases import find_reps
from snatch.signals import smooth
from snatch.spread import PHASES as PHASES_ORDER, phase_values, spread_table
from snatch.video import frames, probe


def analyse(kps: np.ndarray, fps: float):
    kps_s = np.stack([np.stack([smooth(kps[:, j, d], fps) for d in (0, 1)], -1)
                      for j in range(17)], 1)
    ang = sagittal_angles(kps_s)
    reps = find_reps(wrist_y=mid_y(kps_s, "wrist"), nose_y=mid_y(kps_s, "nose"),
                     hip_y=mid_y(kps_s, "hip"), knee=ang["knee"], fps=fps,
                     knee_y=mid_y(kps_s, "knee"))
    return ang, reps, spread_table(phase_values(ang, reps))


clip, out = sys.argv[1], Path(sys.argv[2])
ref = np.load(out / "raw_pose.npz")
fps = float(ref["fps"])
info = probe(clip)
ang0, reps0, sd0 = analyse(ref["keypoints"], fps)
lift = np.zeros(len(ref["keypoints"]), bool)  # setup..lockout of every rep
for r in reps0:
    lift[r.setup:r.lockout + 1] = True

for every in map(int, sys.argv[3:]):
    raw = pose.run(frames(clip, info), info.n_frames,
                   det_boxes=pose.sparse_detections(ref["bbox"], every))
    ang, reps, sd = analyse(raw["keypoints"], fps)
    px = np.linalg.norm(raw["keypoints"] - ref["keypoints"], axis=2)
    print(f"\n=== detector every {every} frames "
          f"({fps / every:.0f} Hz, {info.n_frames // every} detector runs)")
    print(f"keypoint shift vs every-frame, during lifts: median "
          f"{np.median(px[lift]):.1f} px, 99th pct {np.percentile(px[lift], 99):.1f} px")
    for j in JOINTS:
        d = np.abs(ang[j] - ang0[j])[lift]
        print(f"  {j:5s} angle diff during lifts: median {np.median(d):.2f}, "
              f"max {d.max():.2f} deg")
    same = [tuple(getattr(a, p) for p in PHASES_ORDER) ==
            tuple(getattr(b, p) for p in PHASES_ORDER) for a, b in zip(reps, reps0)]
    print(f"  reps found {len(reps)} (ref {len(reps0)}); phase frames identical: {same}")
    for a, b in zip(reps, reps0):
        print("   ", {p: (getattr(a, p), getattr(b, p)) for p in PHASES_ORDER})
    print("  SD (sparse vs every-frame):")
    for j in JOINTS:
        print(f"    {j:5s} " + "  ".join(f"{sd[j][p]:5.1f}/{sd0[j][p]:4.1f}"
                                         for p in PHASES_ORDER))
