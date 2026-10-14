"""Print the src/snatch files that a stage list runs: its stage modules and what they import.

usage: uv run python stage_files.py calibrate|analyze   (from prototype/)
       uv run python stage_files.py show <base> [NAMES|all]

run_clip.sh hashes them into the key of the cached T5 calibration, so a commit that
touches only code the calibration never runs (a later stage, plate.py) keeps it.
stage_cache.py uses code_files() per stage for the same reason.
show: the stages publish_evidence.sh puts in the PR comment, one line each: `all <list> <stage>`
for every stage, `shown <list> <stage> <outputs>` for a shown one. Shown = the stages of a list whose
code changed vs <base> (git diff incl. uncommitted and untracked, from prototype/) and every stage
after the first of them; all of them when scripts/pipeline.py or uv.lock changed; NAMES (space-
separated, or `all`) adds stages by name.
"""

import subprocess
import sys
from collections.abc import Sequence
from modulefinder import ModuleFinder
from pathlib import Path

import snatch
from snatch.stage import Stage
from snatch.stages import CALIBRATE, STAGES

SRC = Path(snatch.__file__).parent.parent


def code_files(stages: Sequence[Stage]) -> list[Path]:
    """The stage list file, each stage's module and every snatch module those import."""
    files = {str(Path(snatch.__file__).parent / "stages" / "__init__.py")}
    for module in {s.run.__module__ for s in stages} | {"snatch.stage"}:
        finder = ModuleFinder(path=[str(SRC)])
        finder.run_script(str(sys.modules[module].__file__))
        files |= {f for name, m in finder.modules.items() if name.startswith("snatch") and (f := getattr(m, "__file__", None))}
        files.add(str(sys.modules[module].__file__))
    return sorted(Path(f).resolve() for f in files)


def changed_files(base: str) -> set[Path]:
    """Files changed vs base, absolute (git diff incl. the working tree, plus untracked)."""
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    out = subprocess.check_output(["git", "diff", "--name-only", base], text=True, cwd=root)
    out += subprocess.check_output(["git", "ls-files", "-o", "--exclude-standard"], text=True, cwd=root)
    return {(root / line).resolve() for line in out.splitlines() if line}


def shown(stages: Sequence[Stage], changed: set[Path], extra: str) -> list[Stage]:
    names = extra.split()
    everything = "all" in names or bool({SRC.parent / "scripts" / "pipeline.py", SRC.parent / "uv.lock"} & changed)
    first = next((i for i, s in enumerate(stages) if set(code_files([s])) & changed), len(stages))
    return [s for i, s in enumerate(stages) if everything or i >= first or s.name in names]


if __name__ == "__main__":
    if sys.argv[1] == "show":
        changed = changed_files(sys.argv[2])
        for lst, stages in (("analyze", STAGES), ("calibrate", CALIBRATE)):
            on = {s.name for s in shown(stages, changed, " ".join(sys.argv[3:]))}
            for s in stages:
                print("all", lst, s.name)
                if s.name in on:
                    print("shown", lst, s.name, *s.outputs)
        sys.exit()
    for f in code_files({"calibrate": CALIBRATE, "analyze": STAGES}[sys.argv[1]]):
        print(f.relative_to(SRC.parent))
