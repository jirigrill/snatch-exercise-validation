import numpy as np
import pytest

from snatch import plate
from snatch.plate import fit_outline, gap_seeds, track, typical_radius
from snatch.stages.plate import BAR_ONLY_EXIT, DEFAULT_RADIUS, TRACK_FAILED_EXIT, check


def test_fit_outline_gives_up_when_there_is_no_plate():
    """R3: a seed on a featureless patch (a missed frame); no test clip shows a fit with nothing to fit."""
    gray = np.full((1200, 800), 120, np.uint8)
    assert fit_outline(gray, 400, 600, 170) is None


def _plate_with_distractors(n: int = 60):
    """Plate moving 5 px/frame; a static ball and a far-off false circle."""
    rng = np.random.default_rng(1)
    cands = []
    for t in range(n):
        plate = [100 + 5.0 * t, 800 - 2.0 * t, 175 + rng.normal(0, 1)]
        ball = [600, 300, 120]  # wrong size, ranked first
        ghost = [rng.uniform(0, 800), rng.uniform(0, 1200), 175]
        rows = [ball, ghost, plate] if t % 3 else [plate, ball, ghost]
        cands.append(np.array(rows))
    return cands


def test_typical_radius_skips_bright_circles():
    """R3: a bright static circle (wall logo) ranks first in every frame; no test clip is known to show one."""
    cands = [np.array([[0, 0, 197.0, 120.0], [0, 0, 155.0, 45.0]])] * 10
    assert typical_radius(cands) == pytest.approx(155)


def test_track_prefers_the_dark_moving_plate_over_a_bright_static_circle():
    """R3: a bright static circle of the plate's size (wall logo); no test clip is known to show one."""
    cands = []
    for t in range(60):
        plate = [100 + 5.0 * t, 800 - 2.0 * t, 175, 45]
        logo = [600, 300, 175, 120]  # same size, static, ranked first
        cands.append(np.array([logo, plate]))
    chosen = track(cands, r0=175, t=np.arange(len(cands)) / 100, max_speed_px_s=2000)
    assert (chosen == 1).all()


def test_track_marks_frames_without_the_plate_as_missing():
    """R3: three frames with only distractors (plate missed by Hough); the track must say -1, not pick one."""
    cands = _plate_with_distractors()
    for t in (20, 21, 22):  # plate not detected: only distractors left
        cands[t] = cands[t][cands[t][:, 0] != 100 + 5.0 * t]
    chosen = track(cands, r0=175, t=np.arange(len(cands)) / 100, max_speed_px_s=2000)
    assert [chosen[t] for t in (20, 21, 22)] == [-1, -1, -1]
    assert cands[23][chosen[23]][0] == pytest.approx(100 + 5.0 * 23)


def test_track_handles_frames_with_no_candidates():
    """R3: a frame where Hough returns nothing at all (empty candidate array)."""
    cands = _plate_with_distractors(10)
    cands[4] = np.empty((0, 3))
    chosen = track(cands, r0=175, t=np.arange(len(cands)) / 100, max_speed_px_s=2000)
    assert chosen[4] == -1
    assert chosen[5] >= 0


def test_gap_seeds_bridge_short_gaps_only():
    """R3: gaps longer than max_gap (24 frames in detect) or open at the end must stay unseeded."""
    nan = np.nan
    seeds = np.array([[0, 0, 170], [nan] * 3, [nan] * 3, [30, 60, 176],
                      [nan] * 3, [nan] * 3, [nan] * 3, [70, 0, 170], [nan] * 3])
    out = gap_seeds(seeds, max_gap=3)
    assert out[1] == pytest.approx([10, 20, 172])
    assert out[2] == pytest.approx([20, 40, 174])
    assert np.isnan(out[4:7]).all()  # seeds 4 frames apart > max_gap
    assert np.isnan(out[8]).all()  # open at the end


def _fast_plate(speed_px_s: float, fps: int = 240):
    t = np.arange(fps) / fps
    # the false circle hops 3000 px a frame, so no path runs through it
    return [np.array([[3000.0 * (i % 2 + 1), 5000.0 + 97 * i, 175.0],
                      [100 + speed_px_s * ti, 800.0, 175.0]])
            for i, ti in enumerate(t)], t


@pytest.mark.parametrize("stride", [1, 4])
def test_track_step_limit_is_per_second_so_240_and_a_60_fps_subsample_both_pass(stride):
    """R3: a fast bar seen at 60 fps (a 240 fps clip subsampled); T6/T7 are 60 fps but slower."""
    cands, t = _fast_plate(6000.0)
    chosen = track(cands[::stride], r0=175, t=t[::stride], max_speed_px_s=7200.0)
    assert (chosen == 1).all()


def test_track_rejects_a_step_faster_than_the_limit():
    """R3: a hop above the speed limit is not followed (no test clip has a track that teleports)."""
    cands, t = _fast_plate(9000.0, fps=60)
    assert not (track(cands, r0=175, t=t, max_speed_px_s=7200.0) == 1).all()


def _result(n: int = 1000, found_frac: float = 1.0, hough: float = 1.0, spread: float = 0.0,
            hole: tuple[int, int] | None = None) -> dict[str, np.ndarray]:
    """Synthetic detect() output: hub rises 0.6 m (floor, lift, hold, floor), 800 px/m, 240 fps."""
    y = np.r_[np.full(n // 5, 900.0), np.linspace(900, 420, 2 * n // 5), np.full(n // 5, 420.0),
              np.linspace(420, 900, n - 4 * (n // 5))]
    found = np.arange(n) < found_frac * n
    if hole:
        found[hole[0]:hole[1]] = False
    seed = np.where(np.arange(n) < hough * n, plate.SEED_HOUGH, plate.SEED_GAP)
    ppm = 800 * (1 + spread * np.linspace(-0.5, 0.5, n))
    return {"found": found, "hub_x": np.full(n, 500.0), "hub_y": y, "px_per_m": ppm, "seed": seed}


@pytest.mark.parametrize("kwargs, code, status, words", [
    ({}, None, None, ()),
    ({"hough": 0.11, "spread": 0.23}, BAR_ONLY_EXIT, "bar_only", ("11%", "--calibrate")),  # T5-like, wins over 4
    ({"hole": (300, 700)}, TRACK_FAILED_EXIT, "plate_track_failed", ("moving", "spread")),
    ({"spread": 0.23}, TRACK_FAILED_EXIT, "plate_track_failed", ("0.2",)),
])
def test_check_stops(kwargs, code, status, words):
    """R1: exit 6 (bar-only, checked first) and exit 4 (found too rarely while moving, or px_per_m spread)."""
    res = _result(**kwargs)
    t = np.arange(len(res["found"])) / 240
    passed, reasons, stop, stats = check(res, t, 1080, "clip.MOV", DEFAULT_RADIUS)
    if code is None:
        assert stop is None and passed and not reasons
        assert stats["moving_found"] == 1.0 and stats["hough_share"] == 1.0
        assert stats["moving"][0] > 0 and stats["moving"][1] <= 1000
        return
    assert stop is not None and (stop.code, stop.status) == (code, status)
    assert all(w in stop.reason for w in words) and "clip.MOV" in stop.reason
