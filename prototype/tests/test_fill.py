import numpy as np
import pytest

from snatch import fill as fl
from snatch.pose import HALPE26
from snatch.skeleton import LengthTable, two_circle_knee


def test_fill_hidden_switches_smoothly() -> None:
    """R3: the fill switches between RTMPose's and the rebuilt knee without a step; no test clip
    shows a step at a switch (it would read as a knee re-bend). The fade is in seconds: 60 fps too."""
    n = 100
    obs, reb = np.zeros((n, 2)), np.ones((n, 2))
    use = np.zeros(n, bool)
    use[40:60] = True
    t = np.arange(n) / 100
    out, w = fl.fill_hidden(obs, reb, use, t, fade_s=0.11)  # 11 frames
    assert out[0, 0] == 0 and out[50, 0] == pytest.approx(1) and w[0] == 0 and w[50] == pytest.approx(1)
    assert np.abs(np.diff(out[:, 0])).max() <= 1 / 11 + 1e-9
    reb[50] = np.nan
    assert fl.fill_hidden(obs, reb, use, t, fade_s=0.11)[0][50, 0] == 0
    assert fl.fade_frames(np.arange(n) / 60) < fl.fade_frames(np.arange(n) / 240)


def test_filled_mask_follows_the_plate() -> None:
    """R3: a plate over the knee only (frames 40-79) marks the knee hidden and fills it, within the
    cross-fade, with the hip and ankle untouched; no table (scale method none) fills nothing."""
    n, fps, side = 120, 60, "r"
    tab = LengthTable(np.linspace(0.4, 1.05, 13), np.full(12, 150.0), np.full(12, 155.0), 300.0)
    hip, ank = np.zeros((n, 2)), np.tile([0.0, 240.0], (n, 1))
    truth, _ = two_circle_knee(hip, ank, 150.0, 155.0)
    raw = np.full((n, 26, 2), np.nan)
    for name, p in (("hip", hip), ("knee", truth), ("ankle", ank)):
        raw[:, HALPE26[f"r_{name}"]] = p
    knee = HALPE26["r_knee"]
    raw[40:80, knee] += 30  # RTMPose's guess behind the plate
    t = np.arange(n) / fps
    plate = {"found": np.zeros(n, bool), "hub_x": truth[:, 0], "hub_y": truth[:, 1],
             "a": np.full(n, 100.0), "b": np.full(n, 100.0), "angle": np.zeros(n)}
    plate["found"][40:80] = True
    res = fl.fill(raw, plate, [(0, n)], t, side, tab, 1.0, 1.0)
    assert np.array_equal(np.flatnonzero(res.hidden[:, knee]), np.arange(40, 80))
    assert res.hidden.sum() == 40  # hip and ankle are clear of the plate
    near = np.flatnonzero(res.filled[:, knee])
    pad = fl.fade_frames(t) // 2
    assert near.min() >= 40 - pad and near.max() <= 79 + pad and res.filled[60, knee]
    assert res.filled.sum() == len(near)  # only the near knee
    assert np.abs(res.keypoints[60, knee] - truth[60]).max() < 1
    assert np.array_equal(res.keypoints[:, [HALPE26["r_hip"], HALPE26["r_ankle"]]], raw[:, [HALPE26["r_hip"], HALPE26["r_ankle"]]])
    none = fl.fill(raw, plate, [(0, n)], t, side, None, 1.0, 1.0)
    assert not none.filled.any() and none.hidden[:, knee].sum() == 40
    assert np.array_equal(none.keypoints, raw, equal_nan=True)
