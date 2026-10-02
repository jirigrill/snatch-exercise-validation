"""Phase times, definition v1 (wrist height) vs v2 (plate hub height).

usage: uv run python scripts/compare_phases.py out/4584
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

SIDE = "r"  # as in analyze.py
EVENTS = [f.name for f in fields(Rep)]

out = Path(sys.argv[1])
raw, plate = np.load(out / "raw_pose.npz"), np.load(out / "plate.npz")
kps, fps = raw["keypoints"], float(raw["fps"])
assert len(plate["hub_y"]) == len(kps), "plate and pose frame counts differ"
kps_s = smooth_keypoints(kps, fps)
common: dict[str, Any] = dict(
    nose_y=mid_y(kps_s, "nose"), hip_y=mid_y(kps_s, "hip"),
    knee=sagittal_angles(kps_s, SIDE)["knee"], fps=fps, knee_y=mid_y(kps_s, "knee"))
v1 = find_reps(wrist_y=mid_y(kps_s, "wrist"), **common)
v2 = find_reps_v2(hub_y=smooth(plate["hub_y"], fps), **common)
found = plate["found"]

(out / "phases_v2.json").write_text(json.dumps({
    "definition": "v2 (hub height for wrist height)", "fps": fps, "side": SIDE,
    "reps": [asdict(r) | {f"{k}_s": (None if v is None else round(v / fps, 3))
                          for k, v in asdict(r).items()} for r in v2],
    "hub_found_at_event": [{k: (None if v is None else bool(found[v]))
                            for k, v in asdict(r).items()} for r in v2],
}, indent=1))


def cell(f: int | None) -> str:
    return "—" if f is None else f"f{f} ({f / fps:.3f} s)"


lines = [f"# {out.name} — phase times, v1 (wrist) vs v2 (hub)", "",
         f"reps: v1 {len(v1)}, v2 {len(v2)}; hub found in {found.mean():.1%} "
         "of frames", "",
         "| rep | event | v1 | v2 | v2 − v1 (frames) | v2 − v1 (ms) |",
         "|---|---|---|---|---|---|"]
for k, (a, b) in enumerate(zip(v1, v2)):
    for e in EVENTS:
        fa, fb = getattr(a, e), getattr(b, e)
        d = None if fa is None or fb is None else fb - fa
        lines.append(f"| {k + 1} | {e} | {cell(fa)} | {cell(fb)} | "
                     f"{'—' if d is None else f'{d:+d}'} | "
                     f"{'—' if d is None else f'{1000 * d / fps:+.0f}'} |")
(out / "phases_v1_v2.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
