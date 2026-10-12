import json
from pathlib import Path

import pytest

from snatch.stage import CLIP, MISSING_INPUT_EXIT, SKELETON, Context, Stage, StageStop, run_stages


def _writer(name: str, calls: list[str]):
    def run(ctx: Context, tmp: Path) -> None:
        calls.append(name)
        (tmp / f"{name}.txt").write_text(f"{name} {ctx.params.get('k')}")
    return run


def _pipeline(calls: list[str]) -> list[Stage]:
    return [
        Stage("A", (CLIP,), ("A.txt",), _writer("A", calls), params=("k",)),
        Stage("B", ("A.txt",), ("B.txt",), _writer("B", calls)),
    ]


@pytest.fixture
def ctx(tmp_path: Path) -> Context:
    clip = tmp_path / "clip.MOV"
    clip.write_bytes(b"video")
    return Context(clip, tmp_path / "out", {"k": 1})


def _quiet(_: str) -> None:
    pass


def test_identical_hash_skips(ctx: Context) -> None:
    calls: list[str] = []
    assert run_stages(_pipeline(calls), ctx, log=_quiet) == 0
    assert run_stages(_pipeline(calls), ctx, log=_quiet) == 0
    assert calls == ["A", "B"]
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert status["stages"]["A"]["state"] == "skipped"


def test_changed_param_reruns(ctx: Context) -> None:
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), Context(ctx.clip, ctx.out, {"k": 2}), log=_quiet)
    assert calls == ["A", "B", "A", "B"]


def test_identical_rerun_output_leaves_downstream_skipped(ctx: Context) -> None:
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, only="A", log=_quiet)
    run_stages(_pipeline(calls), ctx, log=_quiet)
    assert calls == ["A", "B", "A"]


def test_force_reruns_everything(ctx: Context) -> None:
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, force=True, log=_quiet)
    assert calls == ["A", "B", "A", "B"]


def test_only_and_from(ctx: Context) -> None:
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, only="B", log=_quiet)
    run_stages(_pipeline(calls), ctx, start="A", log=_quiet)
    assert calls == ["A", "B", "B", "A", "B"]


def test_missing_input_names_producer_and_never_runs_it(ctx: Context) -> None:
    calls: list[str] = []
    lines: list[str] = []
    code = run_stages(_pipeline(calls), ctx, only="B", log=lines.append)
    assert code == MISSING_INPUT_EXIT not in (0, 1)
    assert calls == []
    assert str(ctx.out / "A.txt") in lines[-1] and "run A" in lines[-1]
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert status["status"] == "missing_input"
    assert status["stages"]["B"] == {"state": "failed", "reason": lines[-1]}


def test_deleted_output_is_stale_and_rebuilt(ctx: Context) -> None:
    calls: list[str] = []
    lines: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    (ctx.out / "A.txt").unlink()
    run_stages(_pipeline(calls), ctx, log=lines.append)
    assert "A stale, rerunning" in lines
    assert (ctx.out / "A.txt").exists()


def test_exception_leaves_no_output_under_final_name(ctx: Context) -> None:
    def crash(_: Context, tmp: Path) -> None:
        (tmp / "A.txt").write_text("half")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_stages([Stage("A", (CLIP,), ("A.txt",), crash)], ctx, log=_quiet)
    assert not (ctx.out / "A.txt").exists()
    assert not (ctx.out / "A.meta.json").exists()
    assert json.loads((ctx.out / "pipeline_status.json").read_text())["status"] == "error"


def test_stop_writes_status_and_returns_code(ctx: Context) -> None:
    def stop(_: Context, __: Path) -> None:
        raise StageStop(3, "bad_clip", "too short")

    assert run_stages([Stage("A", (CLIP,), ("A.txt",), stop)], ctx, log=_quiet) == 3
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert (status["status"], status["reason"]) == ("bad_clip", "too short")


def test_version_bump_reruns(ctx: Context) -> None:
    calls: list[str] = []
    run_stages([Stage("A", (CLIP,), ("A.txt",), _writer("A", calls))], ctx, log=_quiet)
    run_stages([Stage("A", (CLIP,), ("A.txt",), _writer("A", calls), version=2)], ctx, log=_quiet)
    assert calls == ["A", "A"]


def test_unchosen_stage_with_changed_hash_is_recorded_stale(ctx: Context) -> None:
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), Context(ctx.clip, ctx.out, {"k": 2}), only="B", log=_quiet)
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert status["stages"]["A"] == {"state": "stale"}


def _nested(calls: list[str], stop: bool = False):
    def run(_: Context, tmp: Path) -> None:
        calls.append("A")
        (tmp / "overlays").mkdir()
        (tmp / "overlays" / "sheet.jpg").write_bytes(b"jpg")
        if stop:
            raise StageStop(3, "bad_clip", "too short")
        (tmp / "A.txt").write_text("a")
    return [Stage("A", (CLIP,), ("A.txt", "overlays/sheet.jpg"), run)]


def test_stop_leaves_no_nested_output(ctx: Context) -> None:
    assert run_stages(_nested([], stop=True), ctx, log=_quiet) == 3
    assert not (ctx.out / "overlays" / "sheet.jpg").exists()


def test_deleted_nested_output_is_stale(ctx: Context) -> None:
    calls: list[str] = []
    lines: list[str] = []
    run_stages(_nested(calls), ctx, log=_quiet)
    (ctx.out / "overlays" / "sheet.jpg").unlink()
    run_stages(_nested(calls), ctx, log=lines.append)
    assert "A stale, rerunning" in lines
    assert calls == ["A", "A"] and (ctx.out / "overlays" / "sheet.jpg").exists()


def test_skeleton_input_resolves_to_the_athlete_dir_and_is_hashed(tmp_path: Path) -> None:
    clip = tmp_path / "clip.MOV"
    clip.write_bytes(b"v")
    ctx = Context(clip, tmp_path / "out", {"athlete": "jiri"}, athletes=tmp_path / "ath")
    assert ctx.path(SKELETON) == tmp_path / "ath" / "jiri" / "skeleton.json"
    calls: list[str] = []
    stages = [Stage("S4b", (CLIP, SKELETON), ("S4b.txt",), _writer("S4b", calls))]
    ctx.path(SKELETON).parent.mkdir(parents=True)
    ctx.path(SKELETON).write_text("1")
    run_stages(stages, ctx, log=_quiet)
    run_stages(stages, ctx, log=_quiet)
    ctx.path(SKELETON).write_text("2")
    run_stages(stages, ctx, log=_quiet)
    assert calls == ["S4b", "S4b"]


def test_always_stage_runs_every_time_without_meta(ctx: Context) -> None:
    calls: list[str] = []
    stages = [Stage("S0", (), (), lambda c, t: calls.append("S0"), always=True)]
    run_stages(stages, ctx, log=_quiet)
    run_stages(stages, ctx, log=_quiet)
    assert calls == ["S0", "S0"]
    assert not (ctx.out / "S0.meta.json").exists()
