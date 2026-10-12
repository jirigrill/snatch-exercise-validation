import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from snatch.stage import Context, run_stages
from snatch.stages.probe import STAGE, check_brightness, check_times, load_from, rate_reference


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


CAMERA = {"com.apple.quicktime.make": "Apple"}
REMUX = {"encoder": "Lavf63.1.101"}


def test_fps_token_wins_over_the_stream_tag() -> None:
    assert rate_reference("a_0deg_120fps.MOV", 240.0, CAMERA) == (120.0, "filename")
    assert rate_reference("a_0deg_60fps.MOV", 50.0, REMUX) == (60.0, "filename")


def test_camera_original_trusts_the_stream_tag() -> None:
    assert rate_reference("a_0deg_right.MOV", 240.0, CAMERA) == (240.0, "camera")


@pytest.mark.parametrize("tags", [REMUX, {**CAMERA, **REMUX}, {}])
def test_untokened_remux_has_no_reference(tags: dict) -> None:
    assert rate_reference("untokened.MOV", 50.0, tags) == (None, "none")


def test_no_reference_warns_cannot_verify_rate() -> None:
    errors, warnings = check_times(_times(960, 200.0), None)
    assert errors == []
    assert any("cannot verify frame rate" in w for w in warnings)


def _clip(path: Path, seconds: float) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc=size=160x120:rate=240:duration={seconds}", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


@needs_ffmpeg
def test_bad_clip_leaves_no_sheet(tmp_path: Path) -> None:
    ctx = Context(_clip(tmp_path / "a_240fps.mp4", 1), tmp_path / "out")
    assert run_stages([STAGE], ctx, log=lambda _: None) == 3
    assert not (ctx.out / "overlays" / "0_clip_sheet.jpg").exists()


@needs_ffmpeg
def test_clip_json_fps_and_frame_times_are_measured(tmp_path: Path) -> None:
    ctx = Context(_clip(tmp_path / "a_240fps.mp4", 3), tmp_path / "out")
    assert run_stages([STAGE], ctx, log=lambda _: None) == 0
    clip = json.loads((ctx.out / "clip.json").read_text())
    t = np.load(ctx.out / "frame_times.npy")
    assert (clip["fps_reference"], clip["fps_reference_source"]) == (240.0, "filename")
    assert clip["fps"] == pytest.approx(240.0, rel=1e-3)
    assert len(t) == clip["n_frames"] and t[0] == 0
    assert (ctx.out / "overlays" / "0_clip_sheet.jpg").exists()


@needs_ffmpeg
def test_frame_times_keep_measured_jitter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from snatch.stages import probe

    ctx = Context(_clip(tmp_path / "a_240fps.mp4", 3), tmp_path / "out")
    stream, tags, pts = probe._ffprobe(ctx.clip)
    jittered = pts + 10.0 + np.where(np.arange(len(pts)) % 7 == 3, 0.0008, 0.0)
    monkeypatch.setattr(probe, "_ffprobe", lambda _: (stream, tags, jittered))
    assert run_stages([STAGE], ctx, log=lambda _: None) == 0
    np.testing.assert_allclose(np.load(ctx.out / "frame_times.npy"), jittered - jittered[0])
