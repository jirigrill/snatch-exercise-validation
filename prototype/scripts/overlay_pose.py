"""Draw one or two raw_pose.npz runs on the video, to compare them by eye.

usage: uv run python scripts/overlay_pose.py ../vids/<clip>.MOV out/<clip>/raw_pose.npz [other.npz] out.mp4
           [--start F] [--end F] [--fps 30] [--scale 0.5] [--zoom]
reads  the video and the npz file(s); writes out.mp4

First file = green skeleton (reference), second = magenta. With two files only
frames posed in both are shown (a sparse run against a full run works). Each
frame is labelled with the frame number and the largest distance between the
two runs' joints; a red border marks frames above 10 px.
--zoom crops to the lifter. --fps is the playback rate (240 fps footage at 30 =
8x slow motion).
"""

import sys

import cv2
import numpy as np

from snatch.angles import COCO
from snatch.video import frames, probe

EDGES = [("shoulder", "elbow"), ("elbow", "wrist"), ("shoulder", "hip"), ("hip", "knee"),
         ("knee", "ankle")]
FLAG_PX = 10.0

args = sys.argv[1:]


def option(flag: str, default: str) -> str:
    if flag not in args:
        return default
    i = args.index(flag)
    value = args[i + 1]
    del args[i:i + 2]
    return value


zoom = "--zoom" in args
if zoom:
    args.remove("--zoom")
start, end = int(option("--start", "0")), int(option("--end", "-1"))
play_fps, scale = float(option("--fps", "30")), float(option("--scale", "0.5"))
clip, *npz_paths, out_path = args
runs = [np.load(p) for p in npz_paths]
kps = [r["keypoints"].astype(float) for r in runs]
info = probe(clip)
n = min(len(k) for k in kps)
end = n if end < 0 else min(end, n)

posed = np.all([~np.isnan(k).all((1, 2)) for k in kps], axis=0)
posed[:start], posed[end:] = False, False
show = np.flatnonzero(posed)
if not len(show):
    sys.exit("no frame is posed in all files within the range")
dist = (np.linalg.norm(kps[0] - kps[1], axis=-1) if len(kps) > 1 else None)


def skeleton(img: np.ndarray, k: np.ndarray, col: tuple[int, int, int], r: int) -> None:
    for side in ("l", "r"):
        for a, b in EDGES:
            pa, pb = k[COCO[f"{side}_{a}"]], k[COCO[f"{side}_{b}"]]
            if not (np.isnan(pa).any() or np.isnan(pb).any()):
                cv2.line(img, tuple(map(int, pa)), tuple(map(int, pb)), col, r)
    for p in k:
        if not np.isnan(p).any():
            cv2.circle(img, tuple(map(int, p)), r + 2, col, -1)


def text(img: np.ndarray, s: str, y: int) -> None:
    cv2.putText(img, s, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 8)
    cv2.putText(img, s, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)


writer = None
want = set(show.tolist())
flagged = 0
for i, img in enumerate(frames(clip, info)):
    if i > show[-1]:
        break
    if i not in want:
        continue
    img = img.copy()
    for k, col in zip(kps, ((0, 255, 0), (255, 0, 255))):
        skeleton(img, k[i], col, 4)
    text(img, f"f{i}", 60)
    if dist is not None:
        worst = np.nanmax(dist[i])
        text(img, f"max diff {worst:.1f} px", 120)
        if worst > FLAG_PX:
            flagged += 1
            cv2.rectangle(img, (0, 0), (img.shape[1] - 1, img.shape[0] - 1), (0, 0, 255), 24)
    if zoom:
        pts = np.concatenate([k[i] for k in kps])
        pts = pts[~np.isnan(pts).any(1)]
        (x0, y0), (x1, y1) = pts.min(0) - 150, pts.max(0) + 150
        img = img[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)]
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    if writer is None:
        size = (img.shape[1], img.shape[0])
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), play_fps, size)
    elif (img.shape[1], img.shape[0]) != size:  # zoom crop size changes: pad/resize
        img = cv2.resize(img, size)
    writer.write(img)
writer.release()
print(f"wrote {out_path}: {len(show)} frames at {play_fps:g} fps"
      + (f", {flagged} flagged (> {FLAG_PX:g} px)" if dist is not None else ""))
print("green = first file" + (", magenta = second file" if len(kps) > 1 else ""))
