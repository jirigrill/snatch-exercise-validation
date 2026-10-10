"""Phase times, definition v1 (wrist height) vs v2 (plate hub height).

usage: uv run python scripts/compare_phases.py out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg
reads  out/<clip>/raw_pose.npz, out/<clip>/plate.npz
writes out/<clip>/phases_v2.json, out/<clip>/phases_v1_v2.md
"""

import json
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

import numpy as np

from snatch.angles import mid_y, sagittal_angles
from snatch.phases import Rep, find_reps, find_reps_v2
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frame_times, mean_rate

SIDE = "r"  # as in analyze.py
EVENTS = [f.name for f in fields(Rep)]

out = Path(sys.argv[1])
raw, plate = np.load(out / "raw_pose.npz"), np.load(out / "plate.npz")
kps = raw["keypoints"]
t = frame_times(raw)  # real frame times: 2026-10-05 drops frames
fps = mean_rate(t)  # for windows in frames
n = len(kps)
assert len(plate["hub_y"]) == len(kps), "plate and pose frame counts differ"
kps_s = smooth_keypoints(kps, fps, t)
common: dict[str, Any] = dict(
    nose_y=mid_y(kps_s, "nose"), hip_y=mid_y(kps_s, "hip"),
    knee=sagittal_angles(kps_s, SIDE)["knee"], fps=fps, knee_y=mid_y(kps_s, "knee"), t=t)
v1 = find_reps(wrist_y=mid_y(kps_s, "wrist"), **common)
v2 = find_reps_v2(hub_y=smooth(plate["hub_y"], fps, t=t), **common)
found = plate["found"]

(out / "phases_v2.json").write_text(json.dumps({
    "definition": "v2 (hub height for wrist height)", "fps": fps, "side": SIDE,
    "reps": [asdict(r) | {f"{k}_s": (None if v is None else round(float(t[min(v, n - 1)]), 3))
                          for k, v in asdict(r).items()} for r in v2],
    "hub_found_at_event": [{k: (None if v is None or v >= len(found) else bool(found[v]))
                            for k, v in asdict(r).items()} for r in v2],
}, indent=1))


def cell(f: int | None) -> str:
    return "—" if f is None else f"f{f} ({t[min(f, n - 1)]:.3f} s)"


lines = [f"# {out.name} — phase times, v1 (wrist) vs v2 (hub)", "",
         f"reps: v1 {len(v1)}, v2 {len(v2)}; hub found in {found.mean():.1%} "
         "of frames", "",
         "| rep | event | v1 | v2 | v2 − v1 (frames) | v2 − v1 (ms) |",
         "|---|---|---|---|---|---|"]
for k, (a, b) in enumerate(zip(v1, v2)):
    for e in EVENTS:
        fa, fb = getattr(a, e), getattr(b, e)
        d = None if fa is None or fb is None else fb - fa
        ms = None if d is None else 1000 * float(t[min(fb, n - 1)] - t[min(fa, n - 1)])
        lines.append(f"| {k + 1} | {e} | {cell(fa)} | {cell(fb)} | "
                     f"{'—' if d is None else f'{d:+d}'} | "
                     f"{'—' if ms is None else f'{ms:+.0f}'} |")
(out / "phases_v1_v2.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
