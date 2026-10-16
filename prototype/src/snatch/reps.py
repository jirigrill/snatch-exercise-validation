"""S3's attempt finding: split a clip into attempts from the near plate's hub height
(bar on the floor vs off it), to give each attempt a frame range before pose runs.

- floor: the hub's resting height, taken as a high percentile of hub y (image
  y grows downward; the bar spends most of a clip on the floor).
- candidate: a run of frames with the smoothed hub more than `lift_m` above the
  floor. Candidates are merged only when the bar did not come to rest between
  them (no frame within `rest_m` of the floor).
- attempt: a candidate whose hub reaches the athlete's knee height above the
  real floor; the rest are `not_a_pull`.
- start: last frame before the run with the hub within `rest_m` of the
  floor (liftoff); end: first frame after it back within `rest_m` (bar down),
  exclusive.
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
                       t: np.ndarray, floor_pct: float = 95) -> np.ndarray:
    """Smoothed hub height above its resting level, in metres."""
    y = np.where(found, hub_y, np.nan)
    floor_y = np.nanpercentile(y, floor_pct)
    scale = np.nanmedian(np.where(found, px_per_m, np.nan))
    return (floor_y - smooth(y, t=t)) / scale


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) of each run of True."""
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def find_attempts(rise_m: np.ndarray, knee_height_m: float, radius_m: float,
                  lift_m: float = 0.10, rest_m: float = 0.03) -> tuple[list[Lift], list[Lift]]:
    """(attempts, not_a_pull) from the hub's rise above its resting level (height_above_floor).

    A candidate is a run of rise > lift_m; candidates with no frame at rest
    (rise <= rest_m) between them are one. start = last frame before the run
    at rest (liftoff); end = first frame after it back at rest, exclusive. The
    hub's height above the real floor is rise + `radius_m` (the plate radius):
    an attempt peaks at least at `knee_height_m`. `peak_m` is that height.
    """
    rest = rise_m <= rest_m
    merged: list[list[int]] = []
    for s, e in runs(rise_m > lift_m):
        if merged and not rest[merged[-1][1]:s].any():
            merged[-1][1] = e
        else:
            merged.append([s, e])
    attempts, other = [], []
    for s, e in merged:
        before = np.flatnonzero(rest[:s])
        after = np.flatnonzero(rest[e:])
        start = int(before[-1]) if before.size else 0
        end = int(e + after[0] + 1) if after.size else len(rise_m)
        peak = float(rise_m[s:e].max()) + radius_m
        (attempts if peak >= knee_height_m else other).append(Lift(start, end, peak))
    return attempts, other


def pose_range(lift: Lift, t: np.ndarray, n_frames: int, pad_before_s: float = 1.0,
               pad_after_s: float = 1.0) -> tuple[int, int]:
    """Frames to pose for one lift: the lift plus still padding either side."""
    start = int(np.searchsorted(t, t[lift.start] - pad_before_s - 1e-9))
    if lift.end >= len(t):
        return start, n_frames
    end = int(np.searchsorted(t, t[lift.end] + pad_after_s - 1e-9))
    return start, min(n_frames, end)
