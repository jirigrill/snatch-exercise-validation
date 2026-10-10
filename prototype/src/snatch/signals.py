"""Per-frame signal clean-up: fill missing frames, Savitzky-Golay smoothing."""

import numpy as np
from scipy.signal import savgol_filter


def fill_gaps(x: np.ndarray) -> np.ndarray:
    """Linear interpolation over NaNs; edges hold the nearest value."""
    x = np.asarray(x, float)
    ok = ~np.isnan(x)
    idx = np.arange(x.size)
    return np.interp(idx, idx[ok], x[ok])


def window_frames(t: np.ndarray, window_s: float) -> int:
    """Typical number of frames spanning `window_s` seconds of the times `t`."""
    t = np.asarray(t, float)
    ahead = np.searchsorted(t, t + window_s - 1e-9) - np.arange(len(t))
    full = t + window_s <= t[-1] + 1e-9
    return int(np.median(ahead[full] if full.any() else ahead))


def smooth(x: np.ndarray, fps: float | None = None, window_s: float = 0.1,
           polyorder: int = 2, t: np.ndarray | None = None) -> np.ndarray:
    """Pass `t` (frame times, s) or `fps` (uniform frames); `t` wins."""
    if t is not None:
        n = window_frames(t, window_s)
    elif fps is not None:
        n = int(round(window_s * fps))
    else:
        raise ValueError("smooth needs t or fps")
    window = n | 1
    return np.asarray(savgol_filter(fill_gaps(x), window, polyorder))


def smooth_keypoints(kps: np.ndarray, fps: float,
                     t: np.ndarray | None = None) -> np.ndarray:
    """`smooth` applied to every coordinate of (n_frames, n_joints, 2)."""
    return np.stack([np.stack([smooth(kps[:, j, d], fps, t=t) for d in (0, 1)], -1)
                     for j in range(kps.shape[1])], 1)
