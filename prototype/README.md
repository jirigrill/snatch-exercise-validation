# prototype/

The measurement pipeline for the validation (see `../docs/STATUS.md` for what it has to prove). Python 3.12, uv. Run everything from this directory with `uv run`. Library code is `src/snatch/`, tests are `tests/` (`uv run pytest -q`).

## Pipeline v2 (one clip)

`uv run python scripts/pipeline.py clip.MOV --athlete <name> [--height <m>] [--calibrate bar.MOV]` runs the v2 stages (`src/snatch/stages/`, spec `../docs/pipeline-v2.html`) on one clip; `--help` lists the options. Each stage writes to `out/<clip>/`. Stages in order: S-1 probe, S0 athlete check, S1 person, S2 plate track, S3 attempts, S4 pose, side check, S5 scale, S6 fill, S7 angles + phases, S8 judge, S9 bar-path metrics + fault rules (`findings.json`, `findings_sheet.jpg`, `overlays/9_findings.mp4`). After a run where S8 and S9 ran, pipeline.py writes `report.json` (one record per attempt: final_label computed from judgement.json + findings, reason from judgement.json, borders and phases, key angles (knee, hip, elbow) at 5 borders with source seen/filled/hidden (elbow hidden = angles.csv wrist_hidden, hip/knee hidden = S6 hidden at that joint, the signals S8 uses), the S9 metrics and findings, clip warnings) and `overlay.mp4` (the `.mp4` overlays the stages declare, one after another in stage order; `overlay.json` records each layer's path, size and sha256, and overlay.mp4 is re-rendered when that list changes). Every run first deletes report.json, overlay.mp4 and overlay.json, so a clip that stops earlier (exit code) gets only `pipeline_status.json`. There is no batch script; run clips one at a time, or through the verify skill's `run_clip.sh`.

## Library (`src/snatch/`)

| Module | Owns |
|---|---|
| `stage`, `stages/` | The v2 stage runner and the stages |
| `video`, `person`, `pose` | Reading frames, finding the lifter, running the pose model (`HALPE26` keypoint names) |
| `plate` | Plate tracking |
| `signals`, `reps` | Smoothing, attempt finding (S3) |
| `skeleton`, `athlete_store` | Skeleton length table (C3), athlete profiles |
| `fill`, `scale`, `phases`, `judge`, `findings` | S6 fill, S5 scale, S7 phases, S8 judge rules, S9 bar-path metrics + fault rules (pure logic) |
| `overlay` | Drawing on frames |

## `out/`

Committed v1 results, one folder per clip (the cross-clip study outputs were deleted with v1 in #68; git history has them). Large per-frame arrays are tracked too. Don't write a new run over an existing clip's folder when you only want to test something. Use a scratch folder.
