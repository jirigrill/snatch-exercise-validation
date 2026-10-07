"""Pose the lifter in every frame (RTMPose-x) and save the raw output to .npz.

usage: uv run python scripts/extract_pose.py ../vids/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg.MOV out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg
       [--reps ../docs/reps.csv | --every N] [--person person.npz] [--name raw_pose]
       [--overlay [--overlay-step 4]]
reads  the lifter's box per frame from out/<clip>/person.npz (scripts/extract_person.py,
       run it first; --person names another file)
writes out/<clip>/<name>.npz   keypoints, scores, bbox, pose_bbox, n_people, metadata
       out/<clip>/overlay_<name>.mp4   with --overlay: skeleton and boxes on the video
                               (scripts/overlay_video.py)

Partial progress is saved to raw_pose_partial.npz every 500 frames; rerunning
the same command resumes from it.

With --reps, only the clip's pose_start:pose_end ranges from reps.csv are
posed (each rep plus padding; rests between reps are skipped). Arrays stay
indexed by clip frame, NaN outside the ranges; the ranges are saved as
frame_ranges.

With --every N, only every Nth frame is posed, following the previous
keypoints from sample to sample (a quick pass to find reps where the plate
track fails; snatch.reps). --name sets the output file (<name>.npz, default
raw_pose), e.g. to keep a full run.
"""

import csv
import platform
import sys
import time
from pathlib import Path

import numpy as np

from snatch import overlay, pose
from snatch.video import frames, probe, timestamps

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
name = option("--name") or "raw_pose"
person_arg = option("--person")
overlay_step = option("--overlay-step") or "4"
make_overlay = "--overlay" in args
if make_overlay:
    args.remove("--overlay")
clip, out_dir = args[0], Path(args[1])
out_dir.mkdir(parents=True, exist_ok=True)
person_path = Path(person_arg) if person_arg else out_dir / "person.npz"
if not person_path.exists():
    sys.exit(f"{person_path} not found: run scripts/extract_person.py {clip} {out_dir} first")
person = np.load(person_path)
info = probe(clip)
print(info, flush=True)
if len(person["bbox"]) != info.n_frames:
    sys.exit(f"{person_path} has {len(person['bbox'])} frames, the clip {info.n_frames}")
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

partial = out_dir / f"{name}_partial.npz"
resume, done = None, 0
if partial.exists():
    p = np.load(partial)
    resume, done = {k: p[k] for k in p.files if k != "done"}, int(p["done"])
    print(f"resuming from frame {done}", flush=True)

t0 = time.time()


def progress(i):
    if i % 200 == 0:
        el = time.time() - t0
        print(f"frame {i}/{info.n_frames} {el:.0f}s", flush=True)


def checkpoint(result, n):
    tmp = out_dir / f"{name}_tmp.npz"  # gitignored; rename keeps partial atomic
    np.savez(tmp, done=n, **result)
    tmp.replace(partial)


raw = pose.run(frames(clip, info), info.n_frames, person["bbox"],
               progress=progress, resume=resume, done=done, checkpoint=checkpoint,
               ranges=ranges, restart_gap=int(every) if every else 1)
elapsed = time.time() - t0
raw["n_people"] = person["n_people"]
meta = dict(fps=info.fps, t=timestamps(clip, info.fps), width=info.width, height=info.height,
            rotation=info.rotation, model=pose.MODEL_NAME,
            clip=Path(clip).name, seconds=elapsed, machine=platform.platform(),
            person_file=person_path.name, det_every=person["det_every"])
if ranges is not None:
    meta["frame_ranges"] = np.asarray(ranges, np.int64)
arrays: dict[str, np.ndarray] = raw | {k: np.asarray(v) for k, v in meta.items()}
np.savez_compressed(out_dir / f"{name}.npz", allow_pickle=False, **arrays)
partial.unlink(missing_ok=True)
print(f"done {info.n_frames} frames in {elapsed:.0f}s", flush=True)
if make_overlay:
    overlay.call_script(clip, out_dir / f"overlay_{name}.mp4", "--pose",
                        str(out_dir / f"{name}.npz"), "--person", str(person_path),
                        "--boxes", "--zoom", "--step", overlay_step)
