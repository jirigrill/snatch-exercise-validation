"""Camera-view checks for D1 (docs/results/33-d1-views.md).

Pure helpers on per-frame arrays: the plate's viewing angle from its outline,
whether a keypoint lies inside the plate outline (hidden behind it), near/far
keypoint swaps, jitter, and rectifying hub displacements from an oblique view
back to the plate plane (= the sagittal plane: the plate is perpendicular to
the bar, the bar to the sagittal plane).

Outline convention as in snatch.plate: centre (cx, cy), semi-axes a, b, and
`ang` (deg) the direction of the a axis in the image (OpenCV fitEllipse).
"""

import numpy as np


def axis_ratio(a, b):
    """Minor / major semi-axis; ~cos(viewing angle) for a round plate."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.fmin(a, b) / np.fmax(a, b)


def view_angle_deg(a, b):
    """Angle between the camera axis and the bar axis, from the axis ratio."""
    return np.degrees(np.arccos(np.clip(axis_ratio(a, b), 0, 1)))


def _ellipse_frame(dx, dy, ang):
    th = np.deg2rad(np.asarray(ang, float))
    u = np.cos(th) * dx + np.sin(th) * dy
    v = -np.sin(th) * dx + np.cos(th) * dy
    return u, v, th


def ellipse_dist(px, py, cx, cy, a, b, ang):
    """Normalised distance from the outline centre: < 1 inside, 1 on the rim."""
    u, v, _ = _ellipse_frame(np.asarray(px, float) - cx,
                             np.asarray(py, float) - cy, ang)
    return np.hypot(u / a, v / b)


def rectify(dx, dy, a, b, ang):
    """Image displacement (px) -> plate-plane displacement (px at the major
    axis's scale): stretch the minor-axis direction by major / minor.

    An affine (weak-perspective) correction. The depth change of the bar in an
    oblique view (forward travel x sin(angle)) is ignored: at 4 m, 20 cm of
    travel at 45 deg changes the scale by ~3.5%.
    """
    dx, dy = np.asarray(dx, float), np.asarray(dy, float)
    u, v, th = _ellipse_frame(dx, dy, ang)
    major = max(float(a), float(b))
    u, v = u * major / a, v * major / b
    return np.cos(th) * u - np.sin(th) * v, np.sin(th) * u + np.cos(th) * v


def swap_frames(near_raw, near_s, far_s, min_sep_px):
    """Frames where the raw near keypoint sits closer to the far side's
    smoothed track than to its own (a left/right swap), counted only where
    the two tracks are at least `min_sep_px` apart. Inputs (n, 2)."""
    own = np.linalg.norm(near_raw - near_s, axis=1)
    other = np.linalg.norm(near_raw - far_s, axis=1)
    sep = np.linalg.norm(near_s - far_s, axis=1)
    return (other < own) & (sep >= min_sep_px)


def near_plate_mask(hub, near_wrist, far_wrist):
    """Frames where the tracked outline is the near plate, not the far one:
    the hub is closer to the near wrist than to the far wrist. In an oblique
    view both plates are visible and the tracker can switch to the far one.
    Only meaningful while the lifter holds the bar. Inputs (n, 2)."""
    dn = np.linalg.norm(np.asarray(hub, float) - near_wrist, axis=1)
    df = np.linalg.norm(np.asarray(hub, float) - far_wrist, axis=1)
    return dn < df


def jitter_px(raw, smooth):
    """SD of the raw-minus-smoothed distance (px), NaN rows ignored. (n, 2)."""
    d = np.linalg.norm(np.asarray(raw, float) - smooth, axis=1)
    d = d[~np.isnan(d)]
    return float(np.sqrt(np.mean(d ** 2))) if len(d) else float("nan")


def rest_mask(hub_y_s, found, fps, still_px_s=50.0, floor_tol_px=15.0):
    """Frames with the bar resting on the floor: hub found, near its lowest
    image position (within floor_tol_px of the 98th percentile of y) and
    moving slower than still_px_s."""
    y = np.asarray(hub_y_s, float)
    speed = np.abs(np.gradient(y)) * fps
    low = np.nanpercentile(y[found], 98)
    return found & (speed < still_px_s) & (y > low - floor_tol_px)
