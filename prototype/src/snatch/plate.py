"""Track the near weight plate as an object: outline, hub and px->m scale.

The plate is found by its outline, never from the wrists. Pass 1 collects
circle candidates per frame (Hough, half resolution); a Viterbi pass picks the
smoothest path of plate-sized circles through all frames, with an explicit
"not found" state so a lone false circle is never picked. Pass 2 refits each
chosen circle at full resolution as an ellipse from radial edge points, which
also covers a plate seen at an angle. All positions are pixels of the rotated
240 fps frame, indexed like the pose output.

The hub is the outline's centre: the bar axis at the near plate's face.
"""

from collections import deque
from collections.abc import Callable, Iterable

import cv2
import numpy as np

PLATE_DIAMETER_M = 0.45  # bumper plate (IWF standard), also the 5 kg used here
MAX_STEP_PX = 30.0  # plate travel per 240 fps frame, ~3.6 m/s at 820 px/m

Outline = tuple[float, float, float, float, float]  # cx, cy, a, b, angle (deg)


def disc_mean(gray: np.ndarray, x: float, y: float, r: float,
              inner: float = 0.85) -> float:
    """Mean grey level inside inner * r of (x, y)."""
    h, w = gray.shape
    ri = inner * r
    x0, x1 = max(0, int(x - ri)), min(w, int(x + ri) + 1)
    y0, y1 = max(0, int(y - ri)), min(h, int(y + ri) + 1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    inside = np.hypot(xx - x, yy - y) <= ri
    return float(gray[y0:y1, x0:x1][inside].mean()) if inside.any() else 255.0


def candidates(img: np.ndarray, r_min: float, r_max: float, scale: float = 0.5,
               max_n: int = 8) -> np.ndarray:
    """Circle candidates (x, y, r, disc mean grey) in full-res pixels, best first.

    Bumper plates are black, so the disc's mean grey separates the plate from
    round look-alikes (wall logo, ball shelf, ducts).
    """
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 1.5)
    found = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT_ALT, 1.5, 30, param1=150,
                             param2=0.5, minRadius=int(r_min * scale),
                             maxRadius=int(np.ceil(r_max * scale)))
    if found is None:
        return np.empty((0, 4))
    c = found.reshape(-1, 3)[:max_n].astype(float)
    disc = [disc_mean(gray, x, y, r) for x, y, r in c]
    return np.column_stack([c / scale, disc])


def typical_radius(cands: Iterable[np.ndarray], dark: float = 70) -> float:
    """Median radius of the best dark candidate per frame.

    Candidates without a disc column count as dark. Falls back to the
    top-ranked candidate if no frame has a dark one.
    """
    cands = [c for c in cands if len(c)]
    best = []
    for c in cands:
        ok = np.flatnonzero(c[:, 3] < dark) if c.shape[1] > 3 else [0]
        if len(ok):
            best.append(c[ok[0], 2])
    return float(np.median(best or [c[0, 2] for c in cands]))


def track(cands: list[np.ndarray], r0: float, max_step_px: float,
          r_tol: float = 0.15, miss_cost: float = 1.0, reentry_cost: float = 5.0,
          rank_cost: float = 0.05, max_gap: int = 24, dark_ok: float = 60,
          dark_span: float = 40) -> np.ndarray:
    """Candidate index chosen per frame (-1 = plate not found).

    Minimises, over all frames: per-frame cost of the chosen candidate (rank,
    radius off r0, disc brighter than dark_ok grey: +1 per dark_span) or
    `miss_cost` per frame without one; 0.5 * (step / allowed)^2 for moving
    between chosen candidates k frames apart (k <= max_gap), where allowed =
    k * max_step_px and longer steps are forbidden; and `reentry_cost` each time the path starts again after
    longer gaps (or at the start), where position is unconstrained.
    """
    n = len(cands)
    if n == 0:
        return np.empty(0, int)
    pos, unary, keep = [], [], []
    for c in cands:
        c = c.reshape(len(c), -1) if len(c) else np.empty((0, 3))
        idx = np.flatnonzero(np.abs(c[:, 2] - r0) <= r_tol * r0)
        keep.append(idx)
        pos.append(c[idx, :2])
        u = rank_cost * idx + 0.5 * ((c[idx, 2] - r0) / (r_tol * r0)) ** 2
        if c.shape[1] > 3:
            u = u + np.maximum(0, (c[idx, 3] - dark_ok) / dark_span)
        unary.append(u)
    # back pointers: (frame, candidate) or candidate -1 = the lost state there
    cost: list[np.ndarray] = []
    back: list[tuple[np.ndarray, np.ndarray]] = []
    lost = np.zeros(n)  # best cost with the plate lost at frame t
    lost_from = np.full(n, -1)  # candidate at t-1 it was lost after, or -1
    for t in range(n):
        k = len(keep[t])
        best = np.full(k, reentry_cost + (lost[t - 1] if t else 0.0))
        from_t, from_s = np.full(k, t - 1 if t else -1), np.full(k, -1)
        for gap in range(1, min(max_gap, t) + 1):
            p = t - gap
            if not len(keep[p]) or not k:
                continue
            allowed = gap * max_step_px
            step = np.linalg.norm(pos[p][:, None] - pos[t][None], axis=2)
            move = np.where(step <= allowed, 0.5 * (step / allowed) ** 2, np.inf)
            total = cost[p][:, None] + move + miss_cost * (gap - 1)
            i = np.argmin(total, axis=0)
            better = total[i, np.arange(k)] < best
            best[better] = total[i, np.arange(k)][better]
            from_t[better], from_s[better] = p, i[better]
        cost.append(best + unary[t])
        back.append((from_t, from_s))
        # lost at t: stay lost, or lose the plate after a candidate at t-1
        prev = lost[t - 1] if t else 0.0
        if t and len(cost[t - 1]) and cost[t - 1].min() < prev:
            prev, lost_from[t] = cost[t - 1].min(), int(np.argmin(cost[t - 1]))
        lost[t] = prev + miss_cost
    chosen = np.full(n, -1)
    t = n - 1
    s = int(np.argmin(cost[t])) if len(cost[t]) and cost[t].min() < lost[t] else -1
    while t >= 0:
        if s >= 0:
            chosen[t] = keep[t][s]
            t, s = int(back[t][0][s]), int(back[t][1][s])
        else:
            t, s = t - 1, int(lost_from[t])
    return chosen


def fit_outline(gray: np.ndarray, x: float, y: float, r: float,
                band: float = 0.25, min_cover: float = 0.3) -> Outline | None:
    """Ellipse through the plate's rim edges near a seed circle, or None.

    Uses edge pixels whose gradient points along the radius (the rim, not the
    lifter's legs or the bar) and refits while shrinking the inlier band.
    """
    h, w = gray.shape
    m = int(r * (1 + band)) + 3
    x0, y0 = max(0, int(x) - m), max(0, int(y) - m)
    x1, y1 = min(w, int(x) + m + 1), min(h, int(y) + m + 1)
    roi = cv2.GaussianBlur(gray[y0:y1, x0:x1], (5, 5), 1.5)
    gx = cv2.Sobel(roi, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(roi, cv2.CV_32F, 0, 1, ksize=3)
    ys, xs = np.nonzero(cv2.Canny(roi, 20, 60))
    u, v = xs + x0 - x, ys + y0 - y
    d = np.hypot(u, v) + 1e-6
    g = np.hypot(gx[ys, xs], gy[ys, xs]) + 1e-6
    radial = np.abs(gx[ys, xs] * u + gy[ys, xs] * v) / (g * d)
    sel = (np.abs(d - r) < band * r) & (radial > 0.8)
    pts = np.column_stack([xs + x0, ys + y0])[sel].astype(np.float32)
    if len(pts) < min_cover * 2 * np.pi * r:
        return None
    for tol in (0.1, 0.05, 0.02):
        if len(pts) < 5:
            return None
        (cx, cy), (dw, dh), ang = cv2.fitEllipse(pts)
        a, b = dw / 2, dh / 2
        th = np.deg2rad(ang)
        pu, pv = pts[:, 0] - cx, pts[:, 1] - cy
        eu = np.cos(th) * pu + np.sin(th) * pv
        ev = -np.sin(th) * pu + np.cos(th) * pv
        rho = np.hypot(eu / a, ev / b)
        pts = pts[np.abs(rho - 1) < tol]
    if len(pts) < min_cover * 2 * np.pi * r:
        return None
    (cx, cy), (dw, dh), ang = cv2.fitEllipse(pts)
    a, b = dw / 2, dh / 2
    if np.hypot(cx - x, cy - y) > 0.2 * r or not (
            0.6 * r <= min(a, b) and max(a, b) <= 1.3 * r):
        return None
    return float(cx), float(cy), float(a), float(b), float(ang)


def px_per_m(a: float, b: float) -> float:
    """Scale from the outline: the major axis is the plate's true diameter."""
    return 2 * max(a, b) / PLATE_DIAMETER_M


def longest_steady_run(y: np.ndarray, tol_px: float,
                       where: np.ndarray | None = None) -> tuple[int, int]:
    """[start, end) of the longest run whose y stays within a tol_px band.

    y: smoothed height per frame; `where` restricts eligible frames.
    """
    ok = np.ones(len(y), bool) if where is None else np.asarray(where, bool)
    best, lo = (0, 0), 0
    hi_q: deque[int] = deque()  # indices of decreasing / increasing y
    lo_q: deque[int] = deque()
    for i in range(len(y)):
        if not ok[i]:
            lo, hi_q, lo_q = i + 1, deque(), deque()
            continue
        while hi_q and y[hi_q[-1]] <= y[i]:
            hi_q.pop()
        while lo_q and y[lo_q[-1]] >= y[i]:
            lo_q.pop()
        hi_q.append(i)
        lo_q.append(i)
        while y[hi_q[0]] - y[lo_q[0]] > tol_px:
            lo += 1
            if hi_q[0] < lo:
                hi_q.popleft()
            if lo_q[0] < lo:
                lo_q.popleft()
        if i + 1 - lo > best[1] - best[0]:
            best = (lo, i + 1)
    if best[1] == best[0]:
        raise ValueError("no eligible frames")
    return best


FIELDS = ("found", "hub_x", "hub_y", "a", "b", "angle", "px_per_m",
          "seed", "seed_x", "seed_y", "seed_r", "ellipse_fit")
SEED_NONE, SEED_HOUGH, SEED_GAP = 0, 1, 2


def gap_seeds(seeds: np.ndarray, max_gap: int = 24) -> np.ndarray:
    """Linear interpolation of (x, y, r) seeds across short NaN gaps.

    seeds: (n, 3), NaN where no candidate was chosen. Bridges the same gaps as
    `track` (seeds at most max_gap frames apart); longer gaps, or gaps open
    at either end, stay NaN.
    """
    out = seeds.copy()
    ok = ~np.isnan(seeds[:, 0])
    idx = np.flatnonzero(ok)
    for lo, hi in zip(idx, idx[1:]):
        if 1 < hi - lo <= max_gap:
            w = (np.arange(lo + 1, hi) - lo) / (hi - lo)
            out[lo + 1:hi] = seeds[lo] + w[:, None] * (seeds[hi] - seeds[lo])
    return out


def detect(read_frames: Callable[[], Iterable[np.ndarray]], n_frames: int,
           r_min: float = 110, r_max: float = 260,
           max_step_px: float = MAX_STEP_PX,
           progress: Callable[[str, int], None] | None = None
           ) -> dict[str, np.ndarray]:
    """Per-frame plate outline for one clip (two decodes of the frames).

    The outline is refit around the tracked Hough circle; in short gaps of
    the track, around the circle interpolated across the gap (found only if
    that refit succeeds). Where a tracked circle's refit fails, the circle
    itself is the outline.
    """
    cands = []
    for i, img in enumerate(read_frames()):
        if i >= n_frames:
            break
        cands.append(candidates(img, r_min, r_max))
        if progress:
            progress("candidates", i)
    cands += [np.empty((0, 4))] * (n_frames - len(cands))
    r0 = typical_radius(cands)
    chosen = track(cands, r0, max_step_px)
    tracked = np.full((n_frames, 3), np.nan)
    tracked[chosen >= 0] = [cands[i][chosen[i], :3]
                            for i in np.flatnonzero(chosen >= 0)]
    seeds = gap_seeds(tracked)
    out = {k: np.full(n_frames, np.nan) for k in FIELDS}
    out["found"] = np.zeros(n_frames, bool)
    out["ellipse_fit"] = np.zeros(n_frames, bool)
    out["seed"] = np.where(chosen >= 0, SEED_HOUGH,
                           np.where(np.isnan(seeds[:, 0]), SEED_NONE, SEED_GAP))
    for i, img in enumerate(read_frames()):
        if i >= n_frames:
            break
        if out["seed"][i] == SEED_NONE:
            continue
        sx, sy, sr = seeds[i]
        out["seed_x"][i], out["seed_y"][i], out["seed_r"][i] = sx, sy, sr
        fit = fit_outline(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), sx, sy, sr)
        if fit is None and out["seed"][i] == SEED_GAP:
            continue
        out["found"][i] = True
        out["ellipse_fit"][i] = fit is not None
        cx, cy, a, b, ang = fit if fit is not None else (sx, sy, sr, sr, 0.0)
        out["hub_x"][i], out["hub_y"][i] = cx, cy
        out["a"][i], out["b"][i], out["angle"][i] = a, b, ang
        out["px_per_m"][i] = px_per_m(a, b)
        if progress:
            progress("outline", i)
    out["r0"] = np.asarray(r0)
    return out
