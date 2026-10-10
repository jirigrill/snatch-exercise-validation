import numpy as np
import pytest

from snatch.stages.probe import check_brightness, check_times, load_from, tagged_fps


def _times(n: int, fps: float) -> np.ndarray:
    return np.arange(n) / fps


def test_clean_clip_has_no_errors_or_warnings() -> None:
    assert check_times(_times(960, 240.0), 240.0) == ([], [])


def test_non_increasing_times_stop() -> None:
    t = _times(960, 240.0)
    t[100] = t[99]
    errors, _ = check_times(t, 240.0)
    assert "not strictly increasing" in errors[0]


def test_median_rate_off_the_tag_stops() -> None:
    errors, _ = check_times(_times(960, 200.0), 240.0)
    assert any("median rate" in e for e in errors)
    assert check_times(_times(960, 232.0), 240.0)[0] == []


def test_short_clip_stops_on_duration() -> None:
    errors, _ = check_times(_times(240, 240.0), 240.0)
    assert any("duration" in e for e in errors)


def test_no_frames_stops() -> None:
    assert check_times(np.array([]), 240.0)[0] == ["no frames"]


def test_low_fps_warns() -> None:
    assert check_times(_times(300, 60.0), 60.0)[1] == ["fps 60.0 is under 120"]


def test_gaps_warn() -> None:
    t = np.delete(_times(960, 240.0), [100, 101, 500])
    assert check_times(t, 240.0)[1] == ["2 frame-time gaps"]


@pytest.mark.parametrize(("mean", "warns"), [(39.0, True), (40.0, False), (220.0, False), (221.0, True)])
def test_brightness_bounds(mean: float, warns: bool) -> None:
    assert bool(check_brightness(mean)) == warns


@pytest.mark.parametrize(("flag", "name", "want"), [
    (10.0, "x_7-5kg_y.MOV", (10.0, "flag")),
    (None, "20261007_8_jiri_v3_powersnatch_7-5kg_3rep.MOV", (7.5, "filename")),
    (None, "20261001_3_jiri_v1_powersnatch_5kg_1rep.MOV", (5.0, "filename")),
    (None, "20261001_1_jiri_v1_powersnatch_bar_1rep.MOV", (None, "none")),
])
def test_load(flag: float | None, name: str, want: tuple) -> None:
    assert load_from(flag, name) == want


def test_fps_token_wins_over_the_stream_tag() -> None:
    assert tagged_fps("a_0deg_120fps.MOV", 240.0) == 120.0
    assert tagged_fps("a_0deg_right.MOV", 240.0) == 240.0
