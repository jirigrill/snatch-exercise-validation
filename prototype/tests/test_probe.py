import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from snatch.stage import Context, run_stages
from snatch.stages.probe import STAGE, check_brightness, check_times, rate_reference


def _times(n: int, fps: float) -> np.ndarray:
    return np.arange(n) / fps


def test_non_increasing_times_stop() -> None:
    """R1: frame times that do not increase: exit 3."""
    t = _times(960, 240.0)
    t[100] = t[99]
    errors, _ = check_times(t, 240.0)
    assert "not strictly increasing" in errors[0]


def test_median_rate_off_the_tag_stops() -> None:
    """R1: measured rate far from the filename's rate: exit 3."""
    errors, _ = check_times(_times(960, 200.0), 240.0)
    assert any("median rate" in e for e in errors)
    assert check_times(_times(960, 232.0), 240.0)[0] == []


def test_short_clip_stops_on_duration() -> None:
    """R1: a clip too short for a lift: exit 3."""
    errors, _ = check_times(_times(240, 240.0), 240.0)
    assert any("duration" in e for e in errors)


def test_no_frames_stops() -> None:
    """R1: a clip without frames: exit 3."""
    assert check_times(np.array([]), 240.0)[0] == ["no frames"]


@pytest.mark.parametrize(("mean", "warns"), [(39.0, True), (40.0, False), (220.0, False), (221.0, True)])
def test_brightness_bounds(mean: float, warns: bool) -> None:
    """R3: too dark or too bright frames are flagged (all test clips are well lit)."""
    assert bool(check_brightness(mean)) == warns


CAMERA = {"com.apple.quicktime.make": "Apple"}
REMUX = {"encoder": "Lavf63.1.101"}


def test_camera_original_trusts_the_stream_tag() -> None:
    """R3: an uncut camera file trusts its rate tag (every test clip is a remux)."""
    assert rate_reference("a_0deg_right.MOV", 240.0, CAMERA) == (240.0, "camera")


@pytest.mark.parametrize("tags", [REMUX, {**CAMERA, **REMUX}, {}])
def test_untokened_remux_has_no_reference(tags: dict) -> None:
    """R3: a remux without the _<n>fps token has no rate to check against: a warning, not an error."""
    assert rate_reference("untokened.MOV", 50.0, tags) == (None, "none")
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
def test_bad_clip_keeps_the_sheet_but_no_meta(tmp_path: Path) -> None:
    """R1: a stopped probe still has its clip sheet (PSTOP: written when decodable), no clip.json or meta."""
    ctx = Context(_clip(tmp_path / "a_240fps.mp4", 1), tmp_path / "out")
    assert run_stages([STAGE], ctx, log=lambda _: None) == 3
    assert (ctx.out / "overlays" / "0_clip_sheet.jpg").exists()
    assert not (ctx.out / "S-1.meta.json").exists() and not (ctx.out / "clip.json").exists()


@needs_ffmpeg
def test_frame_times_keep_measured_jitter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R3: frame times keep the measured jitter, not an even grid (check_pipeline only checks they increase)."""
    from snatch.stages import probe

    ctx = Context(_clip(tmp_path / "a_240fps.mp4", 3), tmp_path / "out")
    stream, tags, pts = probe._ffprobe(ctx.clip)
    jittered = pts + 10.0 + np.where(np.arange(len(pts)) % 7 == 3, 0.0008, 0.0)
    monkeypatch.setattr(probe, "_ffprobe", lambda _: (stream, tags, jittered))
    assert run_stages([STAGE], ctx, log=lambda _: None) == 0
    np.testing.assert_allclose(np.load(ctx.out / "frame_times.npy"), jittered - jittered[0])
