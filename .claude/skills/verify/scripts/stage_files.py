"""Print the src/snatch files that a stage list runs: its stage modules and what they import.

usage: uv run python stage_files.py calibrate|analyze   (from prototype/)

run_clip.sh hashes them into the key of the cached T5 calibration, so a commit that
touches only code the calibration never runs (a later stage, plate.py) keeps it.
"""

import sys
from modulefinder import ModuleFinder
from pathlib import Path

import snatch
from snatch.stages import CALIBRATE, STAGES

src = Path(snatch.__file__).parent.parent
stages = {"calibrate": CALIBRATE, "analyze": STAGES}[sys.argv[1]]
files = {str(Path(snatch.__file__).parent / "stages" / "__init__.py")}  # the stage lists themselves
for module in {s.run.__module__ for s in stages} | {"snatch.stage"}:
    finder = ModuleFinder(path=[str(src)])
    finder.run_script(str(sys.modules[module].__file__))
    files |= {f for name, m in finder.modules.items() if name.startswith("snatch") and (f := getattr(m, "__file__", None))}
    files.add(str(sys.modules[module].__file__))
print("\n".join(sorted(str(Path(f).resolve().relative_to(src.parent)) for f in files)))
