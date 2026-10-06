"""Decode a clip (rotation applied) and save raw RTMPose-x output to .npz.

usage: uv run python scripts/extract_pose.py ../vids/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg.MOV out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg [det.npz]
       [--reps ../docs/reps.csv | --every N] [--det-every N [--interpolate]] [--name raw_pose]

Partial progress is saved to raw_pose_partial.npz every 500 frames; rerunning
the same command resumes from it.

With det.npz (an earlier raw_pose.npz), its saved lifter boxes are reused and
only the pose model runs (the CPU-bound detector takes ~0.4-0.7 s/frame).

With --reps, only the clip's pose_start:pose_end ranges from reps.csv are
posed (each rep plus padding; rests between reps are skipped). Arrays stay
indexed by clip frame, NaN outside the ranges; the ranges are saved as
frame_ranges.

With --every N, only every Nth frame is posed, following the lifter's box
from sample to sample (a quick pass to find reps where the plate track
fails; snatch.reps).

With --det-every N, the person detector (~95% of the time) runs only every Nth
posed frame; between, the crop follows the previous frame's keypoints. Name
the output to show the setup, e.g. --name raw_pose_det4.

With --interpolate (needs --det-every N, whole clip only), the detector runs
first on every Nth frame, the boxes in between are interpolated, and the pose
model then runs on every frame with the same crop recipe as a full run (box +
previous keypoints). Name e.g. --name raw_pose_det4interp. bbox holds the
interpolated boxes; n_people is 0 on frames the detector did not see.

--name sets the
output file (<name>.npz, default raw_pose), e.g. to keep a full run.
"""

import csv

import platform
import sys
import time
from pathlib import Path

import numpy as np

from snatch import pose
from snatch.video import frames, probe

args = sys.argv[1:]


def option(flag: str) -> str | None:
    if flag not in args:
        return None
    i = args.index(flag)
    value = args[i + 1]
    del args[i:i + 2]
    return value


reps_csv = option("--reps")
every = option("--every")
det_every = int(option("--det-every") or 1)
interpolate = "--interpolate" in args
if interpolate:
    args.remove("--interpolate")
name = option("--name") or "raw_pose"
clip, out_dir = args[0], Path(args[1])
det = np.load(args[2]) if len(args) > 2 else None
det_boxes = None if det is None else det["bbox"]
out_dir.mkdir(parents=True, exist_ok=True)
info = probe(clip)
print(info, flush=True)
ranges = None
if reps_csv is not None:
    with open(reps_csv, newline="") as f:
        ranges = [(int(r["pose_start"]), int(r["pose_end"])) for r in csv.DictReader(f)
                  if r["clip"] == Path(clip).stem]
    if not ranges:
        sys.exit(f"no rows for {Path(clip).stem} in {reps_csv}")
    print("ranges", ranges, flush=True)
if every is not None:
    ranges = [(i, i + 1) for i in range(0, info.n_frames, int(every))]
    print(f"every {every}th frame: {len(ranges)} frames", flush=True)

t0 = time.time()  # whole run, incl. the detector pass
seen_people = None
if interpolate:
    if det_every < 2 or ranges is not None or det_boxes is not None:
        sys.exit("--interpolate needs --det-every N (N > 1), and no --reps/--every/det.npz")
    t_det = time.time()
    boxes, seen_people = pose.detect_boxes(
        frames(clip, info), info.n_frames, det_every, pose.load_detector(),
        progress=lambda i: print(f"detector frame {i}/{info.n_frames} "
                                 f"{time.time() - t_det:.0f}s", flush=True) if i % 800 == 0 else None)
    det_boxes = pose.interpolate_boxes(boxes)
    print(f"detector done: {int((seen_people > 0).sum())} frames, "
          f"{time.time() - t_det:.0f}s", flush=True)

partial = out_dir / f"{name}_partial.npz"
resume, done = None, 0
if partial.exists():
    p = np.load(partial)
    resume, done = {k: p[k] for k in p.files if k != "done"}, int(p["done"])
    print(f"resuming from frame {done}", flush=True)


def progress(i):
    if i % 200 == 0:
        el = time.time() - t0
        print(f"frame {i}/{info.n_frames} {el:.0f}s", flush=True)


def checkpoint(result, n):
    tmp = out_dir / f"{name}_tmp.npz"  # gitignored; rename keeps partial atomic
    np.savez(tmp, done=n, **result)
    tmp.replace(partial)


raw = pose.run(frames(clip, info), info.n_frames, det_boxes=det_boxes,
               progress=progress, resume=resume, done=done, checkpoint=checkpoint,
               ranges=ranges, restart_gap=int(every) if every else 1,
               det_every=1 if interpolate else det_every)
elapsed = time.time() - t0
if det is not None:
    raw["n_people"] = det["n_people"]
if seen_people is not None:
    raw["n_people"] = seen_people
meta = dict(fps=info.fps, width=info.width, height=info.height,
            rotation=info.rotation, model=pose.MODEL_NAME,
            clip=Path(clip).name, seconds=elapsed, machine=platform.platform())
meta["det_every"] = det_every
meta["det_interpolated"] = interpolate
if ranges is not None:
    meta["frame_ranges"] = np.asarray(ranges, np.int64)
arrays: dict[str, np.ndarray] = raw | {k: np.asarray(v) for k, v in meta.items()}
np.savez_compressed(out_dir / f"{name}.npz", allow_pickle=False, **arrays)
partial.unlink(missing_ok=True)
print(f"done {info.n_frames} frames in {elapsed:.0f}s", flush=True)
