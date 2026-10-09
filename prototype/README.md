# prototype/

The measurement pipeline for the validation (see `../docs/STATUS.md` for what it has to prove). Python 3.12, uv. Run everything from this directory as `uv run python scripts/<script>.py`. Library code is `src/snatch/`, tests are `tests/` (`uv run pytest -q`).

## Pipeline (one clip)

`scripts/run_all.sh` runs steps 0–4 for every clip in `../vids/` and fills only what is missing. `../.claude/skills/verify/scripts/run_clip.sh` runs them for one clip into a scratch folder. Each step writes to `out/<clip>/`.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 0 | `extract_person.py` | clip | `person.npz` (lifter box) |
| 1 | `extract_pose.py` | clip, `person.npz` | `raw_pose.npz` (17 keypoints per frame) |
| 2 | `track_plate.py` | clip | `plate.npz`, `plate_check.jpg`, `bar_path.png` |
| 3 | `analyze.py` | `raw_pose.npz`, `plate.npz` | `angles.csv`, `phases.json`, `phase_sheet.jpg`, `overlay.mp4` |
| 4 | `compare_phases.py` | `raw_pose.npz`, `plate.npz` | `phases_v2.json` (the frozen phase definition) |

## Other scripts, by purpose

| Purpose | Scripts |
|---|---|
| Rep lists | `find_reps.py`, `rep_sheets.py` |
| Frame-rate work (#14, #30) | `build_ladder.py`, `measure_hold.py`, `fps_estimate.py`, `add_timestamps.py` |
| Phase checks (#13) | `review_phases.py`, `check_phases_literature.py` |
| Spike session D1 (#23) | `d1_views.py`, `d1_near_plate.py`, `d1_sheets.py` |
| Spike session D2 (#24) | `arm_bend.py` |
| Spike session body height (#22) | `body_height.py`, `height_summary.py`, `segment_lengths.py` |
| Spike session knee and wrist fill-in (#22) | `skeleton_validate.py`, `skeleton_paste.py`, `skeleton_loaded.py`, `skeleton_wrist.py`, `skeleton_camera.py`, `skeleton_sheets.py` |
| Does a shortcut change the results? | `compare_sparse.py`, `compare_rep_pose.py`, `compare_pose_runs.py` |
| Tools | `overlay_video.py`, `show_npz.py`, `bench.py` |

Each script's docstring gives its usage, inputs and outputs. The result a script produced is in `../docs/results/`.

## Library (`src/snatch/`)

| Module | Owns |
|---|---|
| `video`, `person`, `pose` | Reading frames, finding the lifter, running the pose model |
| `plate`, `ladder` | Plate tracking and the frame-rate ladder |
| `angles`, `signals`, `phases`, `reps` | Joint angles, smoothing, the phase definition, rep finding |
| `spread`, `markers` | Across-rep spread and the bar markers with their verdict rule |
| `views`, `armbend`, `height`, `skeleton` | Spike session analyses |
| `overlay` | Drawing on frames |

## `out/`

Committed results, one folder per clip plus the cross-clip files (`fps_estimate.*`, `d1_views.md`, `skeleton/`, ...). Large per-frame arrays are tracked too. Don't write a new run over an existing clip's folder when you only want to test something. Use a scratch folder.
