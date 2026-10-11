---
name: verify
description: Drive and prove the snatch-exercise-validation prototype (Python CLI pipeline in prototype/: video -> RTMPose skeleton -> plate/bar track -> joint angles and snatch phases). Use after changing anything under prototype/src or prototype/scripts, or to check a pipeline output before trusting it.
---

# Verify: snatch pipeline (`prototype/`)

Surface: **CLI pipeline, no server, no UI.** A user runs `uv run python scripts/<step>.py <clip.MOV> out/<clip>` and reads files (npz, json, csv, jpg, png, mp4). All commands run from `prototype/` (uv project, Python 3.12). Paths below are relative to the repo root unless stated. Only the Mac is supported (pose runs on CoreML).

## Launch
Nothing to start. One-time: `cd prototype && uv sync`. Models (`~/.cache/rtmlib/hub/checkpoints`: RTMPose-x 189 MB, YOLOX-x 378 MB) download on first pose run.

Ready = doctor passes. Teardown = none (each step exits).

## Doctor (read-only, run first)
```
.claude/skills/verify/scripts/doctor.sh
```
Checks uv, `.venv`, imports, both ONNX models, ffprobe, clips in `vids/ladder/`, CoreML provider. Any `FAIL` -> fix before driving. `vids/` is gitignored and not in a fresh clone: no clips = nothing to drive except `pytest`.

## Drive
Fast gate (3 s, no video): `cd prototype && uv run pytest -q` and `uv run pyright` (baseline on main: 56 errors, so compare counts before/after, don't expect 0).

End-to-end on one clip (~50 s for the default 60 fps clip, 625 frames):
```
.claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
```
Runs person -> pose -> plate -> analyze -> compare into `.scratch/verify/<UTC ts>/<clip>/` (never `prototype/out/`, which holds committed results), asserts outputs exist and at least one rep was found, prints `OK evidence: <dir>`. person.npz/raw_pose.npz come from `.scratch/verify/cache/<clip>/<key>/` when the clip and `person.py`, `pose.py`, `video.py`, `extract_person.py`, `extract_pose.py` are unchanged (log says `person+pose: cache`); `VERIFY_NO_CACHE=1` forces a rerun. `--det-every 96` was measured against 24 on T1 at 240 fps: boxes differ p95 50 px (max 26% of box height) during the lift, so the default stays 24.

Pipeline v2 runner (S-1 probe, S0 athlete check so far): `uv run python scripts/pipeline.py <clip> --athlete <id> [--height <m>] --out <evidence>/<clip> --athletes <evidence>/athletes`. Exit 2 = no skeleton, 7 = no height, 3 = bad clip, 9 = missing input. Always pass `--out` and `--athletes` under the evidence root, and look at `overlays/0_clip_sheet.jpg`.

Step order and what each reads/writes (all `uv run python scripts/…` from `prototype/`):

| Step | Script | Needs | Writes |
|---|---|---|---|
| 0 | `extract_person.py <clip> <out>` | clip | person.npz (YOLOX box, every 24th frame) |
| 1 | `extract_pose.py <clip> <out>` | person.npz | raw_pose.npz |
| 2 | `track_plate.py <clip> <out> [ellipse] [--radius LO:HI]` | clip | plate.npz, plate_check.jpg, bar_path.png |
| 3 | `analyze.py <clip> <out>` | raw_pose, plate | angles.csv, phases.json, phase_sheet.jpg, overlay.mp4 |
| 4 | `compare_phases.py <out>` | raw_pose, plate | phases_v2.json, phases_v1_v2.md |

Plate options depend on the clip name (see `prototype/scripts/run_all.sh`): `ellipse` for 30deg/45deg, `--radius 70:140` for 20261005_* and 20261007_*_0deg_*. Bar-only clips (`_bar_`) have no plate: skip 2 and 4. `scripts/run_all.sh` batches all clips into `prototype/out/` and **writes there**; don't use it for verification unless asked.

Clip choice: `vids/ladder/*_60fps.MOV` (about 50 s each) for proofs; 240 fps clips in `vids/` and `vids/spike/` take minutes to an hour (detector ~0.4 s per detected frame on CPU). Per-feature recipes: `features/README.md`.

## Evidence
Per proof keep, under `.scratch/verify/<ts>/<clip>/` (gitignored, survives cleanup):
- the run log (`<clip>.log`) and the `OK evidence:` line;
- **look at** `phase_sheet.jpg` (skeleton sits on the lifter at setup/transition/catch/lockout), `plate_check.jpg` (outline on the near plate), `bar_path.png`; open them, an existing file is not proof;
- `phases.json` rep count vs the clip name (`_1rep_`, `_3rep_`), phases in order setup < transition < catch < lockout;
- for a code change: same clip before/after (`git stash` or a worktree) and diff `phases.json`, `angles.csv`; any diff must be explained.

Standards: drive the real scripts on real clips, not a function in a REPL; check side effects (files written, no stray writes into `prototype/out/`: `git status --porcelain prototype/out` must be empty after a run). Reference numbers for 20261001_3 at 60 fps: 1 rep, setup 215, transition 232, catch 276, lockout 341, vertical travel 1.68 m.

## Isolation
Safe to run side by side: each run has its own evidence dir. Don't run two pose extractions at once on the same machine for timing claims (CoreML + CPU contention). Never write into `prototype/out/<clip>` for an existing clip: it holds committed results.

## Cleanup
Nothing to kill. Remove only what you started: partial files (`raw_pose_partial.npz`) in your own evidence dir, background jobs by PID (`kill <pid>` of what you launched, never `pkill python`). Do not delete `.scratch/verify/`; that is the proof.

## Maintenance
Feature map: `features/README.md`. Update it with `/maintain-verification-skill`.
