import numpy as np
import pytest

from snatch.phases import (
    catch_frame, find_reps, find_reps_v2, liftoff_frame, lockout_frame, overhead_runs,
    pull_anchor_frame, transition_frame,
)

FPS = 100


def test_overhead_runs_drops_short_blips():
    above = np.zeros(100, bool)
    above[10:12] = True  # 2 frames: noise
    above[30:80] = True
    assert overhead_runs(above, min_len=10) == [(30, 80)]


def test_liftoff_is_where_the_continuous_rise_starts():
    # image y: wrists still at 900 px, then rise 2 px/frame from frame 40
    wrist_y = np.r_[np.full(40, 900.0), 900 - 2.0 * np.arange(1, 61)]
    assert liftoff_frame(wrist_y, end=99, fps=FPS, still_px_s=50) == 40


def test_liftoff_ignores_setup_fidgets_before_the_last_still_period():
    wrist_y = np.r_[np.full(10, 900.0), np.full(10, 880.0), np.full(20, 900.0),
                    900 - 2.0 * np.arange(1, 61)]
    assert liftoff_frame(wrist_y, end=99, fps=FPS, still_px_s=50) == 40


def test_liftoff_when_the_wrist_has_stalled_by_the_search_end():
    # rise from 40 to 70, then the bar floats (still) before the search end
    wrist_y = np.r_[np.full(40, 900.0), 900 - 10.0 * np.arange(1, 31),
                    np.full(30, 600.0)]
    assert liftoff_frame(wrist_y, end=99, fps=FPS, still_px_s=50) == 40


def test_pull_anchor_is_last_frame_with_wrists_below_hips():
    wrist_y = np.r_[np.full(10, 900.0), np.linspace(900, 500, 20)]
    hip_y = np.full_like(wrist_y, 700.0)
    # linspace crosses 700 between index 19 (710.5) and 20 (689.5)
    assert pull_anchor_frame(wrist_y, hip_y, end=29) == 19


def _clip_with_float_and_reach(reach_px: float):
    """Reach down (wrists lower), grip, rise, bar float, rise to overhead."""
    wrist_y = np.r_[np.full(50, 900.0 + reach_px), np.full(50, 900.0),
                    900 - 5.0 * np.arange(1, 61), np.full(20, 600.0),
                    600 - 10.0 * np.arange(1, 21), np.full(60, 400.0)]
    nose_y = np.full_like(wrist_y, 450.0)
    hip_y = np.full_like(wrist_y, 700.0)
    knee = np.r_[np.full(100, 60.0), _knee_with_rebend(15), 170, 170,
                 np.full(100, 172.0)]
    return dict(wrist_y=wrist_y, nose_y=nose_y, hip_y=hip_y, knee=knee)


@pytest.mark.parametrize("reach_px", [0.0, 45.0])
def test_setup_survives_a_bar_float_and_an_earlier_reach_down(reach_px):
    reps = find_reps(**_clip_with_float_and_reach(reach_px), fps=FPS)
    assert len(reps) == 1
    assert reps[0].setup == 100


def _knee_with_rebend(dip: float) -> np.ndarray:
    # first pull extends 60->130, re-bend by `dip`, second pull to 170
    up1 = np.linspace(60, 130, 30)
    down = np.linspace(130, 130 - dip, 8)
    up2 = np.linspace(130 - dip, 170, 20)
    return np.r_[up1, down, up2]


def test_transition_is_the_knee_rebend_minimum():
    knee = _knee_with_rebend(dip=15)
    assert transition_frame(knee, start=0, end=len(knee) - 1,
                            min_dip_deg=3) == 37


def test_transition_undetected_without_a_rebend():
    knee = np.linspace(60, 170, 60)
    assert transition_frame(knee, start=0, end=59, min_dip_deg=3) is None


def test_transition_ignores_dips_below_threshold():
    knee = _knee_with_rebend(dip=1)
    assert transition_frame(knee, start=0, end=len(knee) - 1,
                            min_dip_deg=3) is None


def test_find_reps_ignores_knee_dips_before_the_bar_passes_the_knees():
    clip = _clip_with_float_and_reach(0.0)
    knee = clip["knee"].copy()
    knee[103:106] -= 20  # occlusion noise, deeper than the real re-bend
    clip["knee"] = knee
    # knees at y=800: wrists (900 -> rising 5 px/frame) pass them at frame 120
    knee_y = np.full_like(knee, 800.0)
    reps = find_reps(**clip, knee_y=knee_y, fps=FPS)
    assert reps[0].transition == 137


def test_catch_is_lowest_hip_in_window():
    hip_y = np.r_[np.linspace(600, 500, 20), np.linspace(500, 700, 10),
                  np.linspace(700, 500, 30)]
    assert catch_frame(hip_y, start=0, end=59) == 29


def test_lockout_is_first_frame_knee_is_back_near_its_max():
    knee = np.r_[np.linspace(100, 175, 30), np.full(30, 175.0)]
    # within 5 deg of 175 -> first frame >= 170
    assert lockout_frame(knee, catch=0, end=59, tol_deg=5) == 28


def _synthetic_clip():
    """Two reps at 100 fps: setup still, pull with re-bend, overhead hold."""
    def rep():
        n_setup, n_pull, n_hold, n_down = 100, 60, 150, 100
        wrist = np.r_[np.full(n_setup, 900.0), np.linspace(900, 100, n_pull),
                      np.full(n_hold, 100.0), np.linspace(100, 900, n_down)]
        nose = np.full_like(wrist, 300.0)
        knee = np.r_[np.full(n_setup, 60.0), _knee_with_rebend(15), 170, 170,
                     np.linspace(170, 120, 20), np.linspace(120, 175, 40),
                     np.full(n_hold - 60, 175.0), np.full(n_down, 175.0)]
        hip = np.r_[np.full(n_setup, 700.0), np.linspace(700, 500, n_pull),
                    np.linspace(500, 650, 20), np.linspace(650, 500, 40),
                    np.full(n_hold - 60, 500.0), np.full(n_down, 500.0)]
        return wrist, nose, knee, hip
    r = rep()
    return [np.r_[a, a] for a in r]


def test_find_reps_on_two_synthetic_reps():
    wrist, nose, knee, hip = _synthetic_clip()
    reps = find_reps(wrist_y=wrist, nose_y=nose, hip_y=hip, knee=knee, fps=FPS)
    assert len(reps) == 2
    first, second = reps
    assert first.setup == pytest.approx(100, abs=2)
    assert second.setup == pytest.approx(510, abs=2)
    for r in reps:
        assert r.transition is not None
        assert r.setup < r.transition < r.catch < r.lockout
        assert r.lockout < r.overhead_end


def test_v2_times_phases_from_the_hub_not_the_wrists():
    hub, nose, knee, hip = _synthetic_clip()
    wrists = np.full_like(hub, 950.0)  # hidden behind the plate: never rise
    reps = find_reps_v2(hub_y=hub, nose_y=nose, hip_y=hip, knee=knee, fps=FPS)
    assert reps == find_reps(wrist_y=hub, nose_y=nose, hip_y=hip, knee=knee, fps=FPS)
    assert len(reps) == 2
    assert find_reps(wrist_y=wrists, nose_y=nose, hip_y=hip, knee=knee, fps=FPS) == []


def test_transition_window_cut_after_the_knee_peak_loses_the_rebend():
    knee = _knee_with_rebend(dip=6)  # local knee max at 29, re-bend min at 37
    end = len(knee) - 1
    assert transition_frame(knee, start=35, end=end, min_dip_deg=3) is None


def test_transition_v21_measures_prominence_from_setup_but_accepts_later():
    knee = _knee_with_rebend(dip=6)
    end = len(knee) - 1
    assert transition_frame(knee, start=0, end=end, min_dip_deg=3,
                            accept_from=35) == 37
    assert transition_frame(knee, start=0, end=end, min_dip_deg=3,
                            accept_from=38) is None


def test_v2_finds_the_rebend_when_the_hub_passes_the_knees_late():
    hub, nose, knee, hip = _synthetic_clip()
    # knees so low that the hub (rising 900 -> 100 over 60 frames from frame
    # 100) passes them only after the knee's local max at frame 129
    knee_y = np.full_like(hub, 415.0)  # passed at frame 136
    v1 = find_reps(wrist_y=hub, nose_y=nose, hip_y=hip, knee=knee, fps=FPS,
                   knee_y=knee_y)
    v2 = find_reps_v2(hub_y=hub, nose_y=nose, hip_y=hip, knee=knee, fps=FPS,
                      knee_y=knee_y)
    assert all(r.transition is None for r in v1)
    assert [r.transition for r in v2] == [137, 547]
