"""Per-lifter 2D skeleton: fill in near-side joints the near plate hides.

The length table, the two-circle knee and knee_gain moved to snatch.skeleton (C3); the
rest moves when S4b fills hidden joints.

Side-on (0 deg) the near plate covers the near knee around the transition
and the near wrist during the pull (docs/results/33-d1-views.md). The
lifter's segment lengths are measured (in px, at one camera position) where
the joints are visible, and the hidden joint is rebuilt from visible ones
(docs/results/36-skeleton-fill.md).

- Knee: the circle of thigh length around the hip meets the circle of shank
  length around the ankle. Of the two solutions, the knee is the one in
  front of the hip-ankle line (toward the lifter's facing direction). Near
  a straight leg (d = |hip - ankle| close to thigh + shank) the half chord
  h = sqrt(L_t^2 - a^2) goes to 0 and the knee's position along the normal
  is very sensitive to the lengths and to d; `knee_gain` gives that
  sensitivity in px of knee per px of length error.
- Lengths can be fixed or depend on d (`LengthTable`): RTMPose's joint
  centres drift with flexion, and the projected thigh shortens when the knee
  points out of the image plane (deep squat), so a 2-link chain with fixed
  lengths does not hold exactly. A table of median lengths over bins of
  d / d_max, measured on a calibration clip, keeps the method 1-DOF and
  uses only visible inputs (hip, ankle).
- Wrist: side-on the hand grips the bar, so the near wrist is the hub plus
  an offset (`fit_offset`, `wrist_from_hub`).

All points are image pixels, (n, 2), y down.
"""

import numpy as np

from snatch.skeleton import unit_normal


def local_frame(hip: np.ndarray, ankle: np.ndarray, knee: np.ndarray,
                facing: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(d, along, out): knee in the hip-ankle frame (px along hip->ankle from
    the hip, px in front of the line)."""
    d, u, n = unit_normal(hip, ankle, facing)
    r = np.asarray(knee, float) - hip
    return d, (r * u).sum(1), (r * n).sum(1)


def fit_offset(wrist: np.ndarray, hub: np.ndarray, mask: np.ndarray | None = None
               ) -> tuple[np.ndarray, np.ndarray]:
    """Median and IQR/1.349 (robust SD) of wrist - hub over `mask` frames."""
    o = np.asarray(wrist, float) - hub
    if mask is not None:
        o = o[mask]
    o = o[~np.isnan(o).any(1)]
    q1, q2, q3 = np.percentile(o, [25, 50, 75], axis=0)
    return q2, (q3 - q1) / 1.349


def wrist_from_hub(hub: np.ndarray, offset: np.ndarray) -> np.ndarray:
    return np.asarray(hub, float) + offset



PHASES = ("setup", "first pull", "transition", "second pull", "catch")


def pull_windows(bar_y: np.ndarray, knee_y: np.ndarray, hip_y: np.ndarray,
                 knee_deg: np.ndarray, fps: float, t: np.ndarray | None = None,
                 still_px_s: float = 50.0, peak_s: float = 0.6) -> list[dict]:
    """Pulls: every rise of the bar (wrist or hub y) from below the knee to
    above the hip. Events: setup (liftoff, as snatch.phases), knee / hip
    (first frame with the bar above the near knee / hip), peak (largest knee
    angle within peak_s after the bar passes the hip)."""
    from snatch.phases import liftoff_frame

    y = np.asarray(bar_y, float)
    above = y < hip_y
    starts = np.flatnonzero(np.diff(above.astype(int)) == 1) + 1
    out, last = [], 0
    for s in starts:
        below = np.flatnonzero(y[last:s] > knee_y[last:s])
        if not len(below):
            continue
        anchor = last + int(below[-1])
        setup = liftoff_frame(y, anchor, fps, still_px_s, t)
        kn = setup + int(np.flatnonzero(y[setup:s + 1] < knee_y[setup:s + 1])[0])
        end = min(s + int(peak_s * fps), len(y))
        peak = s + int(np.argmax(knee_deg[s:end]))
        out.append({"setup": int(setup), "knee": int(kn), "hip": int(s), "peak": int(peak)})
        last = s
    return out


def phase_labels(n: int, ev: dict, fps: float, setup_s: float = 0.25) -> np.ndarray:
    """Per-frame index into PHASES (-1 outside): setup = setup_s before
    liftoff, first pull = liftoff -> bar at knee, transition = bar at knee ->
    bar at hip, second pull = bar at hip -> peak knee extension, catch =
    peak -> ev["lockout"] (if given)."""
    lab = np.full(n, -1)
    lab[max(ev["setup"] - int(setup_s * fps), 0):ev["setup"]] = 0
    lab[ev["setup"]:ev["knee"]] = 1
    lab[ev["knee"]:ev["hip"]] = 2
    lab[ev["hip"]:ev["peak"] + 1] = 3
    if ev.get("lockout") is not None:
        lab[ev["peak"] + 1:ev["lockout"] + 1] = 4
    return lab


def fill_hidden(observed: np.ndarray, rebuilt: np.ndarray, use: np.ndarray,
                fade: int = 25) -> np.ndarray:
    """observed where `use` is False, rebuilt where True, cross-faded over
    `fade` frames at each switch (a moving average of `use`), so the switch
    itself adds no step that could read as a knee re-bend. (n, 2) points;
    NaN rows in `rebuilt` fall back to observed."""
    w = np.convolve(np.asarray(use, float), np.ones(fade) / fade, mode="same")
    w = np.where(np.isnan(rebuilt).any(1), 0.0, w)[:, None]
    return w * np.nan_to_num(rebuilt) + (1 - w) * observed
