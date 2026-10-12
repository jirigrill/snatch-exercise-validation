# prototype/

The measurement pipeline for the validation (see `../docs/STATUS.md` for what it has to prove). Python 3.12, uv. Run everything from this directory as `uv run python scripts/<script>.py`. Library code is `src/snatch/`, tests are `tests/` (`uv run pytest -q`).

## Pipeline (one clip)

`scripts/run_all.sh` runs steps 0–4 for every clip in `../vids/` and fills only what is missing. Each step writes to `out/<clip>/`.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 0 | `extract_person.py` | clip | `person.npz` (lifter box) |
| 1 | `extract_pose.py` | clip, `person.npz` | `raw_pose.npz` (17 keypoints per frame) |
| 2 | `track_plate.py` | clip | `plate.npz`, `plate_check.jpg`, `bar_path.png` |
| 3 | `analyze.py` | `raw_pose.npz`, `plate.npz` | `angles.csv`, `phases.json`, `phase_sheet.jpg`, `overlay.mp4` |
| 4 | `compare_phases.py` | `raw_pose.npz`, `plate.npz` | `phases_v2.json` (the frozen phase definition) |

## Tools (`scripts/`)

| Script | What |
|---|---|
| `find_reps.py`, `rep_sheets.py` | Propose a rep list from the plate hub; one image strip per rep to check it |
| `overlay_video.py` | Boxes, skeleton and plate outline drawn on a clip |
| `show_npz.py` | Print what is inside an `.npz` |
| `bench.py` | Time the detector and the pose model |

## Studies (`scripts/studies/`)

One-off analyses. Each produced a result in `../docs/results/` and is kept so the result can be rerun.

| Ticket | Scripts |
|---|---|
| #13 phase check | `review_phases.py`, `check_phases_literature.py` |
| #14, #30 frame rate | `build_ladder.py`, `measure_hold.py`, `fps_estimate.py`, `add_timestamps.py` |
| #23 D1 camera view | `d1_views.py`, `d1_near_plate.py`, `d1_sheets.py` |
| #24 D2 arm bend | `arm_bend.py` |
| #22 body height | `body_height.py`, `height_summary.py`, `segment_lengths.py` |
| #22 knee and wrist fill-in | `skeleton_validate.py`, `skeleton_paste.py`, `skeleton_loaded.py`, `skeleton_wrist.py`, `skeleton_camera.py`, `skeleton_sheets.py` |
| Does a shortcut change the results? | `compare_sparse.py`, `compare_rep_pose.py`, `compare_pose_runs.py` |

Run them like the others, from `prototype/`: `uv run python scripts/studies/<script>.py`. Each docstring gives usage, inputs and outputs.

## Library (`src/snatch/`)

| Module | Owns |
|---|---|
| `video`, `person`, `pose` | Reading frames, finding the lifter, running the pose model |
| `plate` | Plate tracking |
| `angles`, `signals`, `phases`, `reps` | Joint angles, smoothing, the phase definition (v2 frozen), rep finding |
| `spread` | Across-rep spread |
| `overlay` | Drawing on frames |

`src/snatch/studies/` holds the modules only the studies use: `ladder` (frame-rate ladder), `markers` (bar markers and their verdict rule), `views` (D1), `armbend` (D2), `height` (body height), `skeleton` (knee and wrist fill-in). The pipeline never imports them.

## `out/`

Committed results, one folder per clip plus the cross-clip files (`fps_estimate.*`, `d1_views.md`, `skeleton/`, ...). Large per-frame arrays are tracked too. Don't write a new run over an existing clip's folder when you only want to test something. Use a scratch folder.
