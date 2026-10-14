"""The stage contract and the runner that skips a stage whose hash is unchanged.

A stage hashes the bytes of its input files, its params and its version into
`<stage>.meta.json`. It writes its outputs into a temp directory, and only a
stage that returns has them renamed into place, so a crash never leaves a
file that looks done. A stage that raises StageStop (a stop with an exit code)
still has its outputs moved into place, so the overlay of the failed check can
be looked at, but gets no meta: it reruns next time. Any other exception
discards everything. `pipeline_status.json` holds each stage's state in
pipeline order: done, skipped (hash unchanged) or failed; a stage that --only
or --from did not pick is up_to_date or stale. An `always` stage (a check, no
outputs) runs every time and keeps no meta.
`SKELETON` names the athlete's skeleton.json: as an input, a stage that lists
it reruns when the calibration changes; as an output (C3), it is written to
the athlete profile, not out/<clip>.
"""

import hashlib
import json
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from snatch import athlete_store

CLIP = "<clip>"
SKELETON = "<skeleton>"
STATUS_FILE = "pipeline_status.json"
MISSING_INPUT_EXIT = 9


@dataclass(frozen=True)
class Context:
    clip: Path
    out: Path
    params: Mapping[str, Any] = field(default_factory=dict)
    athletes: Path = Path("athletes")

    def path(self, name: str) -> Path:
        if name == CLIP:
            return self.clip
        if name == SKELETON:
            return athlete_store.path(self.athletes, str(self.params["athlete"]), athlete_store.SKELETON)
        return self.out / name


@dataclass(frozen=True)
class Stage:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    run: Callable[[Context, Path], None]
    params: tuple[str, ...] = ()
    version: int = 1
    always: bool = False


class StageStop(Exception):
    def __init__(self, code: int, status: str, reason: str):
        super().__init__(reason)
        self.code = code
        self.status = status
        self.reason = reason


def stage_hash(stage: Stage, ctx: Context) -> str:
    h = hashlib.sha256()
    h.update(f"{stage.name}\0{stage.version}\0".encode())
    h.update(json.dumps({k: ctx.params.get(k) for k in stage.params}, sort_keys=True).encode())
    for name in stage.inputs:
        h.update(f"\0{name}\0".encode())
        with ctx.path(name).open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def _is_fresh(stage: Stage, ctx: Context, digest: str) -> bool:
    meta = ctx.out / f"{stage.name}.meta.json"
    if not meta.exists() or any(not ctx.path(o).exists() for o in stage.outputs):
        return False
    return json.loads(meta.read_text()).get("hash") == digest


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def _write_status(out: Path, status: dict) -> None:
    _write_json(out / STATUS_FILE, status)


def _missing_input(stage: Stage, ctx: Context, producers: Mapping[str, str]) -> str | None:
    for name in stage.inputs:
        path = ctx.path(name)
        if not path.exists():
            by = producers.get(name)
            return f"{stage.name} needs {path}, run {by} first" if by else f"{stage.name} needs {path}"
    return None


def _run_one(stage: Stage, ctx: Context, digest: str) -> None:
    tmp = ctx.out / f".tmp-{stage.name}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    def move_outputs(only_existing: bool) -> None:
        for name in stage.outputs:
            if only_existing and not (tmp / name).exists():
                continue
            dest = ctx.path(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            (tmp / name).replace(dest)

    try:
        try:
            stage.run(ctx, tmp)
        except StageStop:
            (ctx.out / f"{stage.name}.meta.json").unlink(missing_ok=True)
            move_outputs(only_existing=True)
            raise
        move_outputs(only_existing=False)
        _write_json(ctx.out / f"{stage.name}.meta.json", {"hash": digest, "version": stage.version})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _stopped(stage: Stage, stop: StageStop, out: Path, status: dict, log: Callable[[str], None]) -> int:
    log(f"{stage.name} stopped: {stop.reason}")
    status["stages"][stage.name] = {"state": "failed", "reason": stop.reason}
    status.update(status=stop.status, reason=stop.reason)
    _write_status(out, status)
    return stop.code


def run_stages(
    stages: Sequence[Stage],
    ctx: Context,
    *,
    only: str | None = None,
    start: str | None = None,
    force: bool = False,
    log: Callable[[str], None] = print,
) -> int:
    """Run the stages in order. Returns 0, or the exit code of the stop."""
    names = [s.name for s in stages]
    for pick in (only, start):
        if pick is not None and pick not in names:
            raise ValueError(f"unknown stage {pick}, expected one of {names}")
    pick = only or start
    first = names.index(pick) if pick else 0
    chosen = stages[first:first + 1] if only else stages[first:]
    # checks (always stages) before the pick still gate it: --from S5a must not skip S0
    chosen = [s for s in stages[:first] if s.always] + list(chosen)
    producers = {o: s.name for s in stages for o in s.outputs}

    ctx.out.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {"status": "running", "stages": {}}
    for stage in chosen:
        if stage.always:
            if stage.outputs:
                raise ValueError(f"{stage.name}: an always stage writes no outputs")
            try:
                stage.run(ctx, ctx.out)
            except StageStop as stop:
                return _stopped(stage, stop, ctx.out, status, log)
            log(f"{stage.name} done")
            status["stages"][stage.name] = {"state": "done"}
            _write_status(ctx.out, status)
            continue
        missing = _missing_input(stage, ctx, producers)
        if missing:
            log(missing)
            status["stages"][stage.name] = {"state": "failed", "reason": missing}
            status.update(status="missing_input", reason=missing)
            _write_status(ctx.out, status)
            return MISSING_INPUT_EXIT
        digest = stage_hash(stage, ctx)
        fresh = _is_fresh(stage, ctx, digest)
        if fresh and not (force or only or start):
            log(f"{stage.name} skipped (up to date)")
            status["stages"][stage.name] = {"state": "skipped"}
            continue
        if not fresh and (ctx.out / f"{stage.name}.meta.json").exists():
            log(f"{stage.name} stale, rerunning")
        try:
            _run_one(stage, ctx, digest)
        except StageStop as stop:
            return _stopped(stage, stop, ctx.out, status, log)
        except Exception as e:
            status["stages"][stage.name] = {"state": "failed", "reason": repr(e)}
            status.update(status="error", reason=repr(e))
            _write_status(ctx.out, status)
            raise
        log(f"{stage.name} done")
        status["stages"][stage.name] = {"state": "done"}
        _write_status(ctx.out, status)
    for stage in stages:
        if stage not in chosen and not stage.always:
            fresh = all(ctx.path(i).exists() for i in stage.inputs) and _is_fresh(
                stage, ctx, stage_hash(stage, ctx))
            status["stages"][stage.name] = {"state": "up_to_date" if fresh else "stale"}
    status["stages"] = {s.name: status["stages"][s.name] for s in stages if s.name in status["stages"]}
    status["status"] = "ok"
    _write_status(ctx.out, status)
    return 0
