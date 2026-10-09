"""Body height from a side-on clip: head top to floor, scaled at the body's depth.

Geometry (pinhole, phone level, lens axis along the bar; docs/results/35):
- The near plate's scale (px_per_m, plate.npz) holds at the near plate's
  depth Z_n. The lifter's head top and the floor line under the lifter's
  midline are at the bar centre's depth Z_c > Z_n, where the scale is
  k * px_per_m with k = Z_n / Z_c.
- k from the far plate (`midline_ratio`): both bumpers are 450 mm and
  symmetric about the bar centre, so 1/scale is linear in depth and the bar
  centre's 1/scale is the mean of the two plates'. k = 2 / (1 + r_near/r_far).
  Needs no camera distance and no sleeve length, and holds for a yawed bar.
- k from the protocol (`protocol_ratio`): Z_c = 4 m, Z_n = Z_c - s, s = bar
  centre to the near plate's outer face.
- Floor under the midline: the visible bottom of the near shoe sits nearer
  than the midline, so it reads low in the image. `floor_from_sole` moves it
  up by the perspective shift of half the stance plus half a shoe width; the
  stance comes from the ankle keypoints' image-height difference.
  `floor_from_plate` instead uses the plate resting on the floor and the
  camera height it implies (needs the principal point; image centre assumed).
"""

import cv2
import numpy as np

from snatch.angles import COCO

PLATE_RADIUS_M = 0.225


def midline_ratio(r_near: float, r_far: float) -> float:
    """k = Z_near / Z_centre from the near and far plate radii (px)."""
    return 2.0 / (1.0 + r_near / r_far)


def protocol_ratio(z_centre_m: float = 4.0, s_m: float = 0.70) -> float:
    """k = Z_near / Z_centre from the camera distance and the plate offset."""
    return (z_centre_m - s_m) / z_centre_m


def camera_height_m(hub_rest_y: float, px_per_m_near: float, cy: float) -> float:
    """Lens height above the floor from the near plate resting on the floor."""
    return PLATE_RADIUS_M + (hub_rest_y - cy) / px_per_m_near


def floor_from_plate(hub_rest_y: float, px_per_m_near: float, k: float,
                     cy: float) -> float:
    """Image row of the floor at the bar centre's depth.

    Floor at depth Z projects to cy + f*hc/Z; with f/Z_c = k * px_per_m_near
    and hc from the resting plate.
    """
    hc = camera_height_m(hub_rest_y, px_per_m_near, cy)
    return cy + k * px_per_m_near * hc


def floor_from_sole(sole_y: float, ankle_near_y: float, ankle_far_y: float,
                    px_mid: float, z_centre_m: float, hc_m: float,
                    ankle_h_m: float = 0.10, half_shoe_m: float = 0.05) -> float:
    """Image row of the floor under the midline from the near shoe's lowest pixel.

    Ankles at height ha project (hc - ha) * f * (1/Z_near - 1/Z_far) apart;
    that gives the half stance d. The lowest shoe pixel is the sole's
    camera-side edge at d + half_shoe nearer than the midline, so it reads
    px_mid * hc * (d + half_shoe) / Z_c lower than the midline floor.
    """
    d = (ankle_near_y - ankle_far_y) / 2 / px_mid * z_centre_m / (hc_m - ankle_h_m)
    d = max(d, 0.0)
    return sole_y - px_mid * hc_m * (d + half_shoe_m) / z_centre_m


def facing(kps: np.ndarray) -> float:
    """+1 if the lifter faces image +x (nose ahead of the ears), else -1."""
    ear_x = kps[[COCO["l_ear"], COCO["r_ear"]], 0].mean()
    return 1.0 if kps[COCO["nose"], 0] >= ear_x else -1.0


def foreground(img: np.ndarray, bg: np.ndarray, thresh: float = 35) -> np.ndarray:
    d = np.abs(img.astype(np.int16) - bg.astype(np.int16)).max(2)
    m = (d > thresh).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0


def head_top(img: np.ndarray, bg: np.ndarray, kps: np.ndarray, px_per_m: float,
             max_above_eye_m: float = 0.20, gap_px: int = 3,
             discs: tuple[tuple[float, float, float], ...] = ()
             ) -> tuple[float, float] | None:
    """(x, y) of the top of the head: the highest foreground pixel above the eyes.

    Columns from just behind the ear to between ear and nose. In each column
    the foreground run is followed up from eye level (gaps <= gap_px). A run
    reaching more than max_above_eye_m above the eyes is an arm or the bar
    (lockout) and the column is dropped. The head top is the 3rd highest of
    the remaining column tops (robust to a stray pixel). `discs` (x, y, r):
    the plates; a column whose run reaches a disc is occluded and dropped.
    """
    fg = foreground(img, bg)
    blocked = np.zeros(fg.shape, np.uint8)
    for dx, dy, dr in discs:
        cv2.circle(blocked, (int(round(dx)), int(round(dy))), int(dr + 4), 1, -1)
    sgn = facing(kps)
    ear_x = kps[[COCO["l_ear"], COCO["r_ear"]], 0].mean()
    nose_x = kps[COCO["nose"], 0]
    eye_y = kps[[COCO["l_eye"], COCO["r_eye"], COCO["l_ear"], COCO["r_ear"]], 1].min()
    xa = ear_x - sgn * 0.07 * px_per_m
    xb = ear_x + 0.6 * (nose_x - ear_x)
    x0, x1 = sorted((int(round(xa)), int(round(xb))))
    y_eye = int(round(eye_y))
    lim = int(max_above_eye_m * px_per_m)
    tops = []
    for x in range(max(x0, 0), min(x1 + 1, img.shape[1])):
        y_lo = max(y_eye - lim - 5, 0)
        col = fg[y_lo:y_eye + 1, x][::-1]  # upward from eye
        blk = blocked[y_lo:y_eye + 1, x][::-1]
        if not col[:4].any() or blk[:4].any():
            continue
        run, gap, top, hit = 0, 0, 0, False
        for i, v in enumerate(col):
            if blk[i]:
                hit = True
                break
            if v:
                top, gap = i, 0
            else:
                gap += 1
                if gap > gap_px:
                    break
            run = i
        if hit or top >= lim or run >= len(col) - 1 and top > lim - 5:
            continue  # arm / bar: runs on above the head
        tops.append((y_eye - top, x))
    if len(tops) < 5:
        return None
    tops.sort()
    y, x = tops[min(2, len(tops) - 1)]
    return float(x), float(y)


def green_mask(img: np.ndarray) -> np.ndarray:
    """Neon-green shoe pixels (the 2026-10-07 shoes)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, np.array([35, 70, 80]), np.array([85, 255, 255]))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0


def sole_bottom(img: np.ndarray, kps: np.ndarray, px_per_m: float
                ) -> tuple[float, float] | None:
    """(x, y) of the lowest shoe pixel near the ankles (green mask)."""
    ax = kps[[COCO["l_ankle"], COCO["r_ankle"]], 0]
    ay = kps[[COCO["l_ankle"], COCO["r_ankle"]], 1].max()
    x0 = int(max(ax.min() - 0.25 * px_per_m, 0))
    x1 = int(min(ax.max() + 0.30 * px_per_m, img.shape[1]))
    y0 = int(max(ay - 0.10 * px_per_m, 0))
    y1 = int(min(ay + 0.25 * px_per_m, img.shape[0]))
    m = green_mask(img[y0:y1, x0:x1])
    ys, xs = np.nonzero(m)
    if len(ys) < 50:
        return None
    # lowest row with a few green pixels (not a lone speck)
    rows = np.bincount(ys, minlength=m.shape[0])
    ok = np.flatnonzero(rows >= 3)
    if not len(ok):
        return None
    yb = ok.max()
    return float(xs[ys == yb].mean() + x0), float(yb + y0 + 0.5)


def find_near_plate(gray: np.ndarray, kps: np.ndarray, r0: float,
                    r_range: tuple[float, float] = (0.9, 1.15)
                    ) -> tuple[float, float, float, float, float] | None:
    """Near plate outline (x, y, a, b, angle) held by the lifter, found afresh.

    For frames where plate.npz lost the plate or followed another round
    object (2026-10-07: the air-bike wheels). The hub is near the wrists
    (the hands hold the bar next to it), so Hough circles of r_range * r0
    with the centre within 1.6 r0 of the wrists' mean are refined with
    snatch.plate.fit_outline; the one with the most rim support wins.
    """
    from snatch.plate import fit_outline, rim_points

    wx, wy = kps[[COCO["l_wrist"], COCO["r_wrist"]]].mean(0)
    h, w = gray.shape
    x0, y0 = max(int(wx - 3 * r0), 0), max(int(wy - 3 * r0), 0)
    x1, y1 = min(int(wx + 3 * r0), w), min(int(wy + 3 * r0), h)
    roi = cv2.GaussianBlur(gray[y0:y1, x0:x1], (5, 5), 1.5)
    cs = cv2.HoughCircles(roi, cv2.HOUGH_GRADIENT, dp=1, minDist=5, param1=60,
                          param2=20, minRadius=int(r_range[0] * r0),
                          maxRadius=int(r_range[1] * r0))
    if cs is None:
        return None
    best, best_n = None, 0
    for cx, cy, rr in cs[0][:20]:
        cx, cy = cx + x0, cy + y0
        if np.hypot(cx - wx, cy - wy) > 1.6 * r0:
            continue
        o = fit_outline(gray, float(cx), float(cy), float(rr), r0=r0, r_tol=0.1)
        if o is None:
            continue
        pts = rim_points(gray, o[0], o[1], max(o[2], o[3]), 0.1)
        rad = np.hypot(pts[:, 0] - o[0], pts[:, 1] - o[1])
        n = int((np.abs(rad - np.sqrt(o[2] * o[3])) < 2.0).sum())
        if n > best_n:
            best, best_n = o, n
    return best


def fit_far_plate(gray: np.ndarray, near: tuple[float, float, float],
                  pp: tuple[float, float] | None = None,
                  q_range: tuple[float, float] = (0.6, 0.8), lateral: float = 0.5
                  ) -> tuple[float, float, float, int] | None:
    """Far plate circle (x, y, r, n_inliers) next to the near plate (x, y, r).

    The near disc is painted over with the plate's dark tone, Hough finds
    circles of 0.55-0.85 r_near in the area the far plate can appear
    (toward the principal point and below, as the bar is above the lens at
    lockout), and the best is refined by least squares on Canny edges
    outside the near disc. A bar along the lens axis puts the far hub at
    pp + q (near - pp), q = Z_near / Z_far; candidates must lie within
    lateral * r_near of that segment for q in q_range (a yawed bar shifts it
    sideways), radius within q_range * r_near.
    """
    from snatch.plate import circle_lsq

    nx, ny, rn = near
    h, w = gray.shape
    px, py = pp if pp is not None else (w / 2, h / 2)
    a = np.array([px + q_range[0] * (nx - px), py + q_range[0] * (ny - py)])
    b = np.array([px + q_range[1] * (nx - px), py + q_range[1] * (ny - py)])

    def corridor(cx: float, cy: float) -> bool:
        t = np.clip(np.dot((cx, cy) - a, b - a) / np.dot(b - a, b - a), 0, 1)
        return bool(np.hypot(*((cx, cy) - (a + t * (b - a)))) <= lateral * rn)

    m = gray.copy()
    sx0, sx1 = int(nx + 0.5 * rn), int(nx + 0.6 * rn)
    dark = int(np.median(gray[max(int(ny) - 10, 0):int(ny) + 10, sx0:sx1]))
    cv2.circle(m, (int(nx), int(ny)), int(rn + 3), dark, -1)
    x0, y0 = max(int(nx - 2.2 * rn), 0), max(int(ny - 0.6 * rn), 0)
    x1, y1 = min(int(nx + 2.2 * rn), w), min(int(ny + 2.2 * rn), h)
    roi = cv2.GaussianBlur(m[y0:y1, x0:x1], (5, 5), 1.5)
    cs = cv2.HoughCircles(roi, cv2.HOUGH_GRADIENT, dp=1, minDist=5, param1=60,
                          param2=15, minRadius=int(q_range[0] * rn), maxRadius=int(q_range[1] * rn))
    if cs is None:
        return None
    ys, xs = np.nonzero(cv2.Canny(roi, 20, 60))
    pts = np.column_stack([xs + x0, ys + y0]).astype(float)
    pts = pts[np.hypot(pts[:, 0] - nx, pts[:, 1] - ny) > rn + 5]
    best = None
    cands = [cc for cc in cs[0] if corridor(cc[0] + x0, cc[1] + y0)][:15]
    for cx, cy, rr in cands:
        cx, cy = cx + x0, cy + y0
        inl = pts[:0]
        for t in (4.0, 2.5, 1.5):
            inl = pts[np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - rr) < t]
            if len(inl) < 10:
                break
            cx, cy, rr = circle_lsq(inl)
        if len(inl) >= 10 and q_range[0] * rn < rr < q_range[1] * rn and corridor(cx, cy) and (
                best is None or len(inl) > best[3]):
            best = (float(cx), float(cy), float(rr), len(inl))
    return best
