import math

import numpy as np
import pytest

from snatch.armbend import (PullEvents, arm_signals, phase_time, pull_events,
                            separation, window_min)
from snatch.phases import Rep


def _pts(*xy: tuple[float, float]) -> np.ndarray:
    return np.array(xy, float)


def test_straight_arm_is_in_line_and_bent_arm_is_shorter():
    sh = _pts((0, 0), (0, 0))
    el = _pts((0, 30), (15, 25))  # straight, then elbow out to the side
    hub = _pts((0, 60), (0, 45))
    s = arm_signals(sh, el, hub, hub, px_per_m=100.0)  # 1 px = 1 cm
    assert s["d_cm"] == pytest.approx([60, 45])
    assert s["straight"][0] == pytest.approx(1)
    assert s["straight"][1] < 0.9
    assert s["elbow_hub_deg"][0] == pytest.approx(180)
    assert s["elbow_hub_deg"][1] < 120


def test_pull_events_from_hub_passing_knee_and_hip():
    hub_y = np.linspace(900, 300, 61)  # rising 10 px per frame
    knee_y, hip_y = np.full(61, 700.0), np.full(61, 500.0)
    rep = Rep(setup=0, transition=30, catch=58, lockout=60,
              overhead_start=55, overhead_end=61)
    ev = pull_events(hub_y, knee_y, hip_y, rep)
    assert ev == PullEvents(setup=0, knee=21, transition=30, hip=41)


def test_phase_time_maps_events_to_0_1_2():
    ev = PullEvents(setup=10, knee=20, transition=25, hip=40)
    pt = phase_time(np.array([5, 10, 15, 20, 30, 40, 60]), ev)
    assert pt == pytest.approx([-0.5, 0, 0.5, 1, 1.5, 2, 3])
    assert np.isnan(phase_time(np.array([1]), PullEvents(0, None, None, 5))).all()


def test_window_min_and_separation():
    v, i = window_min(np.array([5.0, 3, 4, 1, 0]), 0, 3)
    assert (v, i) == (1.0, 3)
    assert math.isnan(window_min(np.zeros(3), 0, None)[0])
    s = separation([10, 11, 12], [5, 6, 7])
    assert s["diff"] == pytest.approx(-5)
    assert s["cohen_d"] == pytest.approx(-5)
    assert s["gap"] == pytest.approx(10 - 7)
    assert separation([1, 2, 3], [2.5, 4, 5])["gap"] == pytest.approx(-0.5)
