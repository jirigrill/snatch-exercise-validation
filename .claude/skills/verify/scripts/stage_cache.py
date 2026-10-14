"""Reuse a stage's outputs on T1 when an exact key says a fresh run would give the same.

usage: uv run python stage_cache.py restore|store <out dir> <athletes> <clip> <cache dir>   (from prototype/)

The key of a hashed stage covers what a fresh run depends on: its name, version and
params, the content of its input files (npz: every array but VOLATILE), its code and
every snatch module it imports (stage_files.code_files), scripts/pipeline.py, uv.lock,
the model files and the macOS version. Fresh runs give the same arrays (bfc6f98 vs
5031e5d: only `seconds` differed), so a hit is what a fresh run would write.

restore: before the first run, in pipeline order, copy each hit into <out dir> and write
its <stage>.meta.json, so pipeline.py reports it skipped; stop at the first miss (every
later stage then runs). Prints the reused stage names, comma-separated.
store: after a passing run, keep each stage's outputs under its key. When an entry with
that key exists and the stage ran fresh (VERIFY_NO_CACHE=1, milestones), its content must
equal the fresh outputs; a difference is a FAIL: the key misses something.
"""

import hashlib
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path

import numpy as np

from snatch.stage import CLIP, SKELETON, Context, Stage, stage_hash
from snatch.stages import STAGES

from stage_files import code_files  # pyright: ignore[reportMissingImports]  (run as a script: its dir is on sys.path)

VOLATILE = {"seconds"}  # npz fields that differ run to run (the stage's run time)
MODELS = Path.home() / ".cache" / "rtmlib" / "hub" / "checkpoints"


def content(path: Path) -> bytes:
    """What a file holds, minus run-to-run noise: npz arrays but VOLATILE, else the bytes."""
    if path.suffix != ".npz":
        return path.read_bytes()
    with np.load(path, allow_pickle=False) as z:
        return b"".join(k.encode() + z[k].tobytes() + str(z[k].dtype).encode() + str(z[k].shape).encode()
                        for k in sorted(set(z.files) - VOLATILE))


def env_key() -> str:
    h = hashlib.sha256()
    for f in [*sorted(MODELS.glob("*.onnx")), Path("scripts/pipeline.py"), Path("uv.lock")]:
        h.update(f"{f.name}\0{f.stat().st_size}\0".encode() + (f.read_bytes() if f.suffix != ".onnx" else b""))
    h.update(platform.mac_ver()[0].encode())
    return h.hexdigest()


def key(stage: Stage, ctx: Context, env: str) -> str | None:
    """None when an input is missing (an upstream stage did not run or was not restored)."""
    h = hashlib.sha256(f"{stage.name}\0{stage.version}\0{env}\0".encode())
    h.update(json.dumps({k: ctx.params.get(k) for k in stage.params}, sort_keys=True).encode())
    for f in code_files([stage]):
        h.update(f.read_bytes())
    for name in stage.inputs:
        p = ctx.path(name)
        if not p.is_file():
            return None
        st = p.stat()
        h.update(f"\0{name}\0".encode() + (f"{st.st_size} {st.st_mtime_ns}".encode() if name == CLIP else content(p)))
    return h.hexdigest()[:16]


def outputs(stage: Stage) -> list[str]:
    return [o for o in stage.outputs if o != SKELETON]


def main(mode: str, out: Path, athletes: Path, clip: Path, cache: Path) -> int:
    spec = importlib.util.spec_from_file_location("pipeline", "scripts/pipeline.py")
    assert spec and spec.loader
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    ctx, _ = pipeline.parse([str(clip), "--athlete", "verify", "--height", "1.73", "--out", str(out),
                             "--athletes", str(athletes)])
    env = env_key()
    reused = []
    status = json.loads((out / "pipeline_status.json").read_text())["stages"] if mode == "store" else {}
    for stage in (s for s in STAGES if not s.always):
        k = key(stage, ctx, env)
        entry = cache / stage.name / str(k)
        if mode == "restore":
            if k is None or not (entry / ".done").exists():
                break
            for o in outputs(stage):
                (out / o).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry / o, out / o)
            (out / f"{stage.name}.meta.json").write_text(json.dumps({"hash": stage_hash(stage, ctx), "version": stage.version}))
            reused.append(stage.name)
            continue
        if k is None:
            print(f"FAIL: stage cache: {stage.name} has a missing input after a passing run")
            return 1
        if (entry / ".done").exists():
            if status.get(stage.name, {}).get("state") == "done":
                bad = [o for o in outputs(stage) if content(entry / o) != content(out / o)]
                if bad:
                    print(f"FAIL: stage cache: fresh {stage.name} differs from the cached one with the same key "
                          f"({', '.join(bad)}): the key misses something (stage_cache.py)")
                    return 1
            continue
        tmp = entry.with_name(entry.name + ".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        for o in outputs(stage):
            (tmp / o).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out / o, tmp / o)
        (tmp / ".done").touch()
        shutil.rmtree(entry, ignore_errors=True)
        tmp.rename(entry)
    if mode == "restore":
        print(",".join(reused))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(a[0], Path(a[1]), Path(a[2]), Path(a[3]), Path(a[4])))
