import math

import numpy as np
import pytest

from snatch.studies.markers import bar_markers, group_verdict, verdict
from snatch.phases import Rep

FPS = 100
PPM = 100.0  # 1 px = 1 cm


def _rep(transition: int | None = 40) -> Rep:
    return Rep(setup=10, transition=transition, catch=68, lockout=100,
               overhead_start=62, overhead_end=150)


def _path(points: list[tuple[int, float]], n: int = 150) -> np.ndarray:
    frames, values = zip(*points)
    return np.interp(np.arange(n), frames, values)


def test_bar_displacements_follow_the_hub_path():
    # bar rises from frame 10 to its peak at 60, drops into the catch at 70,
    # stands up by 100. Toward the lifter is -x.
    hub_y = _path([(10, 500), (60, 300), (70, 320), (100, 290)])
    hub_x = _path([(10, 0), (30, -4), (55, 2), (60, 2), (70, -1)])
    m = bar_markers(hub_x, hub_y, PPM, FPS, _rep())
    assert m.peak_frame == 60
    assert m.bar_catch_frame == 70
    assert m.x1_cm == pytest.approx(4)  # back 4 cm in the first pull
    assert m.x2_cm == pytest.approx(6)  # then forward 6 cm
    assert m.xloop_cm == pytest.approx(3)  # back 3 cm after the peak
    assert m.xnet_cm == pytest.approx(-1)  # caught 1 cm behind the start
    assert m.drop_cm == pytest.approx(20)


def test_peak_velocity_and_turnover_from_hub_height():
    # upward speed (m/s): ramps to 2.0 at frame 50, down to -1.0 at 70, 0 at 80
    vy = _path([(10, 0), (50, 2.0), (70, -1.0), (80, 0)])
    hub_y = 500 - np.cumsum(vy) / FPS * PPM
    m = bar_markers(np.zeros_like(hub_y), hub_y, PPM, FPS, _rep())
    assert m.peak_v_m_s == pytest.approx(2.0, abs=0.06)
    assert m.turnover_s == pytest.approx(0.20, abs=0.011)
    # the bar comes to rest at frame 80: the bar catch
    assert m.turnover_to_bar_catch_s == pytest.approx(0.30, abs=0.011)


def test_verdict_compares_the_worst_error_with_rep_to_rep_spread():
    assert verdict(max_err=0.4, spread=1.0) == "usable"
    assert verdict(max_err=0.5, spread=1.0) == "usable"
    assert verdict(max_err=0.9, spread=1.0) == "marginal"
    assert verdict(max_err=1.5, spread=1.0) == "unusable"
    assert verdict(max_err=float("nan"), spread=1.0) == "unusable"  # not detected


def test_group_verdict_is_the_majority_and_ties_go_to_the_worse():
    assert group_verdict(["usable", "usable", "unusable"]) == "usable"
    assert group_verdict(["usable", "marginal"]) == "marginal"
    assert group_verdict(["marginal", "unusable", "usable", "unusable"]) == "unusable"


def test_x1_ends_at_the_transition_even_if_the_bar_keeps_coming_back():
    hub_y = _path([(10, 500), (60, 300), (70, 320), (100, 290)])
    hub_x = _path([(10, 0), (30, -2), (40, -1), (60, -10)])
    m = bar_markers(hub_x, hub_y, PPM, FPS, _rep())
    assert m.x1_cm == pytest.approx(2)
    assert m.x2_cm == pytest.approx(1)


def test_no_transition_means_no_x1_or_x2():
    hub_y = _path([(10, 500), (60, 300), (70, 320), (100, 290)])
    m = bar_markers(np.zeros_like(hub_y), hub_y, PPM, FPS, _rep(transition=None))
    assert math.isnan(m.x1_cm) and math.isnan(m.x2_cm)
    assert m.drop_cm == pytest.approx(20)


def test_no_spread_at_240_fps_gives_no_verdict():
    assert verdict(max_err=0.0, spread=0.0) == "n/a"
    assert group_verdict(["n/a", "marginal"]) == "marginal"
    assert group_verdict(["n/a", "n/a"]) == "n/a"


def test_peak_velocity_and_turnover_with_dropped_frames():
    # the clip above with one frame in 6 dropped (as the 2026-10-05 clips):
    # with the real frame times the markers come out as without the drops
    vy = _path([(10, 0), (50, 2.0), (70, -1.0), (80, 0)])
    hub_y = 500 - np.cumsum(vy) / FPS * PPM
    keep = np.array([i for i in range(len(hub_y)) if i % 6 != 5])
    t = keep / FPS
    at = lambda f: int(np.searchsorted(keep, f))  # noqa: E731
    r = _rep()
    rep = Rep(at(r.setup), at(r.transition), at(r.catch), at(r.lockout),
              at(r.overhead_start), at(r.overhead_end))
    rate = (len(t) - 1) / t[-1]
    m = bar_markers(np.zeros(len(keep)), hub_y[keep], PPM, rate, rep, t=t)
    assert m.peak_v_m_s == pytest.approx(2.0, abs=0.06)
    assert m.turnover_s == pytest.approx(0.20, abs=0.02)
    assert m.turnover_to_bar_catch_s == pytest.approx(0.30, abs=0.02)
    wrong = bar_markers(np.zeros(len(keep)), hub_y[keep], PPM, rate, rep)  # frame / mean rate
    assert abs(wrong.peak_v_m_s - 2.0) > 0.1
