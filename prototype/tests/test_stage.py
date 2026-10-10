import json
from pathlib import Path

import pytest

from snatch.stage import CLIP, Context, Stage, StageStop, run_stages


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
    assert code != 0
    assert calls == []
    assert "A.txt" in lines[-1] and "run A" in lines[-1]


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
