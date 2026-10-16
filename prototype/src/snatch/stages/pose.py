"""S4: pose the lifter (snatch.pose) and find which way they face.

Analyze poses only the attempt windows of S3 (attempts.json; padding included),
--calibrate the whole clip. raw_pose.npz arrays stay indexed by clip frame (NaN
keypoints outside the windows) and carry the frame times of S-1 as `t` and the
posed `ranges` ([start, end) frames; the whole clip for --calibrate). The facing
and near-side check reads only the padding frames of the windows (inside a
window, outside [start, end) of its attempt: the lifter stands there, no plate
in front of the legs); --calibrate reads the whole clip. facing.json holds `facing`: "right" or
"left", the way the toes point in the image, with the votes and leg scores it
came from. The near side follows from it (pose.SIDE_OF), and the leg the model
scores higher must be that side, else the clip is mirrored or the legs are
swapped. No facing majority, or a disagreement, stops with exit 8.
Progress goes to raw_pose_partial.npz in out/<clip> every 500 frames, tagged
with the stage hash; a rerun with the same inputs resumes from it.
"""

import json
import platform
import time
from pathlib import Path

import numpy as np

from snatch import overlay, pose
from snatch.stage import CLIP, Context, Stage, StageStop, stage_hash
from snatch.video import frames, probe

FACING_EXIT = 8
OVERLAY = "overlays/4_pose.mp4"
PARTIAL = "raw_pose_partial.npz"


def check_facing(kps: np.ndarray, scores: np.ndarray) -> dict:
    """facing.json: facing, its votes and the leg scores; StageStop (exit 8) without a clear facing."""
    right, left = pose.facing_votes(kps, scores)
    votes = f"toe votes right {right}, left {left}"
    face = pose.facing(kps, scores)
    if face is None:
        raise StageStop(FACING_EXIT, "facing_ambiguous", f"facing ambiguous: {votes}")
    near = pose.near_side(scores)
    if near != pose.SIDE_OF[face]:
        raise StageStop(FACING_EXIT, "facing_ambiguous",
                        f"facing {face} ({votes}) but the {near} leg scores higher "
                        f"({pose.leg_scores(scores)}): mirrored clip or swapped legs?")
    return {"facing": face, "votes": {"right": right, "left": left}, "leg_scores": pose.leg_scores(scores)}


def _resume(path: Path, digest: str) -> tuple[dict[str, np.ndarray] | None, int]:
    if not path.exists():
        return None, 0
    p = np.load(path)
    if str(p["hash"]) != digest:
        path.unlink()
        return None, 0
    print(f"S4 resuming from frame {int(p['done'])}", flush=True)
    return {k: p[k] for k in p.files if k not in ("done", "hash")}, int(p["done"])


def windows(ctx: Context) -> tuple[list[tuple[int, int]], np.ndarray]:
    """(posing windows, mask of the padding frames) from attempts.json."""
    attempts = json.loads(ctx.path("attempts.json").read_text())["attempts"]
    if not attempts:
        raise ValueError("no attempts in attempts.json")
    n = len(np.load(ctx.path("frame_times.npy")))
    ranges = [(int(a["window"][0]), int(a["window"][1])) for a in attempts]
    padding = np.zeros(n, bool)
    for s, e in ranges:
        padding[s:e] = True
    for a in attempts:
        padding[a["start"]:a["end"]] = False
    return ranges, padding


def _run(ctx: Context, tmp: Path, stage: Stage, from_attempts: bool) -> None:
    clip = json.loads(ctx.path("clip.json").read_text())
    t = np.load(ctx.path("frame_times.npy"))
    person = np.load(ctx.path("person.npz"))
    info = probe(str(ctx.clip))
    if len(person["bbox"]) != len(t) or info.n_frames != len(t):
        raise ValueError(f"{info.n_frames} frames decode, person.npz has {len(person['bbox'])}, "
                         f"frame_times.npy {len(t)}")
    ranges, padding = windows(ctx) if from_attempts else ([(0, info.n_frames)], None)
    partial, digest = ctx.out / PARTIAL, stage_hash(stage, ctx)
    resume, done = _resume(partial, digest)

    def checkpoint(result: dict[str, np.ndarray], n: int) -> None:
        part = ctx.out / f".{PARTIAL}"
        with part.open("wb") as f:
            np.savez(f, allow_pickle=False, **result, done=np.asarray(n), hash=np.asarray(digest))
        part.replace(partial)

    t0 = time.time()
    raw = pose.run(frames(str(ctx.clip), info), info.n_frames, person["bbox"], resume=resume, done=done,
                   checkpoint=checkpoint, ranges=ranges,
                   progress=lambda i: print(f"S4 pose frame {i}/{info.n_frames} {time.time() - t0:.0f}s",
                                            flush=True) if i % 800 == 0 else None)
    partial.unlink(missing_ok=True)
    on = padding if padding is not None else slice(None)
    facing = check_facing(raw["keypoints"][on], raw["scores"][on])
    meta = dict(fps=clip["fps"], t=t, width=info.width, height=info.height, rotation=info.rotation,
                model=pose.MODEL_NAME, clip=ctx.clip.name, seconds=time.time() - t0,
                machine=platform.platform(), det_every=person["det_every"])
    arrays = (raw | {"n_people": person["n_people"], "ranges": np.asarray(ranges, int)}
              | {k: np.asarray(v) for k, v in meta.items()})
    np.savez_compressed(tmp / "raw_pose.npz", allow_pickle=False, **arrays)
    (tmp / "facing.json").write_text(json.dumps(facing, indent=2) + "\n")
    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    notes = (f"facing {facing['facing']}, near {pose.SIDE_OF[facing['facing']]}", "L red, R green")
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), person=dict(person), poses=[arrays], boxes=True,
                   step=4, zoom=True, notes=notes)


def run_analyze(ctx: Context, tmp: Path) -> None:
    _run(ctx, tmp, STAGE, True)


def run_calibrate(ctx: Context, tmp: Path) -> None:
    _run(ctx, tmp, CALIBRATE_STAGE, False)


INPUTS = (CLIP, "clip.json", "frame_times.npy", "person.npz")
OUTPUTS = ("raw_pose.npz", "facing.json", OVERLAY)
STAGE = Stage("S4", (*INPUTS, "attempts.json"), OUTPUTS, run_analyze)
CALIBRATE_STAGE = Stage("S4", INPUTS, OUTPUTS, run_calibrate)  # --calibrate: no S3, the whole clip
