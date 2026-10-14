import json
from pathlib import Path

import pytest

from snatch import athlete_store
from snatch.stage import Context, run_stages
from snatch.stages import athlete, side


def _ctx(tmp_path: Path, **params) -> Context:
    clip = tmp_path / "clip.MOV"
    clip.write_bytes(b"v")
    return Context(clip, tmp_path / "out", {"athlete": "jiri", **params}, athletes=tmp_path / "athletes")


def _run(ctx: Context) -> tuple[int, dict, list[str]]:
    lines: list[str] = []
    code = run_stages([athlete.STAGE], ctx, log=lines.append)
    return code, json.loads((ctx.out / "pipeline_status.json").read_text()), lines


def _skeleton(ctx: Context) -> None:
    athlete_store.save(ctx.athletes, "jiri", athlete_store.SKELETON, {"left": {}})


def _profile(ctx: Context) -> dict:
    prof = athlete_store.load(ctx.athletes, "jiri", athlete_store.ATHLETE)
    assert prof is not None
    return prof


def test_height_writes_profile_and_continues(tmp_path: Path) -> None:
    """R3: --height on a new athlete writes athlete.json and the run goes on (run_clip always passes it)."""
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    code, status, _ = _run(ctx)
    assert code == 0 and status["stages"]["S0"]["state"] == "done"
    prof = _profile(ctx)
    assert prof["athlete"] == "jiri" and prof["height_m"] == 1.80
    assert prof["knee_height_m"] == pytest.approx(0.285 * 1.80)


def test_later_height_overwrites(tmp_path: Path) -> None:
    """R3: a later --height replaces the stored one (spec: no --update-height)."""
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    _run(ctx)
    _run(_ctx(tmp_path, height=1.75))
    assert _profile(ctx)["height_m"] == 1.75


def test_stored_height_is_enough(tmp_path: Path) -> None:
    """R3: without --height the stored height is used (run_clip always passes it)."""
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    _run(ctx)
    assert _run(_ctx(tmp_path))[0] == 0


def test_no_height_exits_7(tmp_path: Path) -> None:
    """R1: no height for the athlete: exit 7, asks for --height."""
    ctx = _ctx(tmp_path)
    _skeleton(ctx)
    code, status, lines = _run(ctx)
    assert (code, status["status"]) == (7, "needs_height")
    assert any("--height" in s for s in lines)


def test_no_skeleton_exits_2_with_calibrate_command(tmp_path: Path) -> None:
    """R1: no skeleton: exit 2 with the --calibrate command to run."""
    code, status, lines = _run(_ctx(tmp_path, height=1.80))
    assert (code, status["status"]) == (2, "needs_calibration")
    assert any("--calibrate <bar.MOV> --athlete jiri" in s for s in lines)


def test_both_missing_is_one_message_exit_2(tmp_path: Path) -> None:
    """R1: height and skeleton both missing: one message, exit 2."""
    code, status, lines = _run(_ctx(tmp_path))
    assert code == 2
    stops = [s for s in lines if "stopped" in s]
    assert len(stops) == 1 and "--height" in stops[0] and "--calibrate" in stops[0]
    assert status["status"] == "needs_calibration"


def test_calibrate_without_height_exits_7(tmp_path: Path) -> None:
    """R1: --calibrate still needs a height: exit 7."""
    code, status, lines = _run(_ctx(tmp_path, calibrate=True))
    assert (code, status["status"]) == (7, "needs_height")
    assert any("--height" in s for s in lines)


@pytest.mark.parametrize("h", [1.39, 2.21, 180.0])
def test_bad_height_exits_7(tmp_path: Path, h: float) -> None:
    """R1: a height outside 1.40-2.20 m (e.g. given in cm) stops with exit 7."""
    code, _, lines = _run(_ctx(tmp_path, height=h))
    assert code == 7 and any("1.40" in s or "cm" in s for s in lines)



def test_s0_always_runs(tmp_path: Path) -> None:
    """R2: S0 runs on every run, also before a later --from stage, and its stop gates that stage."""
    from snatch.stage import Stage
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    _run(ctx)
    assert _run(ctx)[2] == ["S0 done"]
    later = Stage("S99", (), (), lambda c, t: None)
    (tmp_path / "other").mkdir()
    lines: list[str] = []
    assert run_stages([athlete.STAGE, later], _ctx(tmp_path / "other"), start="S99", log=lines.append) == 2
    assert "S99 done" not in lines



@pytest.mark.parametrize("bad", ["../x", "", "a/b", "/abs"])
def test_bad_athlete_id_is_rejected(tmp_path: Path, bad: str) -> None:
    """R3: an athlete id that is not a safe folder name is rejected."""
    with pytest.raises(ValueError):
        athlete_store.path(tmp_path, bad, athlete_store.ATHLETE)


@pytest.mark.parametrize("content", ["", "{}", '{"height_m": 9}'])
def test_unusable_profile_counts_as_no_height(tmp_path: Path, content: str) -> None:
    """R3: a broken athlete.json counts as no height (exit 7), not a crash."""
    ctx = _ctx(tmp_path)
    _skeleton(ctx)
    (ctx.athletes / "jiri" / "athlete.json").write_text(content)
    assert _run(ctx)[0] == 7


@pytest.mark.parametrize("facing, code", [("right", 0), ("left", 2)])
def test_side_check_needs_the_clips_near_side(tmp_path: Path, facing: str, code: int) -> None:
    """R1: a skeleton for the other side only: exit 2 at side."""
    ctx = _ctx(tmp_path)
    athlete_store.save(ctx.athletes, "jiri", athlete_store.SKELETON, {"r": {}})
    ctx.out.mkdir()
    (ctx.out / "facing.json").write_text(json.dumps({"facing": facing}))
    lines: list[str] = []
    assert run_stages([side.STAGE], ctx, log=lines.append) == code
    if code:
        assert any("No l skeleton" in s and "--calibrate" in s for s in lines)
