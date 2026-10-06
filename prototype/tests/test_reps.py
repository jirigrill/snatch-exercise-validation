import numpy as np

from snatch.reps import Lift, find_lifts, pose_range, runs

FPS = 100.0


def _lift(h: np.ndarray, start: int, up: int, top: float, hold: int, down: int) -> None:
    """Hub rises linearly to `top` m, holds, falls back to the floor."""
    h[start:start + up] = np.linspace(0, top, up)
    h[start + up:start + up + hold] = top
    h[start + up + hold:start + up + hold + down] = np.linspace(top, 0, down)


def test_runs_are_half_open():
    assert runs(np.array([0, 1, 1, 0, 1], bool)) == [(1, 3), (4, 5)]


def test_two_lifts_with_a_rest_between():
    h = np.zeros(1000)
    _lift(h, 100, 50, 1.5, 100, 30)
    _lift(h, 600, 50, 1.5, 100, 30)
    lifts = find_lifts(h, FPS)
    assert [(lf.start, lf.end) for lf in lifts] == [(100, 280), (600, 780)]
    assert lifts[0].peak_m == 1.5


def test_a_short_bounce_after_a_drop_stays_one_lift():
    h = np.zeros(800)
    _lift(h, 100, 50, 1.5, 50, 20)  # dropped, back on the floor at 220
    _lift(h, 230, 5, 0.15, 0, 5)  # bounce 10 frames later
    assert len(find_lifts(h, FPS)) == 1


def test_low_movements_are_not_lifts():
    h = np.zeros(500)
    _lift(h, 100, 20, 0.2, 10, 20)  # bar rolled / nudged, never pulled
    assert find_lifts(h, FPS) == []


def test_pose_range_pads_and_clips_to_the_clip():
    assert pose_range(Lift(50, 300, 1.0), FPS, 350) == (0, 350)
    assert pose_range(Lift(500, 700, 1.0), FPS, 1000) == (400, 800)


def test_overhead_lifts_from_sparse_pose():
    from snatch.reps import find_pose_lifts
    n = 1000
    nan = np.full(n, np.nan)
    wrist, nose, knee, hip = nan.copy(), nan.copy(), nan.copy(), nan.copy()
    s = np.arange(0, n, 10)  # sparse: every 10th frame posed
    nose[s], knee[s], hip[s] = 100.0, 400.0, 300.0
    wrist[s] = 350.0  # hands at the thighs: resting between reps
    wrist[s[(s >= 100) & (s < 130)]] = 450.0  # gripping the bar
    wrist[s[(s >= 150) & (s < 300)]] = 50.0  # overhead
    wrist[s[(s >= 300) & (s < 320)]] = 200.0  # lowering, still above the hips
    wrist[s[(s >= 700) & (s < 705)]] = 50.0  # one sample overhead: too short
    lifts = find_pose_lifts(wrist, nose, knee, hip, FPS)
    assert [(lf.start, lf.end) for lf in lifts] == [(120, 321)]


def test_pose_holds_are_long_runs_with_the_wrists_above_mid_thigh():
    from snatch.reps import find_pose_holds
    n = 1000
    wrist, knee, hip = (np.full(n, np.nan) for _ in range(3))
    s = np.arange(0, n, 10)
    knee[s], hip[s], wrist[s] = 400.0, 300.0, 420.0  # bar on the floor
    wrist[s[(s >= 200) & (s < 600)]] = 300.0  # standing hold, bar at the hips
    wrist[s[(s >= 800) & (s < 820)]] = 300.0  # too short
    assert [(h.start, h.end) for h in find_pose_holds(wrist, knee, hip, FPS)] == [(200, 591)]
