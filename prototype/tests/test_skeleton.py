import numpy as np
import pytest

from snatch.studies import skeleton as sk
def _leg(knee_deg: float, lt: float = 150.0, ls: float = 155.0, facing: float = 1.0):
    """Hip at origin, shank vertical below the knee, knee in front (facing)."""
    th = np.radians(180 - knee_deg)  # thigh tilt from vertical
    knee = np.array([[facing * lt * np.sin(th), lt * np.cos(th)]])
    ankle = knee + [[0.0, ls]]
    return np.zeros((1, 2)), knee, ankle


@pytest.mark.parametrize("deg", [70, 100, 130, 160])
@pytest.mark.parametrize("facing", [1.0, -1.0])
def test_two_circle_recovers_forward_knee(deg, facing):
    hip, knee, ankle = _leg(deg, facing=facing)
    k, clipped = sk.two_circle_knee(hip, ankle, 150.0, 155.0, facing)
    assert not clipped[0]
    assert k == pytest.approx(knee, abs=1e-6)


def test_straight_leg_too_long_is_clipped_on_the_line():
    hip, ankle = np.zeros((1, 2)), np.array([[0.0, 320.0]])
    k, clipped = sk.two_circle_knee(hip, ankle, 150.0, 155.0)
    assert clipped[0]
    assert k[0, 0] == pytest.approx(0.0)


def test_gain_grows_toward_straight_leg():
    g = [sk.knee_gain(*_leg(d)[::2], 150.0, 155.0)[0] for d in (90, 140, 170)]
    assert g[0] == pytest.approx(1.0, abs=0.05)
    assert g[0] < g[1] < g[2]
    assert g[2] > 3


def test_local_frame_signs():
    hip, knee, ankle = _leg(120)
    d, along, out = sk.local_frame(hip, ankle, knee, 1.0)
    assert out[0] > 0 and 0 < along[0] < d[0]


def test_length_table_and_scaling():
    rng = np.random.default_rng(0)
    degs = rng.uniform(60, 179, 2000)
    legs = [_leg(d) for d in degs]
    hip = np.vstack([g[0] for g in legs])
    knee = np.vstack([g[1] for g in legs])
    ankle = np.vstack([g[2] for g in legs])
    tab = sk.length_table(hip, knee, ankle, d_ref=305.0)
    lt, ls = tab.lengths(np.array([200.0, 290.0]))
    assert lt == pytest.approx([150, 150])
    assert ls == pytest.approx([155, 155])
    t2 = tab.scaled(1.1)
    lt2, _ = t2.lengths(np.array([220.0]))
    assert lt2[0] == pytest.approx(165)


def test_robust_length_and_offset():
    a = np.zeros((5, 2))
    b = np.array([[0, 10], [0, 11], [0, 12], [0, 13], [0, 100.0]])
    assert sk.robust_length(a, b) == 12
    assert sk.robust_length(a, b, how="p50") == 12
    o, sd = sk.fit_offset(b, a)
    assert o == pytest.approx([0, 12])
    assert sk.wrist_from_hub(a, o)[0] == pytest.approx([0, 12])


def test_pull_windows_and_labels():
    fps = 100.0
    n = 300
    y = np.full(n, 900.0)
    y[100:200] = np.linspace(900, 400, 100)  # bar rises from frame 100
    y[200:] = 400
    knee_y, hip_y = np.full(n, 750.0), np.full(n, 550.0)
    knee_deg = np.full(n, 120.0)
    knee_deg[215] = 170
    ev = sk.pull_windows(y, knee_y, hip_y, knee_deg, fps)
    assert len(ev) == 1
    e = ev[0]
    assert e["setup"] in (100, 101) and e["knee"] == 130 and e["hip"] == 170 and e["peak"] == 215
    lab = sk.phase_labels(n, e, fps)
    assert lab[90] == 0 and lab[120] == 1 and lab[150] == 2 and lab[200] == 3 and lab[250] == -1


def test_fill_hidden_switches_smoothly():
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
