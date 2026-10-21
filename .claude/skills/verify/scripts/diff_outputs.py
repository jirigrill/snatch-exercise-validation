"""Compare a run's stage outputs with main's (base_run.sh) and say which stages the PR changed.

usage: uv run python diff_outputs.py <evidence_root>   (from prototype/)

For every clip dir in <root>/ that also has one in <root>/base/ (the analyze clips, and
calibrate_<T5>/), and every stage of snatch.stages.STAGES (CALIBRATE for calibrate_*), compares each
output file (Stage.outputs; an mp4 also its _sheet.jpg, _worst.jpg and .worst; the athlete store's
SKELETON as athletes/*/skeleton.json): npz arrays but stage_cache.VOLATILE and NaN-equal, json by
top-level key (fields in JSON_VOLATILE ignored), jpg/png by decoded pixels (the JPEG bytes of
an identical image can differ), anything else by bytes. State per stage and clip:
  new        no base file (the stage does not exist on main)
  changed    a file differs, was added or removed (files: name -> what)
  identical  every output equal
  absent     no output on either side (the stage did not run: an expected stop)
  no outputs the stage has none (S0, side)
A clip with no passing base run (no base/<clip>.log with `OK evidence:`) is not compared (`_no_base`).
Writes <root>/changes.json {stage: {clip id: {state, files}}, "_no_base": [clip ids]} (clip id = the
T-number, `calibrate_T5` for the calibration) and prints a table. A stage counts as changed for the PR
when it is new or changed on any clip.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from snatch.stage import SKELETON, Stage
from snatch.stages import CALIBRATE, STAGES

from stage_cache import VOLATILE  # pyright: ignore[reportMissingImports]  (run as a script: its dir is on sys.path)

JSON_VOLATILE = {"fitted", "updated"}  # timestamps inside json outputs (skeleton.json, athlete.json)


def clip_id(d: str) -> str:
    return "calibrate_" + d.split("_")[1] if d.startswith("calibrate_") else d.split("_")[0]


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in JSON_VOLATILE}
    return [strip(v) for v in o] if isinstance(o, list) else o


def same(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and a.dtype == b.dtype and bool(np.array_equal(a, b, equal_nan=a.dtype.kind in "fc"))


def delta(a: np.ndarray, b: np.ndarray) -> str:
    if a.shape != b.shape or a.dtype.kind not in "fiub" or b.dtype.kind not in "fiub":
        return " (shape/type)"
    x, y = a.astype(float), b.astype(float)
    if (np.isnan(x) != np.isnan(y)).any():
        return " (nan pattern)"
    return f" (max diff {np.fmax.reduce(np.abs(x - y).ravel(), initial=0.0):.3g})"


def keys(names: dict[str, str]) -> str:
    return " ".join([f"+{k}" for k, v in names.items() if v == "+"] + [f"-{k}" for k, v in names.items() if v == "-"]
                    + [f"~{k}{v[1:]}" for k, v in names.items() if v[0] == "~"])


def compare(a: Path, b: Path) -> str | None:
    """None when equal, else what differs (a = this run, b = base)."""
    if a.suffix == ".npz":
        with np.load(a, allow_pickle=False) as x, np.load(b, allow_pickle=False) as y:
            fx, fy = set(x.files) - VOLATILE, set(y.files) - VOLATILE
            d = {k: "+" for k in sorted(fx - fy)} | {k: "-" for k in sorted(fy - fx)}
            d |= {k: "~" + delta(x[k], y[k]) for k in sorted(fx & fy) if not same(x[k], y[k])}
        return keys(d) or None
    if a.suffix == ".json":
        x, y = strip(json.loads(a.read_text())), strip(json.loads(b.read_text()))
        if x == y:
            return None
        if isinstance(x, dict) and isinstance(y, dict):
            return keys({k: "+" for k in x.keys() - y.keys()} | {k: "-" for k in y.keys() - x.keys()}
                        | {k: "~" for k in x.keys() & y.keys() if x[k] != y[k]})
        return "differs"
    if a.suffix in (".jpg", ".png"):
        x, y = cv2.imread(str(a)), cv2.imread(str(b))
        return None if x is not None and y is not None and same(x, y) else "pixels differ"
    return None if a.read_bytes() == b.read_bytes() else "bytes differ"


def files_of(stage: Stage, root: Path, clip: str) -> list[tuple[str, str]]:
    """(name for the report, path relative to the root) of every file the stage's outputs stand for."""
    out = []
    for o in stage.outputs:
        if o == SKELETON:
            out += [(str(p.relative_to(root)), str(p.relative_to(root))) for p in sorted(root.glob("athletes/*/skeleton.json"))]
        elif o.endswith(".mp4"):
            out += [(x, f"{clip}/{x}") for x in (o, o[:-4] + "_sheet.jpg", o[:-4] + "_worst.jpg", o[:-4] + ".worst")]
        else:
            out.append((o, f"{clip}/{o}"))
    return out


def stage_state(stage: Stage, root: Path, base: Path, clip: str) -> dict:
    if not stage.outputs:
        return {"state": "no outputs", "files": {}}
    files, ran = {}, False
    for name, rel in files_of(stage, root, clip):
        a, b = root / rel, base / rel
        if not a.exists() and not b.exists():
            continue
        ran = True
        if not b.exists():
            files[name] = "new file"
        elif not a.exists():
            files[name] = "removed"
        elif (d := compare(a, b)) is not None:
            files[name] = d
    if not ran:
        return {"state": "absent", "files": {}}
    if not files:
        return {"state": "identical", "files": {}}
    return {"state": "new" if all(v == "new file" for v in files.values()) else "changed", "files": files}


def diff(root: Path) -> dict:
    base = root / "base"
    res: dict = {"_no_base": []}
    for d in sorted(p.name for p in root.iterdir() if p.is_dir() and p.name not in ("athletes", "base", "proof")):
        log = base / f"{d}.log"
        ok = (base / d).is_dir() if d.startswith("calibrate_") else log.exists() and "OK evidence:" in log.read_text()
        if not ok:
            res["_no_base"].append(clip_id(d))
            continue
        for s in CALIBRATE if d.startswith("calibrate_") else STAGES:
            res.setdefault(s.name, {})[clip_id(d)] = stage_state(s, root, base, d)
    res["_no_base"] = sorted(set(res["_no_base"]))
    return res


def rollup(clips: dict) -> str:
    """The stage's state over its clips: new > changed > identical > absent (> no outputs)."""
    states = {c["state"] for c in clips.values()}
    return next((s for s in ("new", "changed", "identical", "absent", "no outputs") if s in states), "absent")


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    if not (root / "base").is_dir():
        sys.exit(f"FAIL: {root}/base missing: run base_run.sh {sys.argv[1]} first")
    res = diff(root)
    (root / "changes.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"{'stage':6} {'state':10} clips -> files")
    for s in dict.fromkeys(s.name for s in [*STAGES, *CALIBRATE]):
        clips = res.get(s, {})
        off = {c: v for c, v in clips.items() if v["state"] in ("new", "changed")}
        what = "; ".join(f"{c}: {', '.join(f'{k} {v}'.strip() for k, v in x['files'].items())}" for c, x in off.items())
        print(f"{s:6} {rollup(clips):10} {what or ', '.join(sorted(clips))}")
    if res["_no_base"]:
        print("not compared (no passing base run):", ", ".join(res["_no_base"]))
