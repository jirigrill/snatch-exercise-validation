# prototype/

The measurement pipeline for the validation (see `../docs/STATUS.md` for what it has to prove). Python 3.12, uv. Run everything from this directory as `uv run python scripts/<script>.py`. Library code is `src/snatch/`, tests are `tests/` (`uv run pytest -q`).

## Pipeline v2 (one clip)

`scripts/pipeline.py` runs the v2 stages (`src/snatch/stages/`, spec `../docs/pipeline-v2.html`). Each stage writes to `out/<clip>/`.

## Pipeline v1 (deleted with `run_all.sh` in the S9 PR)

`scripts/run_all.sh` runs steps 0–4 for every clip in `../vids/` and fills only what is missing. Each step writes to `out/<clip>/`. The scripts are the source for the v2 stages still to come (S2, S3, S7).

| Step | Script | Reads | Writes |
|---|---|---|---|
| 0 | `extract_person.py` | clip | `person.npz` (lifter box) |
| 1 | `extract_pose.py` | clip, `person.npz` | `raw_pose.npz` (17 keypoints per frame) |
| 2 | `track_plate.py` | clip | `plate.npz`, `plate_check.jpg`, `bar_path.png` |
| 3 | `analyze.py` | `raw_pose.npz`, `plate.npz` | `angles.csv`, `phases.json`, `phase_sheet.jpg`, `overlay.mp4` |
| 4 | `compare_phases.py` | `raw_pose.npz`, `plate.npz` | `phases_v2.json` (the frozen phase definition) |

`find_reps.py` proposes a rep list from the plate hub; `overlay_video.py` draws boxes, skeleton and plate outline on a clip (`--overlay`).

## Studies (`scripts/studies/`)

Kept only as the source of a v2 stage still to come; delete each one in the PR that moves its code.

| Stage | Scripts |
|---|---|
| S2 (oblique near plate, used by `run_all.sh`) | `d1_near_plate.py` |
| S3 (attempt windows vs whole-clip pose) | `compare_rep_pose.py` |
| S5, S6 (scale, knee and wrist fill-in) | `skeleton_loaded.py`, `skeleton_validate.py`, `skeleton_paste.py`, `skeleton_sheets.py`, `skeleton_wrist.py` |

Run them from `prototype/`: `uv run python scripts/studies/<script>.py`. Each docstring gives usage, inputs and outputs.

## Library (`src/snatch/`)

| Module | Owns |
|---|---|
| `stage`, `stages/` | The v2 stage runner and the stages |
| `video`, `person`, `pose` | Reading frames, finding the lifter, running the pose model |
| `plate` | Plate tracking |
| `angles`, `signals`, `phases`, `reps` | Joint angles, smoothing, the phase definition (v2 frozen), rep finding |
| `spread` | Across-rep spread |
| `skeleton`, `athlete_store` | Skeleton length table (C3), athlete profiles |
| `overlay` | Drawing on frames |

`src/snatch/studies/` holds the modules only the kept studies use: `views` (hidden-joint mask for S6), `height` (body height), `skeleton` (knee and wrist fill-in for S6).

## `out/`

Committed results, one folder per clip plus the cross-clip files (`fps_estimate.*`, `d1_views.md`, `skeleton/`, ...). Large per-frame arrays are tracked too. Don't write a new run over an existing clip's folder when you only want to test something. Use a scratch folder.
