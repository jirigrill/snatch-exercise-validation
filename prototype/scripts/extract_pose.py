"""Decode a clip (rotation applied) and save raw RTMPose-x output to .npz.

usage: uv run python scripts/extract_pose.py ../vids/IMG_4584.MOV out/4584 [det.npz]

With det.npz (an earlier raw_pose.npz), its saved lifter boxes are reused and
only the pose model runs (the CPU-bound detector takes ~0.4-0.7 s/frame).
"""

import platform
import sys
import time
from pathlib import Path

import numpy as np

from snatch import pose
from snatch.video import frames, probe

clip, out_dir = sys.argv[1], Path(sys.argv[2])
det = np.load(sys.argv[3]) if len(sys.argv) > 3 else None
det_boxes = None if det is None else det["bbox"]
out_dir.mkdir(parents=True, exist_ok=True)
info = probe(clip)
print(info, flush=True)

t0 = time.time()


def progress(i):
    if i % 200 == 0:
        el = time.time() - t0
        print(f"frame {i}/{info.n_frames} {el:.0f}s", flush=True)


raw = pose.run(frames(clip, info), info.n_frames, det_boxes=det_boxes,
               progress=progress)
elapsed = time.time() - t0
if det is not None:
    raw["n_people"] = det["n_people"]
meta = dict(fps=info.fps, width=info.width, height=info.height,
            rotation=info.rotation, model=pose.MODEL_NAME,
            clip=Path(clip).name, seconds=elapsed, machine=platform.platform())
arrays: dict[str, np.ndarray] = raw | {k: np.asarray(v) for k, v in meta.items()}
np.savez_compressed(out_dir / "raw_pose.npz", allow_pickle=False, **arrays)
print(f"done {info.n_frames} frames in {elapsed:.0f}s", flush=True)
