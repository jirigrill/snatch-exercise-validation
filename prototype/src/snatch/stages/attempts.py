"""S3: split the clip into attempts from the hub's height above the floor (snatch.reps.find_attempts).

Outputs
- attempts.json: `attempts`, one per pull that took the hub up to the athlete's knee height (a miss
  that never goes overhead counts): `attempt` (1-based), `start` (liftoff frame), `end` (first frame
  back on the floor, exclusive), `window` ([start - 1 s, end + 1 s) in frames: what S4 poses), `peak_m`
  (highest hub point above the real floor, m), `t` ([time of start, time of the last frame before end],
  s) and `plate_found` (share of [start, end) where S2 found the plate). `not_a_pull`: the other rises
  over 10 cm, `start`, `end`, `peak_m` (a nudge, a bounce after a drop). `params`: the numbers used.
  No empty `attempts` stops nothing here: S4 raises (the spec has no rule for it yet).
- overlays/3_attempts.mp4: "Attempt k of n" on frames inside an attempt, every other frame dimmed, the
  plate ring + hub as in 2_plate, and the hub height above the floor.

Stop (outputs are still written, no meta, so the stage reruns): exit 4 `plate_track_failed` when the plate
is found in under 90 % of the frames inside an attempt (the S2 check, redone where it matters).
"""

import json
from pathlib import Path

import numpy as np

from snatch import overlay
from snatch.plate import PLATE_DIAMETER_M
from snatch.reps import Lift, find_attempts, height_above_floor, pose_range
from snatch.stage import ATHLETE, CLIP, Context, Stage, StageStop
from snatch.stages.plate import MIN_MOVING_FOUND, TRACK_FAILED_EXIT

OVERLAY = "overlays/3_attempts.mp4"
LIFT_M = 0.10  # a rise above this is a candidate
REST_M = 0.03  # at or below this the bar rests on the floor
PAD_S = 1.0  # window padding either side


def describe(attempts: list[Lift], other: list[Lift], t: np.ndarray, found: np.ndarray,
             n: int) -> tuple[list[dict], list[dict]]:
    """The attempts.json entries: attempts (with window and plate share) and not_a_pull."""
    out = []
    for k, a in enumerate(attempts, 1):
        s, e = pose_range(a, t, n, PAD_S, PAD_S)
        out.append(dict(attempt=k, start=a.start, end=a.end, window=[s, e], peak_m=round(a.peak_m, 4),
                        t=[float(t[a.start]), float(t[a.end - 1])],
                        plate_found=round(float(found[a.start:a.end].mean()), 4)))
    return out, [dict(start=o.start, end=o.end, peak_m=round(o.peak_m, 4)) for o in other]


def run(ctx: Context, tmp: Path) -> None:
    plate = dict(np.load(ctx.path("plate.npz")))
    t = np.load(ctx.path("frame_times.npy"))
    knee = float(json.loads(ctx.path(ATHLETE).read_text())["knee_height_m"])
    found = np.asarray(plate["found"], bool)
    if len(found) != len(t):
        raise ValueError(f"plate.npz has {len(found)} frames, frame_times.npy {len(t)}")
    radius = PLATE_DIAMETER_M / 2
    rise = height_above_floor(plate["hub_y"], found, plate["px_per_m"], t)
    attempts, other = find_attempts(rise, knee, radius, LIFT_M, REST_M)
    entries, not_a_pull = describe(attempts, other, t, found, len(t))
    params = dict(lift_m=LIFT_M, rest_m=REST_M, knee_height_m=knee, plate_radius_m=radius, pad_s=PAD_S)
    (tmp / "attempts.json").write_text(json.dumps(
        dict(attempts=entries, not_a_pull=not_a_pull, params=params), indent=2) + "\n")

    inside = np.zeros(len(t), bool)
    which = np.zeros(len(t), int)
    for a in entries:
        inside[a["start"]:a["end"]] = True
        which[a["start"]:a["end"]] = a["attempt"]

    def labels(i: int) -> list[str]:
        banner = [f"Attempt {which[i]} of {len(entries)}"] if inside[i] else []
        return [*banner, f"hub {rise[i] + radius:.2f} m above floor"]

    if found.any():
        (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
        overlay.render(str(ctx.clip), str(tmp / OVERLAY), plate=plate, step=4, zoom=True,
                       dim=~inside, frame_labels=labels)
    print(f"S3 {len(entries)} attempts {[tuple(a['window']) for a in entries]}, "
          f"{len(not_a_pull)} not_a_pull", flush=True)
    for a in entries:
        if a["plate_found"] < MIN_MOVING_FOUND:
            raise StageStop(TRACK_FAILED_EXIT, "plate_track_failed",
                            f"Plate track unusable in {ctx.clip.name}: found in {a['plate_found']:.0%} of "
                            f"attempt {a['attempt']} (frames {a['start']}-{a['end']}, need {MIN_MOVING_FOUND:.0%}).")


STAGE = Stage("S3", (CLIP, "plate.npz", "clip.json", "frame_times.npy", ATHLETE), ("attempts.json", OVERLAY), run)
