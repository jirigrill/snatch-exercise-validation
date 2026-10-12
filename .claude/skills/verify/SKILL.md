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
Checks uv, `.venv`, imports, both ONNX models, ffprobe, test clips T1–T7 in `vids/test/`, CoreML provider. Any `FAIL` -> fix before driving. `vids/` is gitignored and not in a fresh clone: no clips = nothing to drive except `pytest`.

## Drive
Fast gate (3 s, no video): `cd prototype && uv run pytest -q` and `uv run pyright` (baseline on main: 56 errors, so compare counts before/after, don't expect 0).

End-to-end: pipeline v2 (`scripts/pipeline.py`, spec `docs/pipeline-v2.html`) on one clip (~50 s on T1):
```
.claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
```
Default clip `vids/test/T1_*.MOV`, default root `.scratch/verify/<UTC ts>/`. Writes `<root>/<clip>/` (pipeline outputs), `<root>/<clip>.log` and a placeholder athlete `verify` (`{}` skeleton.json until C3 calibrate exists, height 1.73 m) in `<root>/athletes/`. On a fresh `<root>/<clip>/` it runs `pipeline.py` three times and checks each run with `scripts/check_pipeline.py`:

| Run | Command | Expected states |
|---|---|---|
| first | all stages | every stage `done` |
| rerun | the same again | hashed stages `skipped`, S0 `done` |
| only | `--only <last stage>` | the last stage `done`, S0 `done`, the others `up_to_date` |

Each check: exit 0, `pipeline_status.json` status `ok`, stages in the order of `snatch.stages.STAGES`, every stage output non-empty, and after the first run each stage's content check (`CHECKS` in `check_pipeline.py`: S-1 frame times vs clip.json; S1 box on every frame, `t` = frame_times.npy, lifter found on ≥ 90 % of detector runs). Last, `git status --porcelain prototype/out` must be empty. Prints `OK evidence: <dir>`, exit 0; anything else is `FAIL`, exit 1. No cache: every call reruns.

Stages today: S-1 probe, S0 athlete check, S1 person. Pipeline exits: 2 = no skeleton, 7 = no height, 3 = bad clip, 9 = missing input.

Adding a stage: the stage goes into `snatch.stages.STAGES`; `run_clip.sh` drives it with no edit. Add its content check to `CHECKS` in `check_pipeline.py` when there is more to check than its files existing. A stage that stops a clip by design (S3 exit 6 on a bar-only clip, S2 exit 8) needs an expected stop per clip in `run_clip.sh`; none exists yet.

Manual run: `uv run python scripts/pipeline.py <clip> --athlete <id> [--height <m>] --out <evidence>/<clip> --athletes <evidence>/athletes [--only S | --from S] [--force]`. Always pass `--out` and `--athletes` under the evidence root.

### Levels
- **Per commit to a branch/PR:** `pytest -q` + `pyright` (count ≤ baseline) + `run_clip.sh` on T1, and look at the overlays.
- **Per PR:** `run_clip.sh` on T1–T7 (T5 bar-only, T6/T7 60 fps). Before/after vs the parent branch when a stage's outputs change.

Test clips T1–T7 (`vids/test/`): what each covers and how to rebuild them in [features/test-clips.md](features/test-clips.md). Doctor warns when they are missing. 240 fps clips in `vids/` and `vids/spike/` take minutes to an hour (detector ~0.4 s per detected frame on CPU). Per-feature recipes: `features/README.md`.

## Evidence
Per proof keep, under `.scratch/verify/<ts>/` (gitignored, survives cleanup):
- the run log (`<clip>.log`, the three check lines) and the `OK evidence:` line;
- **look at** the overlays in `<clip>/overlays/`: `0_clip_sheet.jpg` (the clip's frames), `1_person.mp4` (box on the lifter in every phase; thin = interpolated, red = across a missed detection). Open them, an existing file is not proof;
- for a code change that changes a stage's outputs: same clip before/after (`git stash` or a worktree), diff the outputs; any diff must be explained.

Standards: drive the real pipeline on real clips, not a function in a REPL; no stray writes into `prototype/out/`.

## Isolation
Safe to run side by side: each run has its own evidence dir. Don't run two detector/pose runs at once on the same machine for timing claims (CoreML + CPU contention). Never write into `prototype/out/<clip>` for an existing clip: it holds committed results.

## Cleanup
Nothing to kill. Remove only what you started: background jobs by PID (`kill <pid>` of what you launched, never `pkill python`). Do not delete `.scratch/verify/`; that is the proof.

## Maintenance
Feature map: `features/README.md`. Update it with `/maintain-verification-skill`.
