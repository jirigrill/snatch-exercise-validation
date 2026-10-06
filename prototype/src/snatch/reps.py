"""Split a clip into lifts from the near plate's hub height (bar on the floor
vs off it), to give each rep a frame range before pose runs.

Not a phase definition: v1/v2 (snatch.phases) still mark setup, transition,
catch and lockout inside a rep. This only finds where each lift starts and
ends, so pose can skip the rests between reps.

- floor: the hub's resting height, taken as a high percentile of hub y (image
  y grows downward; the bar spends most of a clip on the floor).
- lift: a run of frames with the smoothed hub more than `lift_m` above the
  floor, peaking at least `min_peak_m` up (0.6 m: below a pull to the hips,
  0.68 m in the standing-hold clip; above the false lifts of a jumping
  off-axis hub track, <=0.5 m). Runs closer than `merge_s` are one
  lift (a bounce on a dropped miss).
- start: last frame before the run with the hub within `rest_m` of the
  floor (liftoff); end: first frame after it back within `rest_m` (bar down).
"""

from dataclasses import dataclass

import numpy as np

from snatch.signals import smooth


@dataclass(frozen=True)
class Lift:
    start: int  # liftoff
    end: int  # bar back on the floor (exclusive)
    peak_m: float  # highest hub point above the floor


def height_above_floor(hub_y: np.ndarray, found: np.ndarray, px_per_m: np.ndarray,
                       fps: float, floor_pct: float = 95) -> np.ndarray:
    """Smoothed hub height above its resting level, in metres."""
    y = np.where(found, hub_y, np.nan)
    floor_y = np.nanpercentile(y, floor_pct)
    scale = np.nanmedian(np.where(found, px_per_m, np.nan))
    return (floor_y - smooth(y, fps)) / scale


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) of each run of True."""
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def find_lifts(height_m: np.ndarray, fps: float, lift_m: float = 0.10,
               min_peak_m: float = 0.60, rest_m: float = 0.03,
               merge_s: float = 0.25) -> list[Lift]:
    up = runs(height_m > lift_m)
    merged: list[list[int]] = []
    for s, e in up:
        if merged and s - merged[-1][1] < merge_s * fps:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    lifts = []
    rest = height_m <= rest_m
    for s, e in merged:
        peak = float(height_m[s:e].max())
        if peak < min_peak_m:
            continue
        before = np.flatnonzero(rest[:s])
        after = np.flatnonzero(rest[e:])
        start = int(before[-1]) if before.size else 0
        end = int(e + after[0] + 1) if after.size else len(height_m)
        lifts.append(Lift(start, end, peak))
    return lifts


def pose_range(lift: Lift, fps: float, n_frames: int, pad_before_s: float = 1.0,
               pad_after_s: float = 1.0) -> tuple[int, int]:
    """Frames to pose for one lift: the lift plus still padding either side."""
    return (max(0, lift.start - round(pad_before_s * fps)),
            min(n_frames, lift.end + round(pad_after_s * fps)))


def find_pose_lifts(wrist_y: np.ndarray, nose_y: np.ndarray, knee_y: np.ndarray,
                        hip_y: np.ndarray, fps: float, min_up_s: float = 0.1,
                        merge_s: float = 0.5) -> list[Lift]:
    """Lifts from pose alone, for clips whose plate track fails (off-axis).

    Inputs are per-frame image y (down = larger), NaN where not posed (a
    sparse pass poses every Nth frame). Anchor: a run of posed frames with the
    wrists above the chest, taken as midway between hip and nose (merged
    across gaps < merge_s, at least min_up_s long). Not "above the
    nose": on misses seen from +30° (20261005_10) the wrists only reach nose
    height. Start: last posed frame before it with the wrists
    below the knees (gripping the bar on the floor); end: first posed frame
    after it with the wrists below the hips (bar lowered). Rougher than the
    hub; only used to set pose ranges, which are padded.
    """
    posed = ~np.isnan(wrist_y) & ~np.isnan(nose_y)
    idx = np.flatnonzero(posed)
    chest_y = (hip_y + nose_y) / 2
    over = idx[wrist_y[idx] < chest_y[idx]]
    groups: list[list[int]] = []
    for i in over:
        if groups and i - groups[-1][1] < merge_s * fps:
            groups[-1][1] = int(i)
        else:
            groups.append([int(i), int(i)])
    lifts = []
    for s, e in groups:
        if e - s < min_up_s * fps:
            continue
        low = idx[(idx < s) & (wrist_y[idx] > knee_y[idx])]
        down = idx[(idx > e) & (wrist_y[idx] > hip_y[idx])]
        start = int(low[-1]) if low.size else s
        end = int(down[0]) + 1 if down.size else e + 1
        if lifts and start < lifts[-1].end:
            start = lifts[-1].end
        lifts.append(Lift(start, end, float("nan")))
    return lifts


def find_pose_holds(wrist_y: np.ndarray, knee_y: np.ndarray, hip_y: np.ndarray,
                    fps: float, min_s: float = 0.5) -> list[Lift]:
    """Pulls to a standing hold (no overhead phase), from pose: runs of posed
    frames with the wrists above mid-thigh, at least `min_s` long. Fallback
    when find_pose_lifts finds nothing (20261005_6: two holds, no snatch).
    Starts when the wrists pass mid-thigh, not at liftoff: pad the range.
    """
    idx = np.flatnonzero(~np.isnan(wrist_y) & ~np.isnan(knee_y) & ~np.isnan(hip_y))
    up = wrist_y[idx] < (knee_y[idx] + hip_y[idx]) / 2
    return [Lift(int(idx[s]), int(idx[e - 1]) + 1, float("nan"))
            for s, e in runs(up) if idx[e - 1] - idx[s] >= min_s * fps]
