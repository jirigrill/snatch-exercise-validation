import numpy as np
import pytest

from snatch import skeleton as skel
from snatch.studies import skeleton as sk
def _leg(knee_deg: float, lt: float = 150.0, ls: float = 155.0, facing: float = 1.0):
    """Hip at origin, shank vertical below the knee, knee in front (facing)."""
    th = np.radians(180 - knee_deg)  # thigh tilt from vertical
    knee = np.array([[facing * lt * np.sin(th), lt * np.cos(th)]])
    ankle = knee + [[0.0, ls]]
    return np.zeros((1, 2)), knee, ankle


def test_straight_leg_too_long_is_clipped_on_the_line():
    """R3: a straight leg longer than thigh + shank is clipped onto the hip-ankle line, not NaN."""
    hip, ankle = np.zeros((1, 2)), np.array([[0.0, 320.0]])
    k, clipped = skel.two_circle_knee(hip, ankle, 150.0, 155.0)
    assert clipped[0]
    assert k[0, 0] == pytest.approx(0.0)


def test_gain_grows_toward_straight_leg():
    """R3: the knee gain grows as the leg straightens (S4b keeps RTMPose above MAX_GAIN)."""
    g = [skel.knee_gain(hip, ankle, 150.0, 155.0)[0]
         for hip, _, ankle in map(_leg, (90, 140, 170))]
    assert g[0] == pytest.approx(1.0, abs=0.05)
    assert g[0] < g[1] < g[2]
    assert g[2] > 3


def test_fill_hidden_switches_smoothly():
    """R3: S4b's fill switches between RTMPose and the rebuilt knee without a jump (moves with S4b)."""
    n = 100
    obs = np.zeros((n, 2))
    reb = np.ones((n, 2))
    use = np.zeros(n, bool)
    use[40:60] = True
    out = sk.fill_hidden(obs, reb, use, fade=11)
    assert out[0, 0] == 0 and out[50, 0] == pytest.approx(1)
    assert np.abs(np.diff(out[:, 0])).max() <= 1 / 11 + 1e-9
    reb[50] = np.nan
    assert sk.fill_hidden(obs, reb, use, fade=11)[50, 0] == 0
