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
its side and keeps the other. No wrist offset: the wrist under the plate cannot
be checked on a loaded clip, so it stays RTMPose's.
All points are image pixels, (n, 2), y down.
"""

from dataclasses import dataclass

import numpy as np

from snatch.angles import HALPE26, sagittal_angles
from snatch.signals import smooth_keypoints

MIN_SCORE = 0.5  # near hip, knee and ankle all at least this: the frame is used
STAND_DEG = 165.0  # knee and hip above this: standing
MIN_STANDING = 20  # frames
MIN_BINS = 3  # length-table bins with enough frames


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


def fit(keypoints: np.ndarray, scores: np.ndarray, t: np.ndarray, facing: str
        ) -> tuple[dict, np.ndarray, np.ndarray]:
    """Fit the near side's length table on a bar-only clip's raw pose.

    Returns (skeleton.json entry, smoothed keypoints, rebuilt near knee (n, 2)
    over the used frames, NaN elsewhere). FitError when fewer than
    MIN_STANDING standing frames or MIN_BINS filled bins.
    """
    side = "r" if facing == "right" else "l"
    j = {p: HALPE26[f"{side}_{p}"] for p in ("hip", "knee", "ankle")}
    fps = float((len(t) - 1) / (t[-1] - t[0]))
    k = smooth_keypoints(np.asarray(keypoints, float), fps, t)
    hip, knee, ank = k[:, j["hip"]], k[:, j["knee"]], k[:, j["ankle"]]
    used = (np.asarray(scores)[:, list(j.values())] >= MIN_SCORE).all(1) & ~np.isnan(keypoints).any((1, 2))
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
    sign = 1.0 if facing == "right" else -1.0
    rebuilt = np.full_like(knee, np.nan)
    rebuilt[used] = two_circle_knee(hip[used], ank[used], *tab.lengths(np.hypot(*(ank[used] - hip[used]).T)),
                                    sign)[0]
    err = np.hypot(*(rebuilt[used] - knee[used]).T)
    r = np.hypot(*(ank[used] - hip[used]).T) / d_ref
    entry = {"facing": facing, **tab.to_json(), "bins_measured": filled,
             "r_range": [round(float(r.min()), 3), round(float(r.max()), 3)],
             "frames": int(used.sum()), "standing_frames": int(stand.sum()),
             "knee_err_px": {"median": round(float(np.median(err)), 2),
                             "p90": round(float(np.percentile(err, 90)), 2)}}
    return entry, k, rebuilt
