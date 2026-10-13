"""Per-lifter 2D leg skeleton: thigh and shank lengths, fitted on a bar-only clip (C3).

Side-on, the near plate hides the near knee around the transition
(docs/results/36-skeleton-fill.md). On a bar-only clip the knee is visible,
so the lengths can be measured there and the hidden knee rebuilt later (S4b)
from the hip and ankle.

- Knee: the circle of thigh length around the hip meets the circle of shank
  length around the ankle; of the two solutions, the knee is the one in front
  of the hip-ankle line (toward the lifter's facing direction).
- Lengths depend on d = |hip - ankle| (`LengthTable`): RTMPose's joint centres
  drift with flexion and the projected thigh shortens in a deep squat, so a
  table of median lengths over bins of d / d_ref beats a fixed length (36 §3).
  d_ref is the standing hip-ankle distance, so a table carries to another clip
  by rescaling (S4a).

skeleton.json holds one entry per near side ("r", "l"); a calibration replaces
its side and keeps the other. `hide_test` checks the table on the calibration
clip: it hides the knee where a plate would cover it and rebuilds it. No wrist offset: the wrist under the plate cannot
be checked on a loaded clip, so it stays RTMPose's.
All points are image pixels, (n, 2), y down.
"""

from dataclasses import dataclass

import numpy as np

from snatch.angles import HALPE26, joint_angle, sagittal_angles
from snatch.signals import smooth_keypoints

MIN_SCORE = 0.5  # near hip, knee and ankle all at least this: the frame is used
STAND_DEG = 165.0  # knee and hip above this: standing
MIN_STANDING = 20  # frames
MIN_BINS = 3  # length-table bins with enough frames
MAX_GAIN = 2.0  # rebuild the knee only this well conditioned (36 §1: the hybrid's rule)


def unit_normal(hip: np.ndarray, ankle: np.ndarray, facing: float
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
    d, u, n = unit_normal(hip, ankle, facing)
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

    def to_json(self) -> dict:
        return {"d_ref": self.d_ref, "edges": self.edges.tolist(), "thigh": self.thigh.tolist(),
                "shank": self.shank.tolist()}

    @classmethod
    def from_json(cls, d: dict) -> "LengthTable":
        return cls(np.asarray(d["edges"], float), np.asarray(d["thigh"], float),
                   np.asarray(d["shank"], float), float(d["d_ref"]))


def _fill_nan(x: np.ndarray) -> np.ndarray:
    ok = ~np.isnan(x)
    i = np.arange(len(x))
    return np.interp(i, i[ok], x[ok])


def _binned(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray, d_ref: float, n_bins: int,
            r_lo: float, min_n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = np.hypot(*(np.asarray(ankle, float) - hip).T)
    th = np.hypot(*(np.asarray(knee, float) - hip).T)
    sh = np.hypot(*(np.asarray(ankle, float) - knee).T)
    edges = np.linspace(r_lo, 1.05, n_bins + 1)
    b = np.digitize(d / d_ref, edges) - 1
    t_med, s_med = np.full(n_bins, np.nan), np.full(n_bins, np.nan)
    for k in range(n_bins):
        m = b == k
        if m.sum() >= min_n:
            t_med[k], s_med[k] = np.median(th[m]), np.median(sh[m])
    return edges, t_med, s_med


def length_table(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray,
                 d_ref: float, n_bins: int = 12, r_lo: float = 0.4,
                 min_n: int = 20) -> LengthTable:
    """Binned median thigh and shank over frames with visible joints."""
    edges, t_med, s_med = _binned(hip, knee, ankle, d_ref, n_bins, r_lo, min_n)
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


class FitError(ValueError):
    """The clip has too few usable frames to fit the skeleton."""


def _side_joints(facing: str, *parts: str) -> list[int]:
    side = "r" if facing == "right" else "l"
    return [HALPE26[f"{side}_{p}"] for p in parts]


def fit(keypoints: np.ndarray, scores: np.ndarray, t: np.ndarray, facing: str
        ) -> tuple[dict, LengthTable, np.ndarray]:
    """Fit the near side's length table on a bar-only clip's raw pose.

    Returns (skeleton.json entry, the table, smoothed keypoints). FitError when
    fewer than MIN_STANDING standing frames or MIN_BINS filled bins.
    """
    side = "r" if facing == "right" else "l"
    j = _side_joints(facing, "hip", "knee", "ankle")
    fps = float((len(t) - 1) / (t[-1] - t[0]))
    k = smooth_keypoints(np.asarray(keypoints, float), fps, t)
    hip, knee, ank = (k[:, i] for i in j)
    used = (np.asarray(scores)[:, j] >= MIN_SCORE).all(1) & ~np.isnan(keypoints).any((1, 2))
    ang = sagittal_angles(k, side, facing)
    stand = used & (ang["knee"] > STAND_DEG) & (ang["hip"] > STAND_DEG)
    if stand.sum() < MIN_STANDING:
        raise FitError(f"{int(stand.sum())} standing frames (knee and hip > {STAND_DEG:.0f} deg, "
                       f"{side} hip/knee/ankle score >= {MIN_SCORE}), need {MIN_STANDING}")
    d_ref = robust_length(hip, ank, stand)
    _, t_med, _ = _binned(hip[used], knee[used], ank[used], d_ref, 12, 0.4, 20)
    filled = int((~np.isnan(t_med)).sum())
    if filled < MIN_BINS:
        raise FitError(f"{filled} length-table bins with enough frames, need {MIN_BINS}")
    tab = length_table(hip[used], knee[used], ank[used], d_ref)
    r = np.hypot(*(ank[used] - hip[used]).T) / d_ref
    entry = {"facing": facing, **tab.to_json(), "bins_measured": filled,
             "r_range": [round(float(r.min()), 3), round(float(r.max()), 3)],
             "frames": int(used.sum()), "standing_frames": int(stand.sum())}
    return entry, tab, k


# Hide test: a virtual plate on the bar-only clip, sized and placed as on the
# loaded clips of the 2026-10-07 session (36 §2, §5): radius 96 px and hub =
# wrist + (-7, +53) px (wrist - hub ~ (+2, -15) cm), both at standing
# hip-ankle 312 px, so they scale with d_ref. x is toward the lifter's front.
PLATE_R = 96 / 312
HUB_FROM_WRIST = np.array([-7.0, 53.0]) / 312
HIP_ANKLE_PER_HEIGHT = 0.491  # standing hip joint to ankle joint (Winter: 0.530 - 0.039 of height)


def _stats(x: np.ndarray, nd: int = 2) -> dict:
    return {"median": round(float(np.median(x)), nd), "p90": round(float(np.percentile(x, 90)), nd),
            "max": round(float(x.max()), nd)}


def hide_test(k: np.ndarray, tab: LengthTable, facing: str, height_m: float) -> tuple[dict, dict[str, np.ndarray]]:
    """Hide the near knee where a plate would cover it and rebuild it from hip, ankle and the table.

    Hidden: the knee inside the virtual plate. Rebuilt: hidden, the circles meet
    and the leg is bent enough (gain <= MAX_GAIN), as S4b will; the other
    hidden frames keep the knee (S4b keeps RTMPose's there). The error is the
    rebuilt knee vs the visible one; cm from the athlete's height. Returns
    (summary for skeleton.json, per-frame arrays: hub, hidden, rebuilt mask,
    knee with the rebuild in it). FitError when no frame is rebuilt.
    """
    hip, knee, ank, wrist = (k[:, i] for i in _side_joints(facing, "hip", "knee", "ankle", "wrist"))
    sign = 1.0 if facing == "right" else -1.0
    hub = wrist + HUB_FROM_WRIST * tab.d_ref * [sign, 1.0]
    hidden = np.hypot(*(knee - hub).T) < PLATE_R * tab.d_ref
    lt, ls = tab.lengths(np.hypot(*(ank - hip).T))
    test, clipped = two_circle_knee(hip, ank, lt, ls, sign)
    use = hidden & ~clipped & (knee_gain(hip, ank, lt, ls, sign) <= MAX_GAIN)
    if not use.any():
        raise FitError(f"the knee is behind the virtual plate in {int(hidden.sum())} frames and rebuilt in none: "
                       "no pull from the floor in the clip?")
    filled = np.where(use[:, None], test, knee)
    err_px = np.hypot(*(test[use] - knee[use]).T)
    px_per_cm = tab.d_ref / (HIP_ANKLE_PER_HEIGHT * height_m * 100)
    dang = np.abs(joint_angle(hip, filled, ank) - joint_angle(hip, knee, ank))[use]
    summary = {"hidden_frames": int(hidden.sum()), "rebuilt_frames": int(use.sum()),
               "knee_err_px": _stats(err_px), "knee_err_cm": _stats(err_px / px_per_cm),
               "angle_err_deg": _stats(dang, 1)}
    return summary, {"hub": hub, "hidden": hidden, "rebuilt": use, "knee": filled}
