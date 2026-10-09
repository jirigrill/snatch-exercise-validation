"""Per-lifter 2D skeleton: fill in near-side joints the near plate hides.

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

from dataclasses import dataclass

import numpy as np


def _unit_normal(hip: np.ndarray, ankle: np.ndarray, facing: float
                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(d, u, n): hip-ankle distance, unit hip->ankle, unit normal pointing
    to the lifter's front (image +x if facing = +1)."""
    v = np.asarray(ankle, float) - hip
    d = np.hypot(v[:, 0], v[:, 1])
    u = v / d[:, None]
    n = np.stack([-u[:, 1], u[:, 0]], 1)
    s = np.where(n[:, 0] * facing >= 0, 1.0, -1.0)
    return d, u, n * s[:, None]


def two_circle_knee(hip: np.ndarray, ankle: np.ndarray, l_thigh, l_shank,
                    facing: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Knee from hip, ankle and the two segment lengths (scalars or (n,)).

    Returns (knee (n, 2), clipped (n,) bool). clipped: the circles do not
    meet (d > L_t + L_s, or d < |L_t - L_s|); the knee is then put on the
    hip-ankle line at the point the circles come closest (h = 0).
    """
    hip = np.asarray(hip, float)
    lt = np.broadcast_to(np.asarray(l_thigh, float), (len(hip),))
    ls = np.broadcast_to(np.asarray(l_shank, float), (len(hip),))
    d, u, n = _unit_normal(hip, ankle, facing)
    a = (lt ** 2 - ls ** 2 + d ** 2) / (2 * d)
    h2 = lt ** 2 - a ** 2
    clipped = h2 < 0
    h = np.sqrt(np.where(clipped, 0.0, h2))
    a = np.where(clipped, np.clip(a, -lt, lt), a)
    return hip + a[:, None] * u + h[:, None] * n, clipped


def knee_gain(hip: np.ndarray, ankle: np.ndarray, l_thigh, l_shank,
              facing: float = 1.0, eps: float = 0.5) -> np.ndarray:
    """px of knee movement per px of thigh-length error (numerical).

    1 at a right-angle knee, grows without bound toward a straight leg.
    """
    k0, _ = two_circle_knee(hip, ankle, l_thigh, l_shank, facing)
    k1, _ = two_circle_knee(hip, ankle, np.asarray(l_thigh) + eps, l_shank, facing)
    return np.hypot(*(k1 - k0).T) / eps


def local_frame(hip: np.ndarray, ankle: np.ndarray, knee: np.ndarray,
                facing: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(d, along, out): knee in the hip-ankle frame (px along hip->ankle from
    the hip, px in front of the line)."""
    d, u, n = _unit_normal(hip, ankle, facing)
    r = np.asarray(knee, float) - hip
    return d, (r * u).sum(1), (r * n).sum(1)


@dataclass(frozen=True)
class LengthTable:
    """Thigh and shank length (px) as a function of r = d / d_ref.

    edges: bin edges of r; thigh, shank: median per bin (NaN bins filled
    from neighbours). d_ref: the reference hip-ankle distance (standing),
    so a table carries to another clip by rescaling d_ref and the lengths.
    """
    edges: np.ndarray
    thigh: np.ndarray
    shank: np.ndarray
    d_ref: float

    def lengths(self, d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        centres = (self.edges[:-1] + self.edges[1:]) / 2
        r = np.asarray(d, float) / self.d_ref
        return (np.interp(r, centres, self.thigh), np.interp(r, centres, self.shank))

    def scaled(self, s: float) -> "LengthTable":
        return LengthTable(self.edges, self.thigh * s, self.shank * s, self.d_ref * s)


def _fill_nan(x: np.ndarray) -> np.ndarray:
    ok = ~np.isnan(x)
    i = np.arange(len(x))
    return np.interp(i, i[ok], x[ok])


def length_table(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray,
                 d_ref: float, n_bins: int = 12, r_lo: float = 0.4,
                 min_n: int = 20) -> LengthTable:
    """Binned median thigh and shank over frames with visible joints."""
    d = np.hypot(*(np.asarray(ankle, float) - hip).T)
    th = np.hypot(*(np.asarray(knee, float) - hip).T)
    sh = np.hypot(*(np.asarray(ankle, float) - knee).T)
    edges = np.linspace(r_lo, 1.05, n_bins + 1)
    r = d / d_ref
    b = np.digitize(r, edges) - 1
    t_med, s_med = np.full(n_bins, np.nan), np.full(n_bins, np.nan)
    for k in range(n_bins):
        m = b == k
        if m.sum() >= min_n:
            t_med[k], s_med[k] = np.median(th[m]), np.median(sh[m])
    return LengthTable(edges, _fill_nan(t_med), _fill_nan(s_med), float(d_ref))


def robust_length(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None,
                  how: str = "median") -> float:
    """Segment length (px) between keypoints a and b over `mask` frames.

    how: "median" (use with standing frames) or "pNN" (e.g. "p90": high
    percentile over the lift; foreshortening only shortens, noise
    lengthens, so a high percentile below the max).
    """
    v = np.hypot(*(np.asarray(a, float) - b).T)
    if mask is not None:
        v = v[mask]
    v = v[~np.isnan(v)]
    if how == "median":
        return float(np.median(v))
    if how.startswith("p"):
        return float(np.percentile(v, float(how[1:])))
    raise ValueError(how)


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
