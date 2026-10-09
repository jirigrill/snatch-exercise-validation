"""One image strip per rep, to check the rep list's boundaries by eye.

usage: uv run python scripts/rep_sheets.py out/reps_proposed.csv [clip ...]
reads  the rep list (out/reps_proposed.csv), ../vids/<clip>.MOV
writes out/reps_check/<clip>_rep<k>.jpg  frames: pose_start, start (liftoff),
           4 evenly spaced inside the lift, end (bar down), pose_end
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from snatch.video import frames, probe

TILE_H = 360
rows = defaultdict(list)
with open(sys.argv[1], newline="") as f:
    for r in csv.DictReader(f):
        if r["rep"] and (len(sys.argv) < 3 or r["clip"] in sys.argv[2:]):
            rows[r["clip"]].append(r)
out = Path("out/reps_check")
out.mkdir(parents=True, exist_ok=True)

for clip, reps in rows.items():
    path = f"../vids/{clip}.MOV"
    info = probe(path)
    want: dict[int, list[tuple[int, int, str]]] = defaultdict(list)  # frame -> (rep, slot, label)
    for r in reps:
        s, e = int(r["start_frame"]), int(r["end_frame"])
        marks = ([(int(r["pose_start"]), "pose start"), (s, "liftoff")]
                 + [(int(x), f"{k}/5") for k, x in enumerate(np.linspace(s, e, 6)[1:-1], 1)]
                 + [(e - 1, "bar down"), (int(r["pose_end"]) - 1, "pose end")])
        for slot, (fr, label) in enumerate(marks):
            want[fr].append((int(r["rep"]), slot, f"{label} f{fr}"))
    tiles: dict[tuple[int, int], np.ndarray] = {}
    last = max(want)
    for i, img in enumerate(frames(path, info)):
        if i > last:
            break
        for rep, slot, label in want.get(i, []):
            t = cv2.resize(img, (int(TILE_H * img.shape[1] / img.shape[0]), TILE_H))
            for th, col in ((5, (0, 0, 0)), (2, (255, 255, 255))):
                cv2.putText(t, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, th)
            tiles[rep, slot] = t
    for r in reps:
        k = int(r["rep"])
        strip = np.hstack([tiles[k, s] for s in range(8)])
        cv2.imwrite(str(out / f"{clip}_rep{k}.jpg"), strip, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(clip, len(reps), "reps", flush=True)
