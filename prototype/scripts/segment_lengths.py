"""Segment lengths (cm) from the near-side keypoints of the standing frames (body_height.py).

usage: uv run python scripts/segment_lengths.py out/<clip> [out/<clip> ...] [--side r|l]
reads  out/<clip>/raw_pose.npz, out/<clip>/height.json (frames, px_per_m_mid)
writes nothing; prints a markdown table (median over the clip's frames)

Keypoint to keypoint, so joint centres as RTMPose places them (not bony
landmarks): shank knee-ankle, thigh hip-knee, torso shoulder-hip, upper arm
shoulder-elbow, forearm elbow-wrist; ear-ankle and nose-ankle as a check of
the scale between clips (the body does not change, so a clip whose value
is off has an off scale). Scale: the clip's px_per_m_mid (bar-centre depth).
Side-on 2D lengths are projections: a segment pointing toward the camera
reads short (the torso is near the image plane; feet and hands less so).
"""

import json
import sys
from pathlib import Path

import numpy as np

from snatch.angles import COCO
from snatch.signals import smooth_keypoints

args = sys.argv[1:]
side = "r"
if "--side" in args:
    i = args.index("--side")
    side = args[i + 1]
    del args[i:i + 2]

SEG = {"shank": ("knee", "ankle"), "thigh": ("hip", "knee"), "torso": ("shoulder", "hip"),
       "upper arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"),
       "hip-ankle": ("hip", "ankle"),
       "ear-ankle": ("ear", "ankle"), "nose-ankle": (None, "ankle")}

print("| clip | frames | " + " | ".join(SEG) + " |")
print("|---|---|" + "---|" * len(SEG))
for d in map(Path, args):
    raw = np.load(d / "raw_pose.npz")
    h = json.loads((d / "height.json").read_text())
    kp = smooth_keypoints(raw["keypoints"], float(raw["fps"]))
    fr = [r["frame"] for r in h["rows"]]
    pm = h["summary"]["px_per_m_mid"]
    cells = []
    for a, b in SEG.values():
        ia = COCO["nose"] if a is None else COCO[f"{side}_{a}"]
        ib = COCO[f"{side}_{b}"]
        v = np.hypot(*(kp[fr, ia] - kp[fr, ib]).T) / pm * 100
        cells.append(f"{np.median(v):.1f}" if len(v) else "–")
    print(f"| {d.name} | {len(fr)} | " + " | ".join(cells) + " |")
