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
MAX_SPEED_PX_S = 7200.0  # px/s at 1080 px frame width (~8.8 m/s at 820 px/m)

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


def track(cands: list[np.ndarray], r0: float, t: np.ndarray, max_speed_px_s: float,
          r_tol: float = 0.15, miss_cost: float = 1.0, reentry_cost: float = 5.0,
          rank_cost: float = 0.05, max_gap: int = 24, dark_ok: float = 60,
          dark_span: float = 40) -> np.ndarray:
    """Candidate index chosen per frame (-1 = plate not found).

    Minimises, over all frames: per-frame cost of the chosen candidate (rank,
    radius off r0, disc brighter than dark_ok grey: +1 per dark_span) or
    `miss_cost` per frame without one; 0.5 * (step / allowed)^2 for moving
    between chosen candidates k frames apart (k <= max_gap), where allowed =
    max_speed_px_s times their time gap in `t` (s) and longer
    steps are forbidden; and `reentry_cost` each time the path starts again after
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
    lost = np.zeros(n)  # best cost with the plate lost at frame f
    lost_from = np.full(n, -1)  # candidate at f-1 it was lost after, or -1
    for f in range(n):
        k = len(keep[f])
        best = np.full(k, reentry_cost + (lost[f - 1] if f else 0.0))
        from_t, from_s = np.full(k, f - 1 if f else -1), np.full(k, -1)
        for gap in range(1, min(max_gap, f) + 1):
            p = f - gap
            if not len(keep[p]) or not k:
                continue
            allowed = (t[f] - t[p]) * max_speed_px_s
            step = np.linalg.norm(pos[p][:, None] - pos[f][None], axis=2)
            move = np.where(step <= allowed, 0.5 * (step / allowed) ** 2, np.inf)
            total = cost[p][:, None] + move + miss_cost * (gap - 1)
            i = np.argmin(total, axis=0)
            better = total[i, np.arange(k)] < best
            best[better] = total[i, np.arange(k)][better]
            from_t[better], from_s[better] = p, i[better]
        cost.append(best + unary[f])
        back.append((from_t, from_s))
        prev = lost[f - 1] if f else 0.0
        if f and len(cost[f - 1]) and cost[f - 1].min() < prev:
            prev, lost_from[f] = cost[f - 1].min(), int(np.argmin(cost[f - 1]))
        lost[f] = prev + miss_cost
    chosen = np.full(n, -1)
    f = n - 1
    s = int(np.argmin(cost[f])) if len(cost[f]) and cost[f].min() < lost[f] else -1
    while f >= 0:
        if s >= 0:
            chosen[f] = keep[f][s]
            f, s = int(back[f][0][s]), int(back[f][1][s])
        else:
            f, s = f - 1, int(lost_from[f])
    return chosen


def rim_points(gray: np.ndarray, x: float, y: float, r: float,
               band: float) -> np.ndarray:
    """Edge pixels within band * r of a circle whose gradient is radial.

    Radial gradient keeps the rim (and the lettering ring) and drops the
    lifter's legs, the bar and other edges crossing the circle.
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
    return np.column_stack([xs + x0, ys + y0])[sel].astype(float)


def circle_lsq(pts: np.ndarray) -> tuple[float, float, float]:
    """Least-squares (algebraic) circle through points."""
    a = np.column_stack([2 * pts, np.ones(len(pts))])
    cx, cy, c = np.linalg.lstsq(a, (pts ** 2).sum(1), rcond=None)[0]
    return float(cx), float(cy), float(np.sqrt(c + cx ** 2 + cy ** 2))


def ransac_circle(pts: np.ndarray, r_lo: float, r_hi: float, tol: float,
                  n_hyp: int, rng: np.random.Generator
                  ) -> tuple[float, float, float] | None:
    """Circle with radius in [r_lo, r_hi] that most points lie within tol of."""
    if len(pts) < 3:
        return None
    a, b, c = (pts[rng.integers(0, len(pts), n_hyp)] for _ in range(3))
    # circumcentre of each triple
    d = 2 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
             - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    ok = np.abs(d) > 1e-6
    a, b, c, d = a[ok], b[ok], c[ok], d[ok]
    sa, sb, sc = (a ** 2).sum(1), (b ** 2).sum(1), (c ** 2).sum(1)
    ux = (sa * (b[:, 1] - c[:, 1]) + sb * (c[:, 1] - a[:, 1])
          + sc * (a[:, 1] - b[:, 1])) / d
    uy = (sa * (c[:, 0] - b[:, 0]) + sb * (a[:, 0] - c[:, 0])
          + sc * (b[:, 0] - a[:, 0])) / d
    rr = np.hypot(a[:, 0] - ux, a[:, 1] - uy)
    keep = (rr >= r_lo) & (rr <= r_hi)
    if not keep.any():
        return None
    ux, uy, rr = ux[keep], uy[keep], rr[keep]
    dist = np.hypot(pts[None, :, 0] - ux[:, None], pts[None, :, 1] - uy[:, None])
    k = int(np.argmax((np.abs(dist - rr[:, None]) < tol).sum(1)))
    return float(ux[k]), float(uy[k]), float(rr[k])


def _ellipse_residual(pts: np.ndarray, cx: float, cy: float, a: float,
                      b: float, ang: float) -> np.ndarray:
    """Approximate distance (px) of points from an ellipse."""
    th = np.deg2rad(ang)
    pu, pv = pts[:, 0] - cx, pts[:, 1] - cy
    eu = np.cos(th) * pu + np.sin(th) * pv
    ev = -np.sin(th) * pu + np.cos(th) * pv
    return (np.hypot(eu / a, ev / b) - 1) * (a + b) / 2


def ransac_ellipse(pts: np.ndarray, minor: tuple[float, float],
                   major: tuple[float, float], tol: float, n_hyp: int,
                   rng: np.random.Generator) -> Outline | None:
    """Ellipse with axes in the given (lo, hi) ranges supported by most points.

    5-point samples; then refit on the inliers until stable.
    """
    if len(pts) < 5:
        return None
    f32 = pts.astype(np.float32)
    best, best_n = None, 0
    for _ in range(n_hyp):
        sample = f32[rng.choice(len(pts), 5, replace=False)]
        try:
            (cx, cy), (dw, dh), ang = cv2.fitEllipse(sample)
        except cv2.error:
            continue
        lo, hi = sorted((dw / 2, dh / 2))
        if not (minor[0] <= lo <= minor[1] and major[0] <= hi <= major[1]):
            continue
        n = int((np.abs(_ellipse_residual(pts, cx, cy, dw / 2, dh / 2, ang))
                 < tol).sum())
        if n > best_n:
            best, best_n = (cx, cy, dw / 2, dh / 2, ang), n
    if best is None:
        return None
    for _ in range(3):
        inl = f32[np.abs(_ellipse_residual(pts, *best)) < tol]
        if len(inl) < 5:
            break
        (cx, cy), (dw, dh), ang = cv2.fitEllipse(inl)
        best = (cx, cy, dw / 2, dh / 2, ang)
    return tuple(float(v) for v in best)  # type: ignore[return-value]


def fit_outline(gray: np.ndarray, x: float, y: float, r: float,
                r0: float | None = None, band: float = 0.3,
                r_tol: float = 0.1, tol_px: float = 2.0,
                min_cover: float = 0.3, n_hyp: int = 400,
                rng_seed: int = 0, model: str = "circle",
                axes0: tuple[float, float] | None = None) -> Outline | None:
    """Plate rim near a seed circle: a circle, or an ellipse if clearly better.

    RANSAC circle over radial edge pixels, radius limited to r0 +- r_tol (the
    clip's plate radius: it barely changes within a clip, and the limit rules
    out the lettering ring at ~0.8 r and the tread crescent), then least
    squares on its inliers. An ellipse (off-axis views) replaces the circle
    only if it explains >= 15% more rim pixels. None if under min_cover of
    the rim is supported.

    model="ellipse" (plate seen at an angle): RANSAC ellipse instead, with
    the (minor, major) semi-axes within r_tol of axes0, or, without axes0,
    within 0.75-1.35 of r0.
    """
    r0 = r if r0 is None else r0
    if model == "ellipse":
        rng = np.random.default_rng(rng_seed)
        if axes0 is None:
            lims = ((0.75 * r0, 1.35 * r0),) * 2
        else:
            lims = tuple(((1 - r_tol) * v, (1 + r_tol) * v) for v in axes0)
        reach = max(r, r0, *(axes0 or ()))
        pts = rim_points(gray, x, y, reach, band)
        e = ransac_ellipse(pts, lims[0], lims[1], tol_px, n_hyp, rng)
        if e is None:
            return None
        cx, cy, a, b, ang = e
        n = int((np.abs(_ellipse_residual(pts, *e)) < tol_px).sum())
        if (n < min_cover * np.pi * (a + b)
                or np.hypot(cx - x, cy - y) > 0.35 * reach):
            return None
        return e
    pts = rim_points(gray, x, y, max(r, r0), band)
    rng = np.random.default_rng(rng_seed)
    # an ellipse up to b/a ~ 0.85 is still caught by a loose circle
    found = ransac_circle(pts, (1 - r_tol) * r0, (1 + r_tol) * r0,
                          max(tol_px, 0.06 * r0), n_hyp, rng)
    if found is None:
        return None
    cx, cy, rr = found
    for t in (max(tol_px, 0.06 * r0), 2 * tol_px, tol_px):
        inl = pts[np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - rr) < t]
        if len(inl) < 5:
            return None
        cx, cy, rr = circle_lsq(inl)
    n_circle = len(inl)
    best: Outline = (cx, cy, rr, rr, 0.0)
    near = pts[np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - rr) < 0.15 * rr]
    if len(near) >= 5:
        (ex, ey), (dw, dh), ang = cv2.fitEllipse(near.astype(np.float32))
        for _ in range(2):  # refit on the ellipse's own inliers
            e_inl = near[np.abs(_ellipse_residual(near, ex, ey, dw / 2, dh / 2,
                                                  ang)) < tol_px]
            if len(e_inl) < 5:
                break
            (ex, ey), (dw, dh), ang = cv2.fitEllipse(e_inl.astype(np.float32))
        n_ellipse = int((np.abs(_ellipse_residual(pts, ex, ey, dw / 2, dh / 2,
                                                  ang)) < tol_px).sum())
        if n_ellipse >= 1.15 * n_circle:
            best, n_circle = (ex, ey, dw / 2, dh / 2, ang), n_ellipse
    cx, cy, a, b, ang = best
    if n_circle < min_cover * 2 * np.pi * rr:
        return None
    if np.hypot(cx - x, cy - y) > 0.35 * max(r, r0) or not (
            0.6 * r0 <= min(a, b) and max(a, b) <= 1.3 * r0):
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


def radius_track(seed_r: np.ndarray, window: int = 61) -> np.ndarray:
    """Plate radius per frame: running median of the tracked Hough radius.

    Follows slow changes with depth (the plate is a few % smaller overhead)
    and drops brief blur-inflated or missing radii. NaNs are interpolated.
    """
    from scipy.ndimage import median_filter

    from snatch.signals import fill_gaps
    return np.asarray(median_filter(fill_gaps(seed_r), size=window | 1,
                                    mode="reflect"))


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


def detect(read_frames: Callable[[], Iterable[np.ndarray]], t: np.ndarray,
           r_min: float = 110, r_max: float = 260,
           max_speed_px_s: float = MAX_SPEED_PX_S,
           progress: Callable[[str, int], None] | None = None,
           model: str = "circle") -> dict[str, np.ndarray]:
    """Per-frame plate outline for one clip (three decodes of the frames).

    `t`: frame times (s).

    The outline is refit around the tracked Hough circle; in short gaps of
    the track, around the circle interpolated across the gap (found only if
    that refit succeeds). Where a tracked circle's refit fails, the circle
    itself is the outline.
    """
    n_frames = len(t)
    cands = []
    for i, img in enumerate(read_frames()):
        if i >= n_frames:
            break
        cands.append(candidates(img, r_min, r_max))
        if progress:
            progress("candidates", i)
    cands += [np.empty((0, 4))] * (n_frames - len(cands))
    r0 = typical_radius(cands)
    chosen = track(cands, r0, t, max_speed_px_s)
    tracked = np.full((n_frames, 3), np.nan)
    tracked[chosen >= 0] = [cands[i][chosen[i], :3]
                            for i in np.flatnonzero(chosen >= 0)]
    seeds = gap_seeds(tracked)
    r_ref = radius_track(tracked[:, 2]) if (chosen >= 0).any() else np.full(
        n_frames, r0)
    out = {k: np.full(n_frames, np.nan) for k in FIELDS}
    out["found"] = np.zeros(n_frames, bool)
    out["ellipse_fit"] = np.zeros(n_frames, bool)
    out["seed"] = np.where(chosen >= 0, SEED_HOUGH,
                           np.where(np.isnan(seeds[:, 0]), SEED_NONE, SEED_GAP))
    # Two outline passes. The plate is thick enough that its tread shows on
    # one side, so the rim offers two near-equal circles (near face, outer
    # silhouette) and a single fit can flip between them frame to frame.
    # Pass A fits within +-6% of the tracked Hough radius; pass B refits
    # within +-2.5% of pass A's radius smoothed over time, so neighbouring
    # frames use the same edge.
    # model="ellipse": the same two passes, pass B holding both semi-axes
    # within 6% of their smoothed tracks.
    axes_ref = None
    for pass_r, pass_tol, stage in ((r_ref, 0.06, "outline A"),
                                    (None, 0.025, "outline B")):
        if pass_r is None:
            pass_r = radius_track(out["a"]) if out["found"].any() else r_ref
            if model == "ellipse" and out["found"].any():
                lo, hi = np.fmin(out["a"], out["b"]), np.fmax(out["a"], out["b"])
                axes_ref = np.column_stack([radius_track(lo), radius_track(hi)])
                pass_tol = 0.06
            out["found"][:] = False
            for k in ("hub_x", "hub_y", "a", "b", "angle", "px_per_m"):
                out[k][:] = np.nan
        for i, img in enumerate(read_frames()):
            if i >= n_frames:
                break
            if out["seed"][i] == SEED_NONE:
                continue
            sx, sy, sr = seeds[i]
            out["seed_x"][i], out["seed_y"][i], out["seed_r"][i] = sx, sy, sr
            fit = fit_outline(
                cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), sx, sy, sr,
                r0=float(pass_r[i]), r_tol=pass_tol, rng_seed=i, model=model,
                axes0=None if axes_ref is None else tuple(axes_ref[i]))
            out["ellipse_fit"][i] = fit is not None
            if fit is None and out["seed"][i] == SEED_GAP:
                continue
            out["found"][i] = True
            cx, cy, a, b, ang = fit if fit is not None else (sx, sy, sr, sr, 0.0)
            out["hub_x"][i], out["hub_y"][i] = cx, cy
            out["a"][i], out["b"][i], out["angle"][i] = a, b, ang
            out["px_per_m"][i] = px_per_m(a, b)
            if progress:
                progress(stage, i)
    out["r0"] = np.asarray(r0)
    return out
