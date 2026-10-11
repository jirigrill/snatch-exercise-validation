import json
from pathlib import Path

import pytest

from snatch import athlete_store
from snatch.stage import Context, run_stages
from snatch.stages import athlete


def test_athlete_round_trip(tmp_path: Path) -> None:
    assert not athlete_store.exists(tmp_path, "jiri", athlete_store.ATHLETE)
    athlete_store.save(tmp_path, "jiri", athlete_store.ATHLETE, {"height_m": 1.8})
    assert athlete_store.exists(tmp_path, "jiri", athlete_store.ATHLETE)
    assert athlete_store.load(tmp_path, "jiri", athlete_store.ATHLETE) == {"height_m": 1.8}
    assert athlete_store.load(tmp_path, "nobody", athlete_store.SKELETON) is None


@pytest.mark.parametrize("h", [1.39, 2.21, 180.0])
def test_height_out_of_range_is_rejected(h: float) -> None:
    with pytest.raises(ValueError, match="1.40"):
        athlete.check_height(h)


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
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    code, status, _ = _run(ctx)
    assert code == 0 and status["stages"]["S0"]["state"] == "done"
    prof = _profile(ctx)
    assert prof["athlete"] == "jiri" and prof["height_m"] == 1.80
    assert prof["knee_height_m"] == pytest.approx(0.285 * 1.80)


def test_later_height_overwrites(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    _run(ctx)
    _run(_ctx(tmp_path, height=1.75))
    assert _profile(ctx)["height_m"] == 1.75


def test_stored_height_is_enough(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    _run(ctx)
    assert _run(_ctx(tmp_path))[0] == 0


def test_no_height_exits_7(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _skeleton(ctx)
    code, status, lines = _run(ctx)
    assert (code, status["status"]) == (7, "needs_height")
    assert any("--height" in s for s in lines)


def test_no_skeleton_exits_2_with_calibrate_command(tmp_path: Path) -> None:
    code, status, lines = _run(_ctx(tmp_path, height=1.80))
    assert (code, status["status"]) == (2, "needs_calibration")
    assert any("--calibrate <bar.MOV> --athlete jiri" in s for s in lines)


def test_both_missing_is_one_message_exit_2(tmp_path: Path) -> None:
    code, status, lines = _run(_ctx(tmp_path))
    assert code == 2
    stops = [s for s in lines if "stopped" in s]
    assert len(stops) == 1 and "--height" in stops[0] and "--calibrate" in stops[0]
    assert status["status"] == "needs_calibration"


def test_calibrate_skips_the_skeleton_check(tmp_path: Path) -> None:
    assert _run(_ctx(tmp_path, height=1.80, calibrate=True))[0] == 0


def test_bad_height_exits_7(tmp_path: Path) -> None:
    code, _, lines = _run(_ctx(tmp_path, height=180.0))
    assert code == 7 and any("cm" in s for s in lines)


def test_s0_always_runs(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, height=1.80)
    _skeleton(ctx)
    _run(ctx)
    assert _run(ctx)[2] == ["S0 done"]


@pytest.mark.parametrize("bad", ["../x", "", "a/b", "/abs"])
def test_bad_athlete_id_is_rejected(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        athlete_store.path(tmp_path, bad, athlete_store.ATHLETE)


@pytest.mark.parametrize("content", ["", "{}", '{"height_m": 9}'])
def test_unusable_profile_counts_as_no_height(tmp_path: Path, content: str) -> None:
    ctx = _ctx(tmp_path)
    _skeleton(ctx)
    (ctx.athletes / "jiri" / "athlete.json").write_text(content)
    assert _run(ctx)[0] == 7


def test_from_a_later_stage_still_runs_s0(tmp_path: Path) -> None:
    from snatch.stage import Stage
    later = Stage("S9", (), (), lambda c, t: None)
    lines: list[str] = []
    assert run_stages([athlete.STAGE, later], _ctx(tmp_path), start="S9", log=lines.append) == 2
    assert "S9 done" not in lines
