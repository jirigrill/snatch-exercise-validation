import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "pipeline.py"
spec = importlib.util.spec_from_file_location("pipeline_cli", SCRIPT)
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def test_flags_land_in_ctx() -> None:
    ctx, _ = cli.parse(["c.MOV", "--athlete", "jiri", "--height", "1.8", "--load", "7.5",
                        "--intended", "power", "--radius", "70:140", "--athletes", "/a"])
    assert ctx.clip == Path("c.MOV") and ctx.out == Path("out/c") and ctx.athletes == Path("/a")
    assert ctx.params == {"athlete": "jiri", "height": 1.8, "load": 7.5, "intended": "power",
                          "radius": (70, 140), "calibrate": False}


def test_calibrate_takes_the_bar_clip() -> None:
    ctx, _ = cli.parse(["--calibrate", "bar.MOV", "--athlete", "jiri"])
    assert ctx.clip == Path("bar.MOV") and ctx.params["calibrate"] is True


@pytest.mark.parametrize("argv", [
    ["c.MOV"],                                              # no athlete
    ["--athlete", "jiri"],                                  # no clip
    ["c.MOV", "--calibrate", "b.MOV", "--athlete", "jiri"],  # two clips
    ["c.MOV", "--athlete", "jiri", "--intended", "split"],
    ["c.MOV", "--athlete", "jiri", "--radius", "70"],
])
def test_bad_args_exit_2(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as e:
        cli.parse(argv)
    assert e.value.code == 2
