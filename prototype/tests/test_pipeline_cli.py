import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "pipeline.py"
spec = importlib.util.spec_from_file_location("pipeline_cli", SCRIPT)
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


@pytest.mark.parametrize("argv", [
    ["c.MOV"],                                              # no athlete
    ["--athlete", "jiri"],                                  # no clip
    ["c.MOV", "--calibrate", "b.MOV", "--athlete", "jiri"],  # two clips
    ["c.MOV", "--athlete", "jiri", "--intended", "split"],
    ["c.MOV", "--athlete", "jiri", "--radius", "70"],
    ["c.MOV", "--athlete", "jiri", "--only", "C3"],          # C3 is calibrate only
    ["--calibrate", "b.MOV", "--athlete", "jiri", "--from", "side"],
])
def test_bad_args_exit_2(argv: list[str]) -> None:
    """R1: bad command-line arguments: exit 2."""
    with pytest.raises(SystemExit) as e:
        cli.parse(argv)
    assert e.value.code == 2
