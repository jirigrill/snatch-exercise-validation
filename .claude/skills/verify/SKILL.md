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
Checks uv, `.venv`, imports, both ONNX models, ffprobe, ffmpeg, test clips T1–T8 in `vids/test/`, CoreML provider. Any `FAIL` -> fix before driving. `vids/` is gitignored and not in a fresh clone: no clips = nothing to drive except `pytest`.

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

Each check: the pipeline exit (0, or the expected stop's code), `pipeline_status.json` status `ok` (not ok for an expected stop), stages in the order of `snatch.stages.STAGES`, every stage output non-empty, and after the first run each stage's content check (`check_pipeline.py`: S-1 frame times vs clip.json; S1 box on every frame, `t` = frame_times.npy, lifter found on ≥ 90 % of detector runs; S2 `t` = frame_times.npy, plate.csv has n rows, plate found on ≥ 90 % of the moving span, ppm_spread ≤ 0.10, hough_share ≥ 0.5, `passed` (the old sanity check); S3 attempts.json consistent (windows inside the clip, start < end, peak_m ≥ knee_height_m, plate_found ≥ 0.9, attempt count = `expected_attempts`); S4 keypoints (n, 26, 2), posed frames = exactly the attempt windows of attempts.json (calibrate: every frame), `ranges` = the windows, no partial file left, facing = filename when the name has `_left_`/`_right_`; S5 scale.json fields; the method equals `expected_scale` when the clip has one; method `none`: factor null, 0 frames, nothing else checked; otherwise thigh/shank within 10 % of the skeleton's, no frame used with a covered near hip or ankle (visible_knee: knee too; `ellipse_dist < 1`, recomputed from raw_pose + plate.npz), standing: median raw near-knee angle on the frames used >= 165 deg and a window in each attempt, plus factor / median plate px/m vs T1's in the same root (within 5 % when the clip is from T1's session, the date token after the T id; another session: reported only; no worst-frames sheet: `5_scale.jpg` is not an mp4); C3 the near side in skeleton.json fitted on this clip, a gap-free length table, ≥ 3 bins, d_ref within thigh + shank, no self-test values, and calibration.json: rebuilt knee median < 10 px off the visible one in the bent-leg frames). Last, `git status --porcelain prototype/out` must be empty. Prints `OK evidence: <dir> (root <root>)`, exit 0; anything else is `FAIL`, exit 1, and the FAIL line names the real pipeline exit code.

Timing (M4, measured): no cache at all 229–237 s (T5 calibration about 2.5 min of it); T1 fresh with the calibration reused 71 s; a commit that leaves S-1/S1/S4's code alone (any later stage, plate.py) **9 s** (stages reused, every check still run); a full cache hit about 1 s.

Caches (all in `.scratch/verify/cache/`, only passing runs are stored, `VERIFY_NO_CACHE=1` bypasses all three; use it for timing claims and milestones):
- `calibrate/<key>/`: the T5 calibration. The key covers T5 (size + mtime), only the code the calibration runs (`stage_files.py calibrate`: its stage modules and what they import), `scripts/pipeline.py`, `uv.lock` and the verify scripts. A commit that touches only a later stage (plate.py, a new stage) reuses it; a root whose calibration has another key recalibrates.
- `stage/<clip stem>/<stage>/<key>/`: one stage's outputs (`stage_cache.py`), for the analyze run (`STAGES`) and the `--calibrate` run (`CALIBRATE`, under the T5 stem). The key covers what a fresh run of that stage depends on: name, version, params, the content of its inputs (npz: every array but `seconds`, the run time), its code and every snatch module it imports, `scripts/pipeline.py`, `uv.lock`, the model files and the macOS version. It does not name the stage list, so a stage both lists share (S-1, S1; not S4: analyze hashes attempts.json) is computed once per clip, e.g. T5's calibration feeds T5 as an analyze clip. A stage writing `SKELETON` (C3, in the athlete store, outside the clip dir) is not cacheable: restore stops there, store skips it; a stage that stopped the run (state `failed`) or never ran is not stored. Before each run (the calibrate run only when the whole calibration is not cached) the hits are restored in pipeline order up to the first miss (log line `reused (stage cache): …`, `reused (stage cache, calibrate): …`); pipeline.py reports them `skipped`, `check_pipeline.py --reused` expects that, and their content checks, worst frames and sheets run as on fresh outputs. A fresh run (`VERIFY_NO_CACHE=1`) of a stage whose key is cached must give the same content, else FAIL "the key misses something": the milestone run audits the cache (the calibrate run too; its stages are also stored after a whole-calibration cache hit). Measured: two fresh runs agree (only `seconds` differs); a 3 px change to one cached keypoint FAILs the audit.
- `<clip>/<key>/`: the whole result. The key covers the clip and T5 (size + mtime), all of `src/snatch/**/*.py`, `scripts/pipeline.py`, `uv.lock` and the verify scripts. On a hit the script prints `cache <key>`, copies the stored outputs into the evidence dir and replays the check lines.

Stages today: S-1 probe, S0 athlete check, S1 person, S2 plate track, S3 attempts, S4 pose (analyze: only the attempt windows), side check (calibrate: no S2/S3, S4 poses the whole clip, C3 fit skeleton instead of side). S5 clip scale (analyze only; reads plate.npz so joints inside the plate outline are not used; no usable frames = method `none`, exit 0; exit 5 = thigh/shank off). S6 fill (the hidden near knee), S7 angles + phases (angles.csv, angles.png, phases.json, phase_sheet.jpg, grabs/, `7_phases.mp4`; its `grabs/` is a directory output, which stage.py, stage_cache.py, diff_outputs.py and check_pipeline.py handle; no worst-frames sheet). S3 reads `athlete.json` from the athlete store (`ATHLETE` input); S0 does not rewrite it when `--height` is unchanged, so S3 reruns skipped. Pipeline exits: 2 = no skeleton (or none for the clip's near side; also an argparse usage error), 7 = no height or one outside 1.40–2.20 m, 4 = plate track failed (S2: plate found on < 90 % of the moving span or ppm_spread > 0.10; S3: plate found on < 90 % inside an attempt; status `plate_track_failed`), 6 = bar-only clip given to analyze (S2, status `bar_only`), 3 = bad clip (incl. a calibration clip with too few usable frames, status `calibration_failed`), 8 = facing ambiguous, 9 = missing input, 1 = a crash inside a stage (status `error`).

Expected attempts: `expected_attempts` in `run_clip.sh` gives the number of attempts S3 must find (T1–T4, T6, T7 one, T7 = a standup, one failed attempt; T8 two); `check_pipeline.py --attempts N` asserts it on the first run, also on T4 (stops at `side`, after S3). Add a clip's count when it is added.

Expected scale method: `expected_scale` in `run_clip.sh` gives S5's method per clip (T1, T2, T6, T8 `standing`; T3 `visible_knee`; T7 `none`); `check_pipeline.py --scale-method <m>` asserts it (see S5 above). Add a clip when it is added.

Expected stops: `expected_stop` in `run_clip.sh` lists the clips that stop by design, as `<exit> <stage>`. Today: T4 `2 side` (faces left; T5 calibrates the right side only), T5 `6 S2` (bar-only clip: no plate). Add one when a stage stops a test clip by design (S4 exit 8). check_pipeline.py `--stop <stage>` checks such a run; a stop at S2 still has its files, so it checks `plate_check.jpg` and `overlays/2_plate.mp4` exist and are non-empty.

Detector crash: the detector sometimes crashes at interpreter exit (`recursive_mutex lock failed`, `.scratch/plan/README.md` notes). `run_clip.sh` reruns that pipeline call once (a first run from a clean dir) and logs `retry <run>: pipeline.py exit <code>, recursive_mutex crash at exit`. A second crash is a FAIL.

Adding a stage: the stage goes into `snatch.stages.STAGES`; `run_clip.sh` drives it with no edit. Add its content check to `CHECKS` in `check_pipeline.py` when there is more to check than its files existing, and have the check call `worst()` with the stage's own badness per frame, so its overlay gets a worst-frames sheet. The stage cache picks it up with no edit (its key, store, restore), on two conditions: (1) every file the stage reads is in `Stage.inputs` (S5/S6: `skeleton.json`, `scale.json` too), else a change to it is not in the key and only the milestone's fresh audit catches it; (2) the same inputs give the same outputs: no timestamps or run times in its files (as C3's `fitted`), or add the field to `VOLATILE` in `stage_cache.py`, else the fresh audit FAILs.

Manual run: `uv run python scripts/pipeline.py <clip> --athlete <id> [--height <m>] [--calibrate <bar.MOV>] [--load <kg>] --out <evidence>/<clip> --athletes <evidence>/athletes [--only S | --from S] [--force]`. Always pass `--out` and `--athletes` under the evidence root. Prefer `run_clip.sh`: a manual run gets no checks, sheets or cache.

### Levels
- **Per commit to a branch/PR:** `pytest -q` + `pyright` (0 errors) + `run_clip.sh` on T1 + `base_run.sh`, look at the changed stages' images, then `publish_evidence.sh <root> review.md` to the PR (the review covers every shown image). When a stage's outputs change or a stage is new (state `new`/`changed` on any clip), run T1–T8 into the one root (stage-cached, so cheap), and every such stage needs a proof or a `no proof:` line; publish FAILs otherwise.
- **Milestone items only** (`.scratch/plan/README.md`): one `VERIFY_NO_CACHE=1 run_clip.sh` (fresh, audits the stage cache) on T1–T8 (T5 bar-only, T6/T7 60 fps) into one evidence root, every later run cached; what the milestone checks on those outputs comes from its spec in `.scratch/plan/` (`validation-milestone.md`); publish that root.

Test clips T1–T8 (`vids/test/`): what each covers and how to rebuild them in [features/test-clips.md](features/test-clips.md). Doctor fails when they are missing. 240 fps clips in `vids/` and `vids/spike/` take minutes to an hour (detector ~0.4 s per detected frame on CPU). Per-feature recipes: `features/README.md`.

## Evidence
Per proof keep, under the evidence root (gitignored) and published to the PR:
- the run log (`<clip>.log`, the check lines) and the `OK evidence:` line;
- what changed vs main, from outputs, not code: `base_run.sh <root>` runs main's own pipeline (the merge base with `origin/main`, a git worktree in `.scratch/verify/base-worktrees/<sha>` sharing the caches and the lock) on the same clips into `<root>/base/` (mostly cached, cheap; idempotent); `diff_outputs.py <root>` (from `prototype/`, publish reruns it) compares every stage's outputs per clip (npz arrays but the run time, json by key, files by bytes) and writes `<root>/changes.json` with a state per stage and clip: `new` (not on main), `changed`, `identical`, `absent` (did not run: an expected stop). A stage counts as changed when it is new or changed on any clip; only those show images. Fresh and cached outputs compare identical (measured 2026-10-21, T1 incl. calibration, `VERIFY_NO_CACHE=1` vs the cached main base: every stage identical, mp4s included), so a milestone's fresh run diffs cleanly against a cached base. Without `base/` publish falls back to the code rule (`stage_files.py show`: stages whose code changed vs the merge base, and every stage after) and says so;
- **look at** every image of the changed stages with Read (an mp4 can't be viewed). What each stage does and what to look for in each image (`<name>_sheet.jpg` = 8 evenly spaced frames; `<name>_worst.jpg` = the frames the stage scores worst on, from `<name>.worst`) is in [features/stage-guide.md](features/stage-guide.md), one section per stage, and goes into the comment. The review names every worst frame and says what is wrong or right there (evenly spaced frames miss the bad ones: #56). An existing file is not proof;
- a proof for a new or changed stage: what question it answers, the evidence with ground truth where possible, a verdict. The skill makes none itself; the PR adds a script that writes `<root>/proof/<stage>/verdict.md` (plain English: question, number, yes/no) and png/jpg images, and publish puts them at the top of that stage's section (a calibration stage that is also an analyze stage, S1/S4: `proof/<stage>_calibration/`). Publish FAILs when a shown stage is new or changed and has no `proof/<label>/verdict.md`, unless its review section has a `no proof:` line.

Proof spec. A new or changed stage ships `scripts/proofs/<stage>.py <evidence_root>` (from `prototype/`) writing `proof/<label>/`. Worked example: `proofs/s6.py` (S6's paste test; arrives with #74, on `feat/s6-fill-v2` until then). `verdict.md` answers the stage's questions in plain English for someone who did not follow the work:
- per question: Question -> the numbers (a table) -> **Answer: yes/no**; say no when the numbers say no, never tune to pass;
- ground truth wherever possible (S6: a synthetic occlusion with a known answer, the pasted plate), else say there is none;
- compare with what the stage replaces (S6: RTMPose's guess), not with nothing;
- out-of-sample data (S6: not the calibration clip);
- a "How this test works" paragraph, with its limits;
- images with legends readable at ~900 px;
- cached (`.scratch/verify/cache/proof-<stage>/<key>/`) so reruns take seconds.
Escape: a `no proof: <reason>` line under the stage's `## <stage>` in review.md (rendered "**No proof:** <reason>"). Legitimate only when another stage's proof covers the change ("S5's new multipliers are tested by S6's proof") or it is a pure output-format change with nothing to judge.

S6 proof: `proofs/s6.py` (paste test: a real plate pasted on a bar-only clip, RTMPose vs S6 against the true knee; plus the loaded clips' knee curves). From `prototype/`, after `run_clip.sh` on T1 T2 T3 T6 T7 T8 into one root: `uv run python ../.claude/skills/verify/scripts/proofs/s6.py <evidence_root>` writes `<root>/proof/S6/` (verdict.md + 3 images). Fresh about 5 min (clean-clip detector and pose are cached in `.scratch/verify/cache/proof-s6/`), cached 20 s.

S7 proof: `proofs/s7.py` (S7's 7 phase borders against the true frames in `prototype/tests/data/s7_reference.json`, per border tolerance; compared with the two blind markers' errors and their T1 vs T8 consistency). From `prototype/`, after `run_clip.sh` on T1 T2 T3 T6 T7 T8 into one root: `uv run python ../.claude/skills/verify/scripts/proofs/s7.py <evidence_root>` writes `<root>/proof/S7/` (verdict.md, `1_error_dots.png`, one `2_<clip>_a<k>_fail_strip.jpg` per attempt with failing borders: true frame vs S7's frame, cropped to the lifter). Fresh about 1 min (decoded frames cached in `.scratch/verify/cache/proof-s7/frames-*`), cached seconds. The run's S7 check (`check_pipeline.py`) prints each attempt's S7 - true per border and FAILs only on a regression: a border listed in the reference's `passing` that fails now; a border that newly passes prints "improved", update `passing`.

Flow per commit: `run_clip.sh <clip> <root>` (each clip) -> `base_run.sh <root>` -> `diff_outputs.py <root>` (optional) -> look at the changed stages' images, write `review.md` -> `publish_evidence.sh <root> review.md`.

`review.md`: one section per changed stage, one bullet per shown image (plus `no proof: <reason>` when it has no proof), the clip id and image stem first, a plain-English verdict after the colon, every frame of a `_worst` image named:
```
## S6
- T1 6_filled_worst: f330 purple knee sits under the plate where a knee is; f412 ... 
- T1 6_filled_sheet: ...
## S4 calibration     <- a calibration stage that is also an analyze stage (S1, S4); C3 is just `## C3`
- T5 4_pose_sheet: ...
```
Publish to the PR (after the commit is pushed, so the log's `commit` line names it): `.claude/skills/verify/scripts/publish_evidence.sh <evidence_root> review.md`. `DRY_RUN=1` prints the comment and pushes nothing. The script FAILs before pushing when a shown image has no bullet, a bullet of a `_worst` image misses a frame of its `.worst`, a bullet names no shown image, a section is for a stage that is not shown (stale review), the guide has no section for a shown stage, a new/changed stage has neither a proof nor a `no proof:` line, or a stage changed and the root lacks a log for a test clip T1–T8. The comment: the commit once, a result per clip, a table of every stage (new / changed / identical / absent, with the changed files), then per changed stage in pipeline order its guide text, its proof, and per clip the detail lines from the log, the images (`png`/`jpg` outputs, of an mp4 its `_sheet` and `_worst` with a line `worst frames (from <name>.worst): f461 ...`) each followed by its review bullet. The calibration's stages are their own sections "(calibration, T5)" when changed. Over 4 clips a stage's later clips collapse into `<details>`; over GitHub's 65536 characters more do, and the comment says so. `SHOW_STAGES="S2 C3"` adds stages by name, `all` shows all, in the no-baseline fallback only. No per-file links, one `Files:` link to the root's tree.

Explainer: when the PR text alone is not enough (a new stage, a changed data flow, a new kind of output), make a `/show-me:show-me` page, then `.claude/skills/verify/scripts/screenshot.sh <page.html> <evidence_root>/explain.png` (full-page PNG via the installed Chrome; GitHub shows no HTML and the repo is private, so no link); every image at the top of the root goes into the comment under "Explainer". The script commits the root (without `base/`) to the branch `evidence/pr-<n>` (own history, never merged) and comments on the PR, all pinned to the evidence commit. The checkout and its index are not touched. `.github/workflows/delete-evidence.yml` deletes `evidence/pr-<n>` when the PR closes (the comment text stays; images and links break). Never merge or open a PR from `evidence/*`.

Standards: drive the real pipeline on real clips, not a function in a REPL; no stray writes into `prototype/out/`.

## Isolation
One `run_clip.sh` at a time: it holds `.scratch/verify/.run_clip.lock`, and a second run fails at once naming the first (pid, clip, root). Two runs would share the caches and a root's calibration, and CoreML + CPU contention spoils timings. For several clips, loop them in one shell, one after another. A lock left by a killed run (dead pid) is taken over.

## Cleanup
Nothing to kill. Remove only what you started: background jobs by PID (`kill <pid>` of what you launched, never `pkill python`). Don't delete evidence by hand (base worktrees: `git worktree remove`, never `rm -rf`): `sweep_evidence.sh` (run by the SessionStart hook in `.claude/settings.json`, safe to run by hand, `DRY_RUN=1` only prints) deletes a root under `.scratch/verify/` once its branch (from the log's `commit` line) is neither checked out nor has an open PR, so local evidence goes once the PR is merged or closed, keeps the 3 newest entries per cache dir, and removes base worktrees beyond the 3 newest or that are no open PR's (or the checked-out branch's) merge base. Offline or without `gh` it deletes nothing.

## Maintenance
Feature map: `features/README.md`. Update it with `/maintain-verification-skill`.
