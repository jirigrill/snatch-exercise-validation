"""Per-frame signal clean-up: fill missing frames, Savitzky-Golay smoothing."""

import numpy as np
from scipy.signal import savgol_filter


def fill_gaps(x: np.ndarray) -> np.ndarray:
    """Linear interpolation over NaNs; edges hold the nearest value."""
    x = np.asarray(x, float)
    ok = ~np.isnan(x)
    idx = np.arange(x.size)
    return np.interp(idx, idx[ok], x[ok])


def smooth(x: np.ndarray, fps: float, window_s: float = 0.1,
           polyorder: int = 2) -> np.ndarray:
    window = int(round(window_s * fps)) | 1  # odd
    return np.asarray(savgol_filter(fill_gaps(x), window, polyorder))
