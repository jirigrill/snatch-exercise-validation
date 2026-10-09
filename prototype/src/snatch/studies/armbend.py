"""Early arm bend (A13, D2) from the near shoulder, elbow and the plate hub.

From the side the near wrist sits inside the plate outline, so the hand is
replaced by the hub: with straight arms the hand lies on the camera axis
behind the plate, and the 2D shoulder-to-hub distance is the projected arm
length (docs/research/12-feasibility-grill.md, D2). If the arms bend, it
shrinks. Inputs are smoothed image positions in pixels (y grows downward),
and px_per_m is the plate-plane scale (450 mm plate). The shoulder is
deeper than the plate, so "cm" is in the plate plane: the scale is the same
for every rep of one setup, not a true arm length.

Pull events inside a v2 rep (snatch.phases):
- setup: liftoff (v2).
- knee: first frame after setup with the hub above the near knee.
- transition: v2 transition (deepest knee re-bend); None if not detected.
- hip: first frame after setup with the hub above the near hip, the end of
  the window. Roughly the start of the second pull's extension.
"""

from dataclasses import dataclass

import numpy as np

from snatch.angles import joint_angle
from snatch.phases import Rep


def arm_signals(shoulder: np.ndarray, elbow: np.ndarray, wrist: np.ndarray,
                hub: np.ndarray, px_per_m: float) -> dict[str, np.ndarray]:
    """Per-frame arm signals; points are (n, 2) pixels.

    d_cm: shoulder-to-hub distance. straight: d / (upper arm + elbow-to-hub),
    1 when shoulder, elbow and hub are in line, scale-free. elbow_hub_deg:
    shoulder-elbow-hub angle. elbow_deg: shoulder-elbow-wrist (wrist mostly
    hidden from the side).
    """
    cm = 100 / px_per_m
    d = np.linalg.norm(shoulder - hub, axis=1)
    upper = np.linalg.norm(shoulder - elbow, axis=1)
    fore = np.linalg.norm(elbow - hub, axis=1)
    return {
        "d_cm": d * cm,
        "upper_cm": upper * cm,
        "straight": d / (upper + fore),
        "elbow_hub_deg": joint_angle(shoulder, elbow, hub),
        "elbow_deg": joint_angle(shoulder, elbow, wrist),
    }


@dataclass(frozen=True)
class PullEvents:
    setup: int
    knee: int | None
    transition: int | None
    hip: int | None


def first_above(hub_y: np.ndarray, part_y: np.ndarray, start: int, end: int
                ) -> int | None:
    """First frame in [start, end] with the hub above (smaller y) the part."""
    above = np.flatnonzero(hub_y[start:end + 1] < part_y[start:end + 1])
    return start + int(above[0]) if len(above) else None


def pull_events(hub_y: np.ndarray, knee_y: np.ndarray, hip_y: np.ndarray,
                rep: Rep) -> PullEvents:
    end = rep.overhead_start
    return PullEvents(rep.setup, first_above(hub_y, knee_y, rep.setup, end),
                      rep.transition, first_above(hub_y, hip_y, rep.setup, end))


def at(x: np.ndarray, i: int | None) -> float:
    return float("nan") if i is None else float(x[i])


def window_min(x: np.ndarray, start: int, end: int | None) -> tuple[float, int | None]:
    """Minimum of x over [start, end] and its frame; NaN if no end."""
    if end is None:
        return float("nan"), None
    i = start + int(np.argmin(x[start:end + 1]))
    return float(x[i]), i


def phase_time(i: np.ndarray, ev: PullEvents) -> np.ndarray:
    """Frames mapped to pull time: setup 0, bar at knee 1, bar at hip 2.

    Piecewise linear between the events, linear extrapolation outside, so
    reps of different speed line up for plotting.
    """
    xs = [ev.setup, ev.knee, ev.hip]
    if None in xs or not xs[0] < xs[1] < xs[2]:
        return np.full(len(i), np.nan)
    xp, fp = np.array(xs, float), np.array([0.0, 1.0, 2.0])
    out = np.interp(i, xp, fp)
    lo, hi = i < xp[0], i > xp[-1]
    out[lo] = (i[lo] - xp[0]) / (xp[1] - xp[0])
    out[hi] = 2 + (i[hi] - xp[2]) / (xp[2] - xp[1])
    return out


def separation(a: list[float], b: list[float]) -> dict[str, float]:
    """Group a vs group b: mean difference, pooled-SD effect size (Cohen's d)
    and the gap between the ranges in the direction of the difference
    (positive = the ranges don't overlap, negative = overlap)."""
    x, y = np.asarray(a, float), np.asarray(b, float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    pooled = np.sqrt(((len(x) - 1) * x.var(ddof=1) + (len(y) - 1) * y.var(ddof=1))
                     / (len(x) + len(y) - 2))
    return {
        "n_a": len(x), "n_b": len(y),
        "mean_a": float(x.mean()), "mean_b": float(y.mean()),
        "sd_a": float(x.std(ddof=1)), "sd_b": float(y.std(ddof=1)),
        "diff": float(y.mean() - x.mean()),
        "cohen_d": float((y.mean() - x.mean()) / pooled),
        "gap": float(y.min() - x.max() if y.mean() >= x.mean() else x.min() - y.max()),
    }
