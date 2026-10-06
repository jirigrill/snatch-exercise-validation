"""Find the lifter's box in every frame and save it (person.npz); the pose step reads it.

usage: uv run python scripts/extract_person.py ../vids/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg.MOV out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg
           [--det-every 24] [--name person] [--overlay [--overlay-step 4]]
writes out/<clip>/<name>.npz   bbox (n_frames, 4) lifter box, interpolated between
                               detections; detected (n_frames,) True where the detector
                               ran; n_people (n_frames,); fps, width, height, rotation,
                               model, clip, seconds, machine, det_every
       out/<clip>/overlay_<name>.mp4   with --overlay: the box on the video
                               (scripts/overlay_video.py; thick = detected, thin = interpolated)

The YOLOX-x detector is ~95% of the pose pipeline's time (~0.4 s/frame on the CPU),
so it runs once per clip and every --det-every-th frame only; the boxes between are
interpolated (snatch.person). 24 (0.1 s at 240 fps) differs from a run on every
frame by ~1.5 px median at the pose keypoints and about 1 deg at the joint angles
(8 clips of 2026-10-01, docs/pipeline.html). --det-every 1 detects every frame.
"""

import platform
import sys
import time
from pathlib import Path

import numpy as np

from snatch import overlay, person
from snatch.video import frames, probe

args = sys.argv[1:]


def option(flag: str) -> str | None:
    if flag not in args:
        return None
    i = args.index(flag)
    value = args[i + 1]
    del args[i:i + 2]
    return value


det_every = int(option("--det-every") or person.DEFAULT_DET_EVERY)
name = option("--name") or "person"
overlay_step = option("--overlay-step") or "4"
make_overlay = "--overlay" in args
if make_overlay:
    args.remove("--overlay")
clip, out_dir = args[0], Path(args[1])
out_dir.mkdir(parents=True, exist_ok=True)
info = probe(clip)
print(info, flush=True)

t0 = time.time()
res = person.detect(
    frames(clip, info), info.n_frames, det_every, person.load_detector(),
    progress=lambda i: print(f"detector frame {i}/{info.n_frames} {time.time() - t0:.0f}s",
                             flush=True) if i % 800 == 0 else None)
elapsed = time.time() - t0
meta = dict(fps=info.fps, width=info.width, height=info.height, rotation=info.rotation,
            model=person.DETECTOR_NAME, clip=Path(clip).name, seconds=elapsed,
            machine=platform.platform(), det_every=det_every)
arrays: dict[str, np.ndarray] = res | {k: np.asarray(v) for k, v in meta.items()}
np.savez_compressed(out_dir / f"{name}.npz", allow_pickle=False, **arrays)
print(f"done {int(res['detected'].sum())} detections on {info.n_frames} frames in {elapsed:.0f}s",
      flush=True)
if make_overlay:
    overlay.call_script(clip, out_dir / f"overlay_{name}.mp4", "--person",
                        str(out_dir / f"{name}.npz"), "--zoom", "--step", overlay_step)
