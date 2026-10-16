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
  plate ring + hub as in 2_plate, and the hub height above the floor. Every 4th frame plus `key_frames`.
- attempts.png: hub height above the floor (m) over time, gaps where S2 lost the plate. Red dashed: the
  knee gate; orange: the candidate threshold (plate radius + 10 cm); blue dotted: rest (radius + 3 cm).
  Green = an attempt (dot = its peak, labelled in m), grey = its 1 s window padding (what S4 poses),
  orange = a not_a_pull. Thin vertical lines = the key frames, `f<frame>`: each attempt's liftoff, peak
  and back on the floor (not when the clip ends first), the highest not_a_pull's peak. An attempt's
  dot must sit above the red line; the liftoff and floor lines must sit on the blue one.

Stop (outputs are still written, no meta, so the stage reruns): exit 4 `plate_track_failed` when the plate
is found in under 90 % of the frames inside an attempt (the S2 check, redone where it matters).
"""

import json
from pathlib import Path

import matplotlib
import numpy as np

from snatch import overlay
from snatch.plate import PLATE_DIAMETER_M
from snatch.reps import Lift, find_attempts, height_above_floor, pose_range
from snatch.stage import ATHLETE, CLIP, Context, Stage, StageStop
from snatch.stages.plate import MIN_MOVING_FOUND, TRACK_FAILED_EXIT

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

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


def key_frames(rise: np.ndarray, attempts: list[Lift], other: list[Lift]) -> list[int]:
    """Frames that prove the split, sorted: per attempt its start (last frame at rest before liftoff), its
    peak, and end - 1 (first frame back at rest; only when the bar rests again before the clip ends); the
    peak of the highest not_a_pull."""
    keys: set[int] = set()
    for a in attempts:
        keys |= {a.start, a.start + int(np.nanargmax(rise[a.start:a.end]))}
        if a.end < len(rise):
            keys.add(a.end - 1)
    if other:
        o = max(other, key=lambda x: x.peak_m)
        keys.add(o.start + int(np.nanargmax(rise[o.start:o.end])))
    return sorted(keys)


def write_plot(path: Path, t: np.ndarray, rise: np.ndarray, radius: float, entries: list[dict],
               not_a_pull: list[dict], keys: list[int], params: dict) -> None:
    """attempts.png (see the module docstring)."""
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(t, rise + radius, lw=0.9, color="black")
    tt = lambda i: t[min(i, len(t) - 1)]  # noqa: E731
    knee = params["knee_height_m"]
    for y, c, ls, name in ((knee, "red", "--", f"knee gate {knee:.2f} m"),
                           (radius + params["lift_m"], "orange", "-", "candidate: radius + lift"),
                           (radius + params["rest_m"], "blue", ":", "rest: radius + rest")):
        ax.axhline(y, color=c, ls=ls, lw=1, label=name)
    for a in entries:
        s, e = a["window"]
        ax.axvspan(tt(s), tt(a["start"]), color="grey", alpha=0.2, lw=0)
        ax.axvspan(tt(a["end"] - 1), tt(e - 1), color="grey", alpha=0.2, lw=0)
        ax.axvspan(tt(a["start"]), tt(a["end"] - 1), color="green", alpha=0.2, lw=0)
        pk = a["start"] + int(np.nanargmax(rise[a["start"]:a["end"]]))
        ax.plot(t[pk], a["peak_m"], "o", color="green")
        ax.annotate(f"Attempt {a['attempt']}\npeak {a['peak_m']:.2f} m", (t[pk], a["peak_m"]),
                    textcoords="offset points", xytext=(8, -30), color="darkgreen")
    for o in not_a_pull:
        ax.axvspan(tt(o["start"]), tt(o["end"] - 1), color="orange", alpha=0.3, lw=0)
        ax.annotate("not_a_pull", (tt(o["start"]), radius + params["lift_m"]), textcoords="offset points",
                    xytext=(2, 14), color="darkorange")
    for k in keys:
        ax.axvline(t[k], color="grey", lw=0.6)
        ax.annotate(f"f{k}", (t[k], 1), xycoords=("data", "axes fraction"), textcoords="offset points",
                    xytext=(2, -12), rotation=90, fontsize=8, va="top")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("hub height above the floor (m)")
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(top=float(np.nanmax(rise) + radius) * 1.1)
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title(f"{len(entries)} attempts, {len(not_a_pull)} not_a_pull, knee gate {knee:.2f} m")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


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

    keys = key_frames(rise, attempts, other)
    write_plot(tmp / "attempts.png", t, rise, radius, entries, not_a_pull, keys, params)

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
                       dim=~inside, frame_labels=labels, extra=keys)
    print(f"S3 {len(entries)} attempts {[tuple(a['window']) for a in entries]}, "
          f"{len(not_a_pull)} not_a_pull", flush=True)
    for a in entries:
        if a["plate_found"] < MIN_MOVING_FOUND:
            raise StageStop(TRACK_FAILED_EXIT, "plate_track_failed",
                            f"Plate track unusable in {ctx.clip.name}: found in {a['plate_found']:.0%} of "
                            f"attempt {a['attempt']} (frames {a['start']}-{a['end']}, need {MIN_MOVING_FOUND:.0%}).")


STAGE = Stage("S3", (CLIP, "plate.npz", "clip.json", "frame_times.npy", ATHLETE), ("attempts.json", "attempts.png", OVERLAY), run)
