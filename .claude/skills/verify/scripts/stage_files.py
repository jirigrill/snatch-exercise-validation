"""Print the src/snatch files that a stage list runs: its stage modules and what they import.

usage: uv run python stage_files.py calibrate|analyze   (from prototype/)

run_clip.sh hashes them into the key of the cached T5 calibration, so a commit that
touches only code the calibration never runs (a later stage, plate.py) keeps it.
stage_cache.py uses code_files() per stage for the same reason.
"""

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


if __name__ == "__main__":
    for f in code_files({"calibrate": CALIBRATE, "analyze": STAGES}[sys.argv[1]]):
        print(f.relative_to(SRC.parent))
