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
    """R2: same inputs, params and version: the stage is skipped."""
    calls: list[str] = []
    assert run_stages(_pipeline(calls), ctx, log=_quiet) == 0
    assert run_stages(_pipeline(calls), ctx, log=_quiet) == 0
    assert calls == ["A", "B"]
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert status["stages"]["A"]["state"] == "skipped"


def test_changed_param_reruns(ctx: Context) -> None:
    """R2: a changed param changes the hash: the stage reruns."""
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), Context(ctx.clip, ctx.out, {"k": 2}), log=_quiet)
    assert calls == ["A", "B", "A", "B"]


def test_identical_rerun_output_leaves_downstream_skipped(ctx: Context) -> None:
    """R2: a rerun with byte-identical output does not rerun downstream."""
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, only="A", log=_quiet)
    run_stages(_pipeline(calls), ctx, log=_quiet)
    assert calls == ["A", "B", "A"]


def test_force_reruns_everything(ctx: Context) -> None:
    """R2: --force ignores the hashes."""
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, force=True, log=_quiet)
    assert calls == ["A", "B", "A", "B"]


def test_only_and_from(ctx: Context) -> None:
    """R2: --only runs one stage, --from that stage and every later one."""
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, only="B", log=_quiet)
    run_stages(_pipeline(calls), ctx, start="A", log=_quiet)
    assert calls == ["A", "B", "B", "A", "B"]


def test_missing_input_names_producer_and_never_runs_it(ctx: Context) -> None:
    """R1: a missing input stops (exit 9) naming the stage that makes it; producers never run for you."""
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
    """R2: a deleted output (top level or nested) makes its stage stale; the rerun rebuilds it."""
    calls: list[str] = []
    lines: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    (ctx.out / "A.txt").unlink()
    run_stages(_pipeline(calls), ctx, log=lines.append)
    assert "A stale, rerunning" in lines
    assert (ctx.out / "A.txt").exists()

    nested: list[str] = []
    lines = []
    run_stages(_nested(nested), ctx, log=_quiet)
    (ctx.out / "overlays" / "sheet.jpg").unlink()
    run_stages(_nested(nested), ctx, log=lines.append)
    assert "A stale, rerunning" in lines
    assert nested == ["A", "A"] and (ctx.out / "overlays" / "sheet.jpg").exists()



def test_exception_leaves_no_output_under_final_name(ctx: Context) -> None:
    """R2: a crash mid-stage leaves no file that looks done (temp dir + rename)."""
    def crash(_: Context, tmp: Path) -> None:
        (tmp / "A.txt").write_text("half")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_stages([Stage("A", (CLIP,), ("A.txt",), crash)], ctx, log=_quiet)
    assert not (ctx.out / "A.txt").exists()
    assert not (ctx.out / "A.meta.json").exists()
    assert json.loads((ctx.out / "pipeline_status.json").read_text())["status"] == "error"


def test_stop_writes_status_and_returns_code(ctx: Context) -> None:
    """R1: a stop returns its exit code and records status + reason (nested too); no meta, so it reruns."""
    def stop(_: Context, __: Path) -> None:
        raise StageStop(3, "bad_clip", "too short")

    assert run_stages([Stage("A", (CLIP,), ("A.txt",), stop)], ctx, log=_quiet) == 3
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert (status["status"], status["reason"]) == ("bad_clip", "too short")
    assert run_stages(_nested([], stop=True), ctx, log=_quiet) == 3
    assert not (ctx.out / "A.meta.json").exists() and not (ctx.out / "A.txt").exists()  # nothing was written


def test_version_bump_reruns(ctx: Context) -> None:
    """R2: a STAGE_VERSION bump reruns the stage."""
    calls: list[str] = []
    run_stages([Stage("A", (CLIP,), ("A.txt",), _writer("A", calls))], ctx, log=_quiet)
    run_stages([Stage("A", (CLIP,), ("A.txt",), _writer("A", calls), version=2)], ctx, log=_quiet)
    assert calls == ["A", "A"]


def test_unchosen_stage_with_changed_hash_is_recorded_stale(ctx: Context) -> None:
    """R2: with --only, a stage not run but out of date is reported stale."""
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), Context(ctx.clip, ctx.out, {"k": 2}), only="B", log=_quiet)
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert status["stages"]["A"] == {"state": "stale"}


def test_unchosen_fresh_stage_is_up_to_date_and_listed_in_order(ctx: Context) -> None:
    """R2: with --only, untouched stages are reported up_to_date, in pipeline order."""
    calls: list[str] = []
    run_stages(_pipeline(calls), ctx, log=_quiet)
    run_stages(_pipeline(calls), ctx, only="B", log=_quiet)
    status = json.loads((ctx.out / "pipeline_status.json").read_text())
    assert status["stages"] == {"A": {"state": "up_to_date"}, "B": {"state": "done"}}
    assert list(status["stages"]) == ["A", "B"]


def _nested(calls: list[str], stop: bool = False):
    def run(_: Context, tmp: Path) -> None:
        calls.append("A")
        (tmp / "overlays").mkdir()
        (tmp / "overlays" / "sheet.jpg").write_bytes(b"jpg")
        if stop:
            raise StageStop(3, "bad_clip", "too short")
        (tmp / "A.txt").write_text("a")
    return [Stage("A", (CLIP,), ("A.txt", "overlays/sheet.jpg"), run)]


def test_skeleton_input_resolves_to_the_athlete_dir_and_is_hashed(tmp_path: Path) -> None:
    """R2: skeleton.json is read from athletes/<id>/ and is part of the hash."""
    clip = tmp_path / "clip.MOV"
    clip.write_bytes(b"v")
    ctx = Context(clip, tmp_path / "out", {"athlete": "jiri"}, athletes=tmp_path / "ath")
    assert ctx.path(SKELETON) == tmp_path / "ath" / "jiri" / "skeleton.json"
    calls: list[str] = []
    stages = [Stage("S6", (CLIP, SKELETON), ("S6.txt",), _writer("S6", calls))]
    ctx.path(SKELETON).parent.mkdir(parents=True)
    ctx.path(SKELETON).write_text("1")
    run_stages(stages, ctx, log=_quiet)
    run_stages(stages, ctx, log=_quiet)
    ctx.path(SKELETON).write_text("2")
    run_stages(stages, ctx, log=_quiet)
    assert calls == ["S6", "S6"]


def test_always_stage_runs_every_time_without_meta(ctx: Context) -> None:
    """R2: an always stage (S0, side) runs every time and keeps no meta."""
    calls: list[str] = []
    stages = [Stage("S0", (), (), lambda c, t: calls.append("S0"), always=True)]
    run_stages(stages, ctx, log=_quiet)
    run_stages(stages, ctx, log=_quiet)
    assert calls == ["S0", "S0"]
    assert not (ctx.out / "S0.meta.json").exists()


def test_skeleton_output_goes_to_the_athlete_dir(tmp_path: Path) -> None:
    """R2: C3's skeleton.json output lands in athletes/<id>/, not out/<clip>/."""
    clip = tmp_path / "clip.MOV"
    clip.write_bytes(b"v")
    ctx = Context(clip, tmp_path / "out", {"athlete": "jiri"}, athletes=tmp_path / "ath")
    calls: list[str] = []

    def fit(c: Context, tmp: Path) -> None:
        calls.append("C3")
        (tmp / SKELETON).write_text("{}")
    stages = [Stage("C3", (CLIP,), (SKELETON,), fit)]
    run_stages(stages, ctx, log=_quiet)
    run_stages(stages, ctx, log=_quiet)
    assert calls == ["C3"] and ctx.path(SKELETON).exists() and not (ctx.out / SKELETON).exists()


def test_stop_keeps_the_outputs_but_writes_no_meta(ctx: Context) -> None:
    """R2: a StageStop moves the written outputs into place and drops the meta of an earlier run, so the stage reruns."""
    calls: list[str] = []

    def stop(c: Context, tmp: Path) -> None:
        calls.append("S2")
        (tmp / "S2.txt").write_text("check image")  # S2b.txt is never written
        raise StageStop(6, "bar_only", "no plate")
    ctx.out.mkdir()
    (ctx.out / "S2.meta.json").write_text('{"hash": "from an earlier run that passed"}')
    stages = [Stage("S2", (CLIP,), ("S2.txt", "S2b.txt"), stop)]
    assert run_stages(stages, ctx, force=True, log=_quiet) == 6
    assert (ctx.out / "S2.txt").read_text() == "check image"
    assert not (ctx.out / "S2b.txt").exists() and not (ctx.out / "S2.meta.json").exists()
    assert run_stages(stages, ctx, log=_quiet) == 6
    assert calls == ["S2", "S2"]
