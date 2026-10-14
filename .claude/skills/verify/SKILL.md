---
name: verify
description: Drive and prove the snatch-exercise-validation prototype (Python CLI pipeline in prototype/: pipeline v2 stages via scripts/pipeline.py; video -> person -> pose -> plate/bar track -> joint angles and snatch phases). Use after changing anything under prototype/src or prototype/scripts, or to check a pipeline output before trusting it.
---

# Verify: snatch pipeline (`prototype/`)

Surface: **CLI pipeline, no server, no UI.** A user runs `uv run python scripts/pipeline.py <clip.MOV> --athlete <id>` and reads files (npz, json, csv, jpg, png, mp4). All commands run from `prototype/` (uv project, Python 3.12). Paths below are relative to the repo root unless stated. Only the Mac is supported (pose runs on CoreML).

## Launch
Nothing to start. One-time: `cd prototype && uv sync`. Models (`~/.cache/rtmlib/hub/checkpoints`: RTMPose-x body7 halpe26, YOLOX-x 378 MB) download on first pose run. The halpe26 pose model needs one network download; doctor prints the command when it is missing.

Ready = doctor passes. Teardown = none (each step exits).

## Doctor (read-only, run first)
```
.claude/skills/verify/scripts/doctor.sh
```
Checks uv, `.venv`, imports, both ONNX models, ffprobe, ffmpeg, test clips T1–T7 in `vids/test/`, CoreML provider. Any `FAIL` -> fix before driving. `vids/` is gitignored and not in a fresh clone: no clips = nothing to drive except `pytest`.

## Drive
Fast gate (3 s, no video): `cd prototype && uv run pytest -q` and `uv run pyright` (baseline on main: 0 errors).

End-to-end: pipeline v2 (`scripts/pipeline.py`, spec `docs/pipeline-v2.html`) on one clip:
```
.claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
```
Default clip `vids/test/T1_*.MOV`. Default root `.scratch/verify/<branch>__<clip id>__<short sha>[-dirty]/` (`/` in the branch becomes `-`; `-dirty` = uncommitted changes under `prototype/` or the verify skill). For several clips pass one root yourself, e.g. `.scratch/verify/<branch>__T1-T7__<sha>`. Writes `<root>/<clip>/` (pipeline outputs), `<root>/<clip>.log`, the athlete `verify` (height 1.73 m, skeleton.json calibrated on T5) in `<root>/athletes/` and the calibration run in `<root>/calibrate_<T5>/`. It runs `pipeline.py` up to four times and checks each run with `scripts/check_pipeline.py`:

| Run | Command | Expected states |
|---|---|---|
| calibrate | `--calibrate T5` (skipped when the root's calibration, or the cache, has the current key) | every stage of `snatch.stages.CALIBRATE` `done` |
| calibrate rerun | the same again | hashed stages `skipped`, S0 `done` |
| first | all stages | every stage `done` (an expected stop: up to it, it `failed`) |
| rerun | the same again | hashed stages `skipped`, S0 and side `done` |

Each check: the pipeline exit (0, or the expected stop's code), `pipeline_status.json` status `ok` (not ok for an expected stop), stages in the order of `snatch.stages.STAGES`, every stage output non-empty, and after the first run each stage's content check (`check_pipeline.py`: S-1 frame times vs clip.json; S1 box on every frame, `t` = frame_times.npy, lifter found on ≥ 90 % of detector runs; S4 keypoints (n, 26, 2) on every frame, no partial file left, facing = filename when the name has `_left_`/`_right_`; S2 `t` = frame_times.npy, plate.csv has n rows, plate found on ≥ 90 % of the moving span, ppm_spread ≤ 0.10, hough_share ≥ 0.5, `passed` (the old sanity check); C3 the near side in skeleton.json fitted on this clip, a gap-free length table, ≥ 3 bins, d_ref within thigh + shank, no self-test values, and calibration.json: rebuilt knee median < 10 px off the visible one in the bent-leg frames). Last, `git status --porcelain prototype/out` must be empty. Prints `OK evidence: <dir> (root <root>)`, exit 0; anything else is `FAIL`, exit 1, and the FAIL line names the real pipeline exit code.

Timing (M4, measured): no cache at all 229–237 s (T5 calibration about 2.5 min of it); T1 fresh with the calibration reused 71 s; a commit that leaves S-1/S1/S4's code alone (any later stage, plate.py) **9 s** (stages reused, every check still run); a full cache hit about 1 s.

Caches (all in `.scratch/verify/cache/`, only passing runs are stored, `VERIFY_NO_CACHE=1` bypasses all three; use it for timing claims and milestones):
- `calibrate/<key>/`: the T5 calibration. The key covers T5 (size + mtime), only the code the calibration runs (`stage_files.py calibrate`: its stage modules and what they import), `scripts/pipeline.py`, `uv.lock` and the verify scripts. A commit that touches only a later stage (plate.py, a new stage) reuses it; a root whose calibration has another key recalibrates.
- `stage/<clip stem>/<stage>/<key>/`: one stage's outputs (`stage_cache.py`), for the analyze run (`STAGES`) and the `--calibrate` run (`CALIBRATE`, under the T5 stem). The key covers what a fresh run of that stage depends on: name, version, params, the content of its inputs (npz: every array but `seconds`, the run time), its code and every snatch module it imports, `scripts/pipeline.py`, `uv.lock`, the model files and the macOS version. It does not name the stage list, so a stage both lists share (S-1, S1, S4) is computed once per clip, e.g. T5's calibration feeds T5 as an analyze clip. A stage writing `SKELETON` (C3, in the athlete store, outside the clip dir) is not cacheable: restore stops there, store skips it; a stage that stopped the run (state `failed`) or never ran is not stored. Before each run (the calibrate run only when the whole calibration is not cached) the hits are restored in pipeline order up to the first miss (log line `reused (stage cache): …`, `reused (stage cache, calibrate): …`); pipeline.py reports them `skipped`, `check_pipeline.py --reused` expects that, and their content checks, worst frames and sheets run as on fresh outputs. A fresh run (`VERIFY_NO_CACHE=1`) of a stage whose key is cached must give the same content, else FAIL "the key misses something": the milestone run audits the cache (the calibrate run too; its stages are also stored after a whole-calibration cache hit). Measured: two fresh runs agree (only `seconds` differs); a 3 px change to one cached keypoint FAILs the audit.
- `<clip>/<key>/`: the whole result. The key covers the clip and T5 (size + mtime), all of `src/snatch/**/*.py`, `scripts/pipeline.py`, `uv.lock` and the verify scripts. On a hit the script prints `cache <key>`, copies the stored outputs into the evidence dir and replays the check lines.

Stages today: S-1 probe, S0 athlete check, S1 person, S4 pose, side check, S2 plate track (calibrate: C3 fit skeleton instead of side). Pipeline exits: 2 = no skeleton (or none for the clip's near side; also an argparse usage error), 7 = no height or one outside 1.40–2.20 m, 4 = plate track failed (S2: plate found on < 90 % of the moving span or ppm_spread > 0.10, status `plate_track_failed`), 6 = bar-only clip given to analyze (S2, status `bar_only`), 3 = bad clip (incl. a calibration clip with too few usable frames, status `calibration_failed`), 8 = facing ambiguous, 9 = missing input, 1 = a crash inside a stage (status `error`).

Expected stops: `expected_stop` in `run_clip.sh` lists the clips that stop by design, as `<exit> <stage>`. Today: T4 `2 side` (faces left; T5 calibrates the right side only), T5 `6 S2` (bar-only clip: no plate). Add one when a stage stops a test clip by design (S4 exit 8). check_pipeline.py `--stop <stage>` checks such a run; a stop at S2 still has its files, so it checks `plate_check.jpg` and `overlays/2_plate.mp4` exist and are non-empty.

Detector crash: the detector sometimes crashes at interpreter exit (`recursive_mutex lock failed`, `.scratch/plan/README.md` notes). `run_clip.sh` reruns that pipeline call once (a first run from a clean dir) and logs `retry <run>: pipeline.py exit <code>, recursive_mutex crash at exit`. A second crash is a FAIL.

Adding a stage: the stage goes into `snatch.stages.STAGES`; `run_clip.sh` drives it with no edit. Add its content check to `CHECKS` in `check_pipeline.py` when there is more to check than its files existing, and have the check call `worst()` with the stage's own badness per frame, so its overlay gets a worst-frames sheet. The stage cache picks it up with no edit (its key, store, restore), on two conditions: (1) every file the stage reads is in `Stage.inputs` (S5/S6: `skeleton.json`, `scale.json` too), else a change to it is not in the key and only the milestone's fresh audit catches it; (2) the same inputs give the same outputs: no timestamps or run times in its files (as C3's `fitted`), or add the field to `VOLATILE` in `stage_cache.py`, else the fresh audit FAILs.

Manual run: `uv run python scripts/pipeline.py <clip> --athlete <id> [--height <m>] [--calibrate <bar.MOV>] [--load <kg>] --out <evidence>/<clip> --athletes <evidence>/athletes [--only S | --from S] [--force]`. Always pass `--out` and `--athletes` under the evidence root. Prefer `run_clip.sh`: a manual run gets no checks, sheets or cache.

### Levels
- **Per commit to a branch/PR:** `pytest -q` + `pyright` (0 errors) + `run_clip.sh` on T1, look at the frame sheets, then `publish_evidence.sh` to the PR (review covers every shown image).
- **Milestone items only** (`.scratch/plan/README.md`): `VERIFY_NO_CACHE=1 run_clip.sh` (fresh, audits the stage cache) on T1–T7 (T5 bar-only, T6/T7 60 fps) into one evidence root vs main, every diff explained; publish that root.

Test clips T1–T7 (`vids/test/`): what each covers and how to rebuild them in [features/test-clips.md](features/test-clips.md). Doctor fails when they are missing. 240 fps clips in `vids/` and `vids/spike/` take minutes to an hour (detector ~0.4 s per detected frame on CPU). Per-feature recipes: `features/README.md`.

## Evidence
Per proof keep, under the evidence root (gitignored) and published to the PR:
- the run log (`<clip>.log`, the check lines) and the `OK evidence:` line;
- **look at** every image in `<clip>/overlays/` and `calibrate_<T5>/overlays/` with Read (an mp4 can't be viewed):
  - `0_clip_sheet.jpg` (written by S-1: 6 frames of the clip); `plate_check.jpg` (S2, in the clip dir, not overlays/);
  - `<name>_sheet.jpg` for every overlay mp4 (`run_clip.sh`: 8 evenly spaced frames): `1_person` (box on the lifter in every phase; thin = interpolated, red = across a missed detection), `4_pose` (skeleton on the lifter, near leg green on a right-facing clip), `2_plate` (outline on the plate rim, green when the sanity check passed, orange when not; trail = hub over the last 0.5 s), `calibration_overlay` (green RTMPose, magenta the same pose with the near knee rebuilt wherever the leg is bent enough for S6 to rebuild it; magenta should cover green; red border = > 20 px apart);
  - `<name>_worst.jpg` (4 frames): the frames the stage scores worst on, from `<name>.worst` (line 2 says by what): `1_person` detector runs that missed the lifter (only when there are any), `4_pose` the lowest near-knee scores, `2_plate` the frames where px_per_m is farthest from its median (or no plate inside the moving span), `calibration_overlay` the rebuilt knee farthest from RTMPose's. Evenly spaced frames miss the frames where a stage is wrong (#56: the airborne f1695–1698 never showed up), so the review names every worst frame and says what is wrong or right there.
  An existing file is not proof;
- for a code change that changes a stage's outputs: same clip before/after (`git stash` or a worktree), diff the outputs; any diff must be explained.

Publish to the PR (after the commit is pushed, so the log's `commit` line names it):
```
.claude/skills/verify/scripts/publish_evidence.sh <evidence_root> "<review: one line per sheet, every worst frame named>"
```
`DRY_RUN=1` prints the comment and pushes nothing. The comment shows only what a reviewer needs: the commit once, the run-state lines, the review, and for the **shown stages** their detail lines and images. Shown = the stages (per list, `STAGES` and `CALIBRATE`) whose code (`stage_files.code_files([stage])`) changed vs the merge base with `origin/main`, plus every stage after the first of them; all of them when `scripts/pipeline.py` or `uv.lock` changed (`stage_files.py show <base>` computes it). `SHOW_STAGES="S2 C3"` adds stages by name (a changed sheet or check drawing), `SHOW_STAGES=all` shows all. The others are named in one line ("Unchanged vs main"; nothing shown: "No stage code changed vs main"). Images per shown stage, via `Stage.outputs`: each png/jpg output, and per mp4 output its `_sheet.jpg` and `_worst.jpg` with a line `worst frames (from <name>.worst): f461 …` (the review uses these numbers, not the sheet labels); the calibration's under "calibration". No per-file links, one `Files:` link to the root's tree. The script FAILs before pushing when the review does not mention the file stem of every shown image (`2_plate_sheet`, `plate_check`, `bar_path`, …) or every frame number of a shown `.worst` (`f461` or `461`).

Explainer: when the PR text alone is not enough (a new stage, a changed data flow, a new kind of output), make a `/show-me:show-me` page, then `.claude/skills/verify/scripts/screenshot.sh <page.html> <evidence_root>/explain.png` (full-page PNG via the installed Chrome; GitHub shows no HTML and the repo is private, so no link); every image at the top of the root goes into the comment under "Explainer". The script commits the root to the branch `evidence/pr-<n>` (own history, never merged) and comments on the PR, all pinned to the evidence commit. The checkout and its index are not touched. `.github/workflows/delete-evidence.yml` deletes `evidence/pr-<n>` when the PR closes (the comment text stays; images and links break). Never merge or open a PR from `evidence/*`.

Standards: drive the real pipeline on real clips, not a function in a REPL; no stray writes into `prototype/out/`.

## Isolation
One `run_clip.sh` at a time: it holds `.scratch/verify/.run_clip.lock`, and a second run fails at once naming the first (pid, clip, root). Two runs would share the caches and a root's calibration, and CoreML + CPU contention spoils timings. For several clips, loop them in one shell, one after another. A lock left by a killed run (dead pid) is taken over.

## Cleanup
Nothing to kill. Remove only what you started: background jobs by PID (`kill <pid>` of what you launched, never `pkill python`). Don't delete evidence by hand: `sweep_evidence.sh` (run by the SessionStart hook in `.claude/settings.json`, safe to run by hand, `DRY_RUN=1` only prints) deletes a root under `.scratch/verify/` once its branch (from the log's `commit` line) is neither checked out nor has an open PR, so local evidence goes once the PR is merged or closed, and keeps the 3 newest entries per cache dir. Offline or without `gh` it deletes nothing.

## Maintenance
Feature map: `features/README.md`. Update it with `/maintain-verification-skill`.
