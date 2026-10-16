"""Print the src/snatch files that a stage list runs: its stage modules and what they import.

usage: uv run python stage_files.py calibrate|analyze   (from prototype/)
       uv run python stage_files.py show <base> [NAMES|all]

run_clip.sh hashes them into the key of the cached T5 calibration, so a commit that
touches only code the calibration never runs (a later stage, plate.py) keeps it.
stage_cache.py uses code_files() per stage for the same reason.
show: the stages publish_evidence.sh puts in the PR comment, one line each: `all <list> <stage>`
for every stage, `shown <list> <stage> <outputs>` for a shown one, `focus <list> <stage>` for a
focus one, `shared <list> <stage> <files>` for a context one (the changed files it imports, relative to src). Shown = the stages of a list whose code (module + snatch imports) changed vs <base> (git
diff incl. uncommitted and untracked, from prototype/) and every stage after the first of them; all
of them when scripts/pipeline.py or uv.lock changed; NAMES (space-separated, or `all`) adds stages
by name. Focus (a subset of shown, shown in full) = the stages whose own module changed or named in
NAMES, plus, transitively, every stage reading an output of a focus stage (CLIP ignored) or importing
its module (e.g. side, which reads S4's facing.json without declaring it);
everything when pipeline.py or uv.lock changed. The other shown stages are context (shown because
only shared code or an earlier stage changed; the comment collapses them).
"""

import subprocess
import sys
from collections.abc import Sequence
from modulefinder import ModuleFinder
from pathlib import Path

import snatch
from snatch.stage import CLIP, Stage
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


def focus(stages: Sequence[Stage], changed: set[Path], extra: str) -> list[Stage]:
    """Stages whose own module changed or named in extra, then, transitively, those that read an
    output of one (declared inputs) or import its module (side reads S4's facing.json that way)."""
    names = extra.split()
    if "all" in names or {SRC.parent / "scripts" / "pipeline.py", SRC.parent / "uv.lock"} & changed:
        return list(stages)
    own = {s.name: Path(str(sys.modules[s.run.__module__].__file__)).resolve() for s in stages}
    code = {s.name: set(code_files([s])) for s in stages}
    on = {n for n, f in own.items() if f in changed or n in names}
    while True:
        outs = {o for s in stages if s.name in on for o in s.outputs}
        mods = {own[n] for n in on}
        more = {s.name for s in stages if s.name not in on and ((set(s.inputs) - {CLIP}) & outs or code[s.name] & mods)}
        if not more:
            return [s for s in stages if s.name in on]
        on |= more


if __name__ == "__main__":
    if sys.argv[1] == "show":
        changed = changed_files(sys.argv[2])
        for lst, stages in (("analyze", STAGES), ("calibrate", CALIBRATE)):
            foc = {s.name for s in focus(stages, changed, " ".join(sys.argv[3:]))}
            on = {s.name for s in shown(stages, changed, " ".join(sys.argv[3:]))} | foc
            for s in stages:
                print("all", lst, s.name)
                if s.name in on:
                    print("shown", lst, s.name, *s.outputs)
                if s.name in foc:
                    print("focus", lst, s.name)
                elif s.name in on:
                    print("shared", lst, s.name, *sorted(str(f.relative_to(SRC)) for f in set(code_files([s])) & changed
                                                          if f != Path(str(sys.modules[s.run.__module__].__file__)).resolve()))
        sys.exit()
    for f in code_files({"calibrate": CALIBRATE, "analyze": STAGES}[sys.argv[1]]):
        print(f.relative_to(SRC.parent))
