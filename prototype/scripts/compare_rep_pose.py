"""Does posing only the rep ranges change anything? Full run vs per-rep run.

usage: uv run python scripts/compare_rep_pose.py out/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg
reads  out/<clip>/raw_pose.npz (full clip), raw_pose_reps.npz (extract_pose.py
       --reps --name raw_pose_reps), plate.npz
writes out/<clip>/rep_pose_check.md

Tracking restarts at each range start (snatch.pose.run), so the first frames
of a range may differ from the full run until the crop settles; the padding
before liftoff is meant to absorb that. Checked here: keypoint differences
inside the ranges (per second from the range start), and the v2 phase frames
from both runs.
"""

import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from snatch.angles import mid_y, sagittal_angles
from snatch.phases import find_reps_v2
from snatch.signals import smooth, smooth_keypoints

SIDE = "r"  # as in analyze.py
MIN_SCORE = 0.3

out = Path(sys.argv[1])
full, reps = np.load(out / "raw_pose.npz"), np.load(out / "raw_pose_reps.npz")
plate = np.load(out / "plate.npz")
fps = float(full["fps"])
ranges = [tuple(map(int, r)) for r in reps["frame_ranges"]]


def phases(kps: np.ndarray) -> list[dict]:
    s = smooth_keypoints(kps, fps)
    return [asdict(r) for r in find_reps_v2(
        hub_y=smooth(plate["hub_y"], fps), nose_y=mid_y(s, "nose"), hip_y=mid_y(s, "hip"),
        knee=sagittal_angles(s, SIDE)["knee"], fps=fps, knee_y=mid_y(s, "knee"))]


lines = [f"# {out.name} — pose on rep ranges vs full clip", "",
         f"ranges {ranges}; keypoints with score ≥ {MIN_SCORE} in both runs", "",
         "| range | seconds from range start | frames | median px | p95 px | max px |",
         "|---|---|---|---|---|---|"]
for a, b in ranges:
    d = np.linalg.norm(full["keypoints"][a:b] - reps["keypoints"][a:b], axis=-1)
    ok = (full["scores"][a:b] >= MIN_SCORE) & (reps["scores"][a:b] >= MIN_SCORE)
    for s0 in range(int(np.ceil((b - a) / fps))):
        f0, f1 = int(s0 * fps), min(b - a, int((s0 + 1) * fps))
        x = d[f0:f1][ok[f0:f1]]
        lines.append(f"| {a}:{b} | {s0}–{s0 + 1} | {f1 - f0} | {np.median(x):.1f} | "
                     f"{np.percentile(x, 95):.1f} | {x.max():.1f} |")
    same = np.all(full["keypoints"][a:b] == reps["keypoints"][a:b], axis=(1, 2))
    first_same = int(np.argmax(same)) if same.any() else None
    lines.append("")
    lines.append(f"Frames bit-identical to the full run: {same.mean():.1%}; first at "
                 f"{'never' if first_same is None else f'+{first_same} frames ({first_same / fps:.2f} s)'}"
                 " after the range start.")
    lines.append("")

p_full, p_reps = phases(full["keypoints"]), phases(reps["keypoints"])
lines += ["## v2 phase frames", "", "| rep | event | full | rep ranges | Δ frames |",
          "|---|---|---|---|---|"]
for k, (x, y) in enumerate(zip(p_full, p_reps), 1):
    for e in x:
        dx = None if x[e] is None or y[e] is None else y[e] - x[e]
        lines.append(f"| {k} | {e} | {x[e]} | {y[e]} | {'—' if dx is None else f'{dx:+d}'} |")
if len(p_full) != len(p_reps):
    lines.append(f"\nRep count differs: full {len(p_full)}, rep ranges {len(p_reps)}.")
(out / "rep_pose_check.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
