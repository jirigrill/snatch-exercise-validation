import numpy as np
import pytest

from snatch.signals import fill_gaps, smooth


def test_fill_gaps_interpolates_interior_and_holds_edges():
    x = np.array([np.nan, 1.0, np.nan, 3.0, np.nan])
    assert fill_gaps(x) == pytest.approx([1.0, 1.0, 2.0, 3.0, 3.0])


def test_smooth_keeps_a_line_and_damps_jitter():
    t = np.arange(240, dtype=float)
    line = 2 * t
    assert smooth(line, fps=240, window_s=0.1) == pytest.approx(line)
    rng = np.random.default_rng(0)
    noisy = line + rng.normal(0, 5, t.size)
    resid = smooth(noisy, fps=240, window_s=0.1) - line
    assert resid.std() < 2.5
