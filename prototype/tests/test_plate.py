import cv2
import numpy as np
import pytest

from snatch.plate import (
    PLATE_DIAMETER_M, candidates, fit_outline, gap_seeds, longest_steady_run,
    px_per_m, track, typical_radius,
)


def _scene(cx: float, cy: float, a: float, b: float, angle: float = 0.0,
           size: tuple[int, int] = (1200, 800)) -> np.ndarray:
    """Dark plate (ellipse) with a blue hub on a mid-grey background."""
    img = np.full((*size, 3), 120, np.uint8)
    centre, axes = (round(cx * 16), round(cy * 16)), (round(a * 16), round(b * 16))
    cv2.ellipse(img, centre, axes, angle, 0, 360, (30, 30, 30), -1,
                cv2.LINE_AA, shift=4)
    cv2.circle(img, (round(cx), round(cy)), 20, (200, 60, 30), -1)  # hub
    return img


def test_candidates_find_the_plate_in_full_resolution_pixels():
    img = _scene(410, 700, 175, 175)
    c = candidates(img, r_min=140, r_max=210)
    x, y, r, disc = c[0]
    assert (x, y) == pytest.approx((410, 700), abs=4)
    assert r == pytest.approx(175, abs=6)
    assert disc < 60  # mean grey inside: the plate is dark


def test_fit_outline_recovers_a_circle_with_subpixel_centre():
    img = _scene(410.4, 700.6, 175, 175)
    out = fit_outline(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 405, 704, 170)
    assert out is not None
    cx, cy, a, b, _ = out
    assert (cx, cy) == pytest.approx((410.4, 700.6), abs=1.0)
    assert (a, b) == pytest.approx((175, 175), abs=2.0)


def test_fit_outline_recovers_a_plate_seen_at_an_angle():
    img = _scene(400, 650, 175, 120, angle=10)
    out = fit_outline(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 400, 650, 150)
    assert out is not None
    cx, cy, a, b, _ = out
    assert (cx, cy) == pytest.approx((400, 650), abs=1.5)
    assert max(a, b) == pytest.approx(175, abs=3)
    assert min(a, b) == pytest.approx(120, abs=3)


def test_fit_outline_gives_up_when_there_is_no_plate():
    gray = np.full((1200, 800), 120, np.uint8)
    assert fit_outline(gray, 400, 600, 170) is None


def test_px_per_m_uses_the_major_axis_as_the_true_diameter():
    assert px_per_m(175.0, 120.0) == pytest.approx(350 / PLATE_DIAMETER_M)
    assert px_per_m(120.0, 175.0) == pytest.approx(350 / PLATE_DIAMETER_M)


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


def test_typical_radius_is_the_usual_size_among_top_candidates():
    cands = [np.array([[0, 0, 175.0]])] * 8 + [np.array([[0, 0, 120.0]])] * 3
    assert typical_radius(cands) == pytest.approx(175)


def test_typical_radius_skips_bright_circles():
    # a bright wall logo ranks first in every frame; the dark plate second
    cands = [np.array([[0, 0, 197.0, 120.0], [0, 0, 155.0, 45.0]])] * 10
    assert typical_radius(cands) == pytest.approx(155)


def test_track_prefers_the_dark_moving_plate_over_a_bright_static_circle():
    cands = []
    for t in range(60):
        plate = [100 + 5.0 * t, 800 - 2.0 * t, 175, 45]
        logo = [600, 300, 175, 120]  # same size, static, ranked first
        cands.append(np.array([logo, plate]))
    chosen = track(cands, r0=175, max_step_px=20)
    assert (chosen == 1).all()


def test_track_follows_the_smooth_path_not_the_top_ranked_circle():
    cands = _plate_with_distractors()
    chosen = track(cands, r0=175, max_step_px=20)
    for t, k in enumerate(chosen):
        assert k >= 0
        assert cands[t][k][0] == pytest.approx(100 + 5.0 * t)


def test_track_marks_frames_without_the_plate_as_missing():
    cands = _plate_with_distractors()
    for t in (20, 21, 22):  # plate not detected: only distractors left
        cands[t] = cands[t][cands[t][:, 0] != 100 + 5.0 * t]
    chosen = track(cands, r0=175, max_step_px=20)
    assert [chosen[t] for t in (20, 21, 22)] == [-1, -1, -1]
    assert cands[23][chosen[23]][0] == pytest.approx(100 + 5.0 * 23)


def test_track_handles_frames_with_no_candidates():
    cands = _plate_with_distractors(10)
    cands[4] = np.empty((0, 3))
    chosen = track(cands, r0=175, max_step_px=20)
    assert chosen[4] == -1
    assert chosen[5] >= 0


def test_longest_steady_run_finds_the_hold_despite_jitter_and_sway():
    rng = np.random.default_rng(2)
    # floor, pull up, hold 150 frames at 300 (+-2 px jitter), lower
    y = np.r_[np.full(50, 900.0), np.linspace(900, 300, 50), np.full(150, 300.0),
              np.linspace(300, 900, 50)]
    y[100:250] += rng.uniform(-2, 2, 150)
    start, end = longest_steady_run(y, tol_px=6)
    assert start == pytest.approx(100, abs=2)
    assert end == pytest.approx(250, abs=2)


def test_longest_steady_run_only_counts_frames_in_the_mask():
    y = np.r_[np.full(200, 900.0), np.linspace(900, 300, 50), np.full(80, 300.0)]
    start, end = longest_steady_run(y, tol_px=6, where=y < 600)
    assert (start, end) == pytest.approx((249, 330), abs=1)


def test_gap_seeds_bridge_short_gaps_only():
    nan = np.nan
    seeds = np.array([[0, 0, 170], [nan] * 3, [nan] * 3, [30, 60, 176],
                      [nan] * 3, [nan] * 3, [nan] * 3, [70, 0, 170], [nan] * 3])
    out = gap_seeds(seeds, max_gap=3)
    assert out[1] == pytest.approx([10, 20, 172])
    assert out[2] == pytest.approx([20, 40, 174])
    assert np.isnan(out[4:7]).all()  # seeds 4 frames apart > max_gap
    assert np.isnan(out[8]).all()  # open at the end
