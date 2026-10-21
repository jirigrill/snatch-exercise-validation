import numpy as np

from snatch.phases import find_phases


def test_no_dip_bar_lowest_is_bar_peak() -> None:
    """R3: no test clip is a muscle snatch: the hub keeps rising after full extension and never dips, so
    bar_lowest = bar_peak (the catch has no length) and standing still follows."""
    f = np.arange(300)
    t = f / 100
    hub_y = np.where(f < 50, 800.0, np.where(f < 150, 800 - 6.5 * (f - 50), 150 - 0.25 * (f - 150)))
    knee = np.interp(f, [0, 50, 140, 300], [90, 90, 175, 175])
    b = find_phases(knee=knee, hub_y=hub_y, hip_y=np.full(300, 500.0), knee_y=np.full(300, 650.0),
                    nose_y=np.full(300, 200.0), t=t, px_per_m=400.0).borders
    peak, lowest, standing = b["bar_peak"], b["bar_lowest"], b["standing"]
    assert peak is not None and lowest == peak
    assert standing is not None and standing >= peak
