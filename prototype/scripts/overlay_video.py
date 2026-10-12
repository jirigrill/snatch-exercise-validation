"""Draw person boxes, pose skeletons and the plate outline on a clip (snatch.overlay).

usage: uv run python scripts/overlay_video.py ../vids/<clip>.MOV out.mp4
           [--person out/<clip>/person.npz] [--pose raw_pose.npz [--pose other.npz]]
           [--plate out/<clip>/plate.npz] [--boxes] [--zoom] [--step 4] [--fps 15]
           [--scale 0.5] [--start F] [--end F]
reads  the video and the npz files given; writes out.mp4

Layers: person boxes (thick = detector ran, thin = interpolated), pose skeleton
(one --pose: left red, right green; two: green = first, magenta = second),
plate outline + hub. With two --pose
files only frames posed in both are shown, each labelled with the largest joint
distance between the two runs; a red border marks frames above 10 px (compare
a fast run against a full run). --boxes also draws the crop given to the pose
model. --zoom crops to everything drawn; --step N
shows every Nth frame; --fps is the playback rate (240 fps footage, --step 4,
--fps 15 is 4x slow motion).

The pipeline scripts call this script with --overlay (extract_person.py,
extract_pose.py, track_plate.py).
"""

import argparse

import numpy as np

from snatch import overlay

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("clip")
ap.add_argument("out")
ap.add_argument("--person")
ap.add_argument("--pose", action="append", default=[])
ap.add_argument("--plate")
ap.add_argument("--boxes", action="store_true")
ap.add_argument("--zoom", action="store_true")
ap.add_argument("--step", type=int, default=4)
ap.add_argument("--fps", type=float, default=15.0)
ap.add_argument("--scale", type=float, default=0.5)
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int)
a = ap.parse_args()
if len(a.pose) > 2:
    ap.error("at most two --pose files")
if not (a.person or a.pose or a.plate):
    ap.error("nothing to draw: give --person, --pose and/or --plate")

load = lambda p: dict(np.load(p))  # noqa: E731
res = overlay.render(
    a.clip, a.out, person=load(a.person) if a.person else None,
    poses=[load(p) for p in a.pose], plate=load(a.plate) if a.plate else None,
    boxes=a.boxes, start=a.start, end=a.end, step=a.step, fps=a.fps, scale=a.scale,
    zoom=a.zoom)
print(f"wrote {a.out}: {res['frames']} frames at {a.fps:g} fps"
      + (f", {res['flagged']} flagged (> 10 px)" if len(a.pose) > 1 else ""))
