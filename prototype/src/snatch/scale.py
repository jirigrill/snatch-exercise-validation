"""Clip scale (S5): how much bigger or smaller the athlete's leg skeleton is in this clip.

The skeleton's lengths (snatch.skeleton.LengthTable) are pixels on the calibration
clip. A clip from another camera distance needs them times a factor. Two methods:

1. standing: in each attempt window (padding included) the longest run of at least
   MIN_WINDOW_S seconds (frame times `t`, so 60 and 240 fps alike) of frames with the
   near hip, knee and ankle scored >= MIN_SCORE, knee angle >= STAND_DEG (the calibration's
   standing rule) on the smoothed keypoints, and the hip and ankle outside the plate
   outline. The factor is the median hip-ankle distance over all windows' frames / the
   skeleton's d_ref. One window per attempt, so a clip with two attempts must stand twice.
2. visible_knee, only when no attempt has a standing window: frames of the windows
   with hip, knee and ankle scored >= KNEE_SCORE and outside the plate outline (at least
   MIN_KNEE_FRAMES). Per frame
   (thigh + shank) / the table's thigh + shank at the same r = d / (d_ref x factor);
   r depends on the factor, so the median is iterated from factor = 1.

Neither method has enough frames (e.g. a standup: the plate covers the hip): method "none",
factor None, no stop. Proportions guard (a different person?): median thigh / shank on the
frames used vs the scaled table's at the same r; off by more than MAX_PROPORTION stops
(CannotScale). No limit on the factor itself. All keypoints are smoothed per attempt window (the gaps between windows
are not interpolated across).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from snatch.pose import HALPE26
from snatch.signals import smooth, window_frames
from snatch.plate import ellipse_dist
from snatch.skeleton import MIN_SCORE, STAND_DEG, LengthTable, sagittal_angles

MIN_WINDOW_S = 0.3
KNEE_SCORE = 0.6
MIN_KNEE_FRAMES = 20
MAX_PROPORTION = 0.10
FIXED_POINT_ITERATIONS = 20


@dataclass(frozen=True)
class Scale:
    factor: float | None  # None: method "none"
    method: str  # "standing" | "visible_knee" | "none"
    frames: np.ndarray  # clip frame indices used, sorted
    ratios: np.ndarray  # per used frame: the factor that frame alone gives
    thigh_shank: float | None
    thigh_shank_cal: float | None
    windows: list[tuple[int, int]] = field(default_factory=list)  # standing: [start, end) per window


class CannotScale(Exception):
    """Proportions off (exit 5). `partial`: what was measured."""

    def __init__(self, reason: str, partial: Scale | None = None):
        super().__init__(reason)
        self.reason = reason
        self.partial = partial


def smoothed(keypoints: np.ndarray, t: np.ndarray, windows: list[tuple[int, int]], side: str) -> np.ndarray:
    """The nose and the near leg's joints smoothed inside each window on its own; NaN elsewhere."""
    out = np.full(keypoints.shape, np.nan)
    joints = [HALPE26["nose"], *(HALPE26[f"{side}_{j}"] for j in ("shoulder", "hip", "knee", "ankle"))]
    for s, e in windows:
        if window_frames(t[s:e], 0.1) | 1 > e - s:
            continue  # shorter than the smoothing window
        for j in joints:
            seg = np.asarray(keypoints[s:e, j], float)
            if not np.isnan(seg).all():
                out[s:e, j] = np.stack([smooth(seg[:, d], t=t[s:e]) for d in (0, 1)], -1)
    return out


def covered(raw: np.ndarray, plate: Mapping[str, np.ndarray], side: str) -> np.ndarray:
    """(n, 3) bool: the raw near hip, knee, ankle lie inside the plate outline on a frame where it was found."""
    out = np.zeros((len(raw), 3), bool)
    found = np.asarray(plate["found"], bool)
    for c, j in enumerate(("hip", "knee", "ankle")):
        p = raw[:, HALPE26[f"{side}_{j}"]]
        with np.errstate(invalid="ignore"):
            d = ellipse_dist(p[:, 0], p[:, 1], plate["hub_x"], plate["hub_y"], plate["a"], plate["b"], plate["angle"])
        out[:, c] = found & (d < 1)
    return out


def _joints(k: np.ndarray, side: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return k[:, HALPE26[f"{side}_hip"]], k[:, HALPE26[f"{side}_knee"]], k[:, HALPE26[f"{side}_ankle"]]


def _runs(frames: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) runs of consecutive indices."""
    if not len(frames):
        return []
    cut = np.flatnonzero(np.diff(frames) > 1) + 1
    return [(int(a[0]), int(a[-1]) + 1) for a in np.split(frames, cut)]


def _proportions(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray, tab: LengthTable, factor: float
                 ) -> tuple[float, float]:
    d = np.hypot(*(ankle - hip).T)
    th, sh = np.hypot(*(knee - hip).T), np.hypot(*(ankle - knee).T)
    lt, ls = tab.scaled(factor).lengths(d)
    return float(np.median(th / sh)), float(np.median(lt / ls))


def _standing(k: np.ndarray, scores: np.ndarray, t: np.ndarray, windows: list[tuple[int, int]],
              side: str, cov: np.ndarray) -> np.ndarray:
    """Frame indices of the standing window of every attempt window that has one."""
    hip, _, _ = _joints(k, side)
    near = list(HALPE26[f"{side}_{j}"] for j in ("hip", "knee", "ankle"))
    ang = sagittal_angles(k, side)["knee"]
    cand = ((scores[:, near] >= MIN_SCORE).all(1) & (ang >= STAND_DEG) & ~np.isnan(hip).any(1)
            & ~cov[:, 0] & ~cov[:, 2])
    used: list[np.ndarray] = []
    for s, e in windows:
        best: tuple[int, int] | None = None
        for a, b in _runs(np.flatnonzero(cand[s:e])):
            if best is None or t[s + b - 1] - t[s + a] > t[s + best[1] - 1] - t[s + best[0]]:
                best = (a, b)
        if best and t[s + best[1] - 1] - t[s + best[0]] >= MIN_WINDOW_S:
            used.append(np.arange(s + best[0], s + best[1]))
    return np.concatenate(used) if used else np.zeros(0, int)


def estimate(k: np.ndarray, scores: np.ndarray, t: np.ndarray, windows: list[tuple[int, int]],
             tab: LengthTable, side: str, cov: np.ndarray) -> Scale:
    """The clip's scale from smoothed keypoints `k` (see `smoothed`); method "none" when no frames
    are usable; CannotScale when the proportions are off. `cov`: see `covered`, from the raw keypoints."""
    hip, knee, ank = _joints(k, side)
    d = np.hypot(*(ank - hip).T)
    frames = _standing(k, scores, t, windows, side, cov)
    method = "standing"
    ratios: np.ndarray
    if len(frames):
        ratios = d[frames] / tab.d_ref
        factor = float(np.median(ratios))
        found = [(s, e) for s, e in windows if ((frames >= s) & (frames < e)).any()]
    else:
        method, found = "visible_knee", []
        near = [HALPE26[f"{side}_{j}"] for j in ("hip", "knee", "ankle")]
        inside = np.zeros(len(t), bool)
        for s, e in windows:
            inside[s:e] = True
        ok = inside & (scores[:, near] >= KNEE_SCORE).all(1) & ~np.isnan(d) & ~cov.any(1)
        frames = np.flatnonzero(ok)
        if len(frames) < MIN_KNEE_FRAMES:
            return Scale(None, "none", np.zeros(0, int), np.zeros(0), None, None)
        meas = (np.hypot(*(knee - hip).T) + np.hypot(*(ank - knee).T))[frames]
        factor, ratios = 1.0, np.zeros(0)
        for _ in range(FIXED_POINT_ITERATIONS):
            lt, ls = tab.lengths(d[frames] / factor)  # unscaled table at r = d / (d_ref x factor)
            ratios = meas / (lt + ls)  # per frame: measured / the unscaled table at that r
            new = float(np.median(ratios))
            done = abs(new - factor) < 1e-6
            factor = new
            if done:
                break
    ts, ts_cal = _proportions(hip[frames], knee[frames], ank[frames], tab, factor)
    result = Scale(factor, method, frames, ratios, ts, ts_cal, found if method == "standing" else [])
    if abs(ts / ts_cal - 1) > MAX_PROPORTION:
        raise CannotScale(f"thigh / shank {ts:.3f} on the {len(frames)} {method} frames, the skeleton's "
                          f"{ts_cal:.3f} at the same hip-ankle distance: off by {abs(ts / ts_cal - 1):.0%} "
                          f"(limit {MAX_PROPORTION:.0%}); another person? Recalibrate for this athlete", result)
    return result


def spread(ratios: np.ndarray) -> float:
    """IQR / median of the per-frame ratios."""
    q1, q3 = np.percentile(ratios, [25, 75])
    return float((q3 - q1) / np.median(ratios))


def to_json(s: Scale) -> dict:
    if s.factor is None or s.thigh_shank is None or s.thigh_shank_cal is None:
        return {"factor": None, "method": "none", "n_frames": 0, "spread": None, "frames": [],
                "thigh_shank": None, "thigh_shank_cal": None}
    return {"factor": round(s.factor, 4), "method": s.method, "n_frames": len(s.frames),
            "spread": round(spread(s.ratios), 4), "frames": [list(r) for r in _runs(s.frames)],
            "thigh_shank": round(s.thigh_shank, 4), "thigh_shank_cal": round(s.thigh_shank_cal, 4)}
