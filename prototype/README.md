# prototype/

The measurement pipeline for the validation (see `../docs/STATUS.md` for what it has to prove). Python 3.12, uv. Run everything from this directory with `uv run`. Library code is `src/snatch/`, tests are `tests/` (`uv run pytest -q`).

## Pipeline v2 (one clip)

`uv run python scripts/pipeline.py clip.MOV --athlete <name> [--height <m>] [--calibrate bar.MOV]` runs the v2 stages (`src/snatch/stages/`, spec `../docs/pipeline-v2.html`) on one clip; `--help` lists the options. Each stage writes to `out/<clip>/`.

## Library (`src/snatch/`)

| Module | Owns |
|---|---|
| `stage`, `stages/` | The v2 stage runner and the stages |
| `video`, `person`, `pose` | Reading frames, finding the lifter, running the pose model (`HALPE26` keypoint names) |
| `plate` | Plate tracking |
| `signals`, `reps` | Smoothing, attempt finding (S3) |
| `skeleton`, `athlete_store` | Skeleton length table (C3), athlete profiles |
| `overlay` | Drawing on frames |

## `out/`

Committed results, one folder per clip plus the cross-clip files (`fps_estimate.*`, `d1_views.md`, `skeleton/`, ...). Large per-frame arrays are tracked too. Don't write a new run over an existing clip's folder when you only want to test something. Use a scratch folder.
