"""How far do pose runs of one clip differ from a reference run (e.g. a full run)?

usage: uv run python scripts/compare_pose_runs.py ref.npz run1.npz [run2.npz ...] [--plate plate.npz]
reads  the raw_pose.npz files; with --plate also v2 phases (needs hub_y)
writes nothing (prints)

Per run: run time, crop shift (pose_bbox, px), right-side joint distances
(score >= 0.3 in both runs), smoothed joint-angle differences (hip, knee,
trunk, elbow; degrees) and, with --plate, the v2 phase frames' difference per
rep. Only frames posed in both files count.
"""

import sys
from dataclasses import asdict

import numpy as np

from snatch.angles import COCO, mid_y, sagittal_angles
from snatch.phases import find_reps_v2
from snatch.signals import smooth, smooth_keypoints

args = sys.argv[1:]
plate = None
if "--plate" in args:
    i = args.index("--plate")
    plate = np.load(args[i + 1])
    del args[i:i + 2]
ref = np.load(args[0])
fps = float(ref["fps"])
SIDE = [COCO[f"r_{n}"] for n in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")]


def phases(kps: np.ndarray) -> list[dict]:
    s = smooth_keypoints(kps, fps)
    return [asdict(r) for r in find_reps_v2(
        hub_y=smooth(plate["hub_y"], fps), nose_y=mid_y(s, "nose"), hip_y=mid_y(s, "hip"),
        knee=sagittal_angles(s, "r")["knee"], fps=fps, knee_y=mid_y(s, "knee"))]


posed = lambda r: ~np.isnan(r["keypoints"]).all((1, 2))  # noqa: E731
ref_k = ref["keypoints"].astype(float)
ref_ang = sagittal_angles(smooth_keypoints(ref_k, fps), "r")
ref_ph = phases(ref_k) if plate is not None else None
for path in args[1:]:
    run = np.load(path)
    both = posed(ref) & posed(run)
    k = run["keypoints"].astype(float)
    d = np.linalg.norm(ref_k - k, axis=-1)[both]
    ok = ((ref["scores"] >= 0.3) & (run["scores"] >= 0.3))[both]
    x = d[:, SIDE][ok[:, SIDE]]
    crop = np.linalg.norm(ref["pose_bbox"] - run["pose_bbox"], axis=1)[both]
    ang = sagittal_angles(smooth_keypoints(k, fps), "r")
    print(f"== {path}  ({float(run['seconds']):.0f} s, {int(both.sum())} frames compared)")
    print(f"  crop shift px          median {np.median(crop):.1f}  p95 {np.percentile(crop, 95):.1f}")
    print(f"  right-side joints px   median {np.median(x):.2f}  p95 {np.percentile(x, 95):.1f}  "
          f"p99 {np.percentile(x, 99):.1f}  max {x.max():.0f}  >10px {(x > 10).mean():.1%}")
    print("  angle |diff| deg (median/p95/max)  " + "  ".join(
        f"{j} {np.median(a):.1f}/{np.percentile(a, 95):.1f}/{a.max():.0f}"
        for j, a in ((j, np.abs(ang[j] - ref_ang[j])[both]) for j in ("hip", "knee", "trunk", "elbow"))))
    if plate is not None:
        ph = phases(k)
        if len(ph) != len(ref_ph):
            print(f"  v2 phases: rep count differs, reference {len(ref_ph)}, run {len(ph)}")
        for n, (a, b) in enumerate(zip(ref_ph, ph), 1):
            print(f"  v2 phases rep {n} (frames): " + " ".join(
                f"{e}:{'-' if a[e] is None or b[e] is None else b[e] - a[e]:+}" if a[e] is not None and b[e] is not None
                else f"{e}:-" for e in a))
