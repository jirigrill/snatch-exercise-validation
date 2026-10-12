"""S1: find the lifter's box in every frame (snatch.person) and draw it.

The detector runs every DEFAULT_DET_EVERY-th frame, the boxes between are
interpolated. person.npz carries the frame times of S-1 as `t`. The overlay
draws a thick box where the detector found the lifter, a thin one where the box
is interpolated, and a red one across a detection the detector missed.
"""

import json
import platform
import time
from pathlib import Path

import numpy as np

from snatch import overlay, person
from snatch.stage import CLIP, Context, Stage
from snatch.video import frames, probe

OVERLAY = "overlays/1_person.mp4"


def run(ctx: Context, tmp: Path) -> None:
    clip = json.loads(ctx.path("clip.json").read_text())
    t = np.load(ctx.path("frame_times.npy"))
    info = probe(str(ctx.clip))
    if info.n_frames != len(t):
        raise ValueError(f"{info.n_frames} frames decode, frame_times.npy has {len(t)}")
    t0 = time.time()
    res = person.detect(
        frames(str(ctx.clip), info), info.n_frames, person.DEFAULT_DET_EVERY, person.load_detector(),
        progress=lambda i: print(f"S1 detector frame {i}/{info.n_frames} {time.time() - t0:.0f}s",
                                 flush=True) if i % 800 == 0 else None)
    meta = dict(fps=clip["fps"], t=t, width=info.width, height=info.height, rotation=info.rotation,
                model=person.DETECTOR_NAME, clip=ctx.clip.name, seconds=time.time() - t0,
                machine=platform.platform(), det_every=person.DEFAULT_DET_EVERY)
    arrays = res | {k: np.asarray(v) for k, v in meta.items()}
    np.savez_compressed(tmp / "person.npz", allow_pickle=False, **arrays)
    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), person=arrays, step=4, zoom=True)


STAGE = Stage("S1", (CLIP, "clip.json", "frame_times.npy"), ("person.npz", OVERLAY), run)
