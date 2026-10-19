# B: front stages S1, S4, S2, S3

Order: S1 → S4 (whole clip) → C3 calibrate (C-skeleton.md) → S2 → S3 (S4 switches to attempt windows).

Prep (frame times, Halpe-26 + facing, cut-clip fix) is on main via #52. Existing `raw_pose.npz` files need a rerun for Halpe-26.

## Stages (logic moves from scripts/* into snatch/stages/*)
| Stage | Source | Out | Overlay |
|---|---|---|---|
| S1 person | `scripts/extract_person.py` | person.npz (+t) | 1_person.mp4 (overlay.render) |
| S4 pose | `scripts/extract_pose.py --reps` | raw_pose.npz (26 kp, ranges, t), facing.json | 4_pose.mp4 |
| S2 plate | `scripts/track_plate.py` | plate.npz (found, passed, t), plate.csv, bar_path.png, plate_check.jpg | 2_plate.mp4 (**new**: outline + hub + trail, orange when the check fails) |
| S3 attempts | `scripts/find_reps.py` / reps.py | attempts.json (incl. failed attempts) | 5_attempts.mp4 |

- S2 stops (spec): found < 90 % of the frames where the plate moves (re-checked in attempt windows after S3), or px_per_m varies > 10 % → exit 4; no plate anywhere → exit 6 (bar-only clip, use `--calibrate`). The old track_plate.py checks (found < 90 %, travel < 0.4 m, jumps) only set `passed` = false (orange overlay), no stop.
- S4 (own PR): poses the whole clip, as C2 does in calibrate mode. Facing (both feet vote) has no 2/3 majority → exit 8. Near side follows from facing (right → r); the higher-scoring leg must agree, else exit 8. Facing goes to facing.json {facing, votes, leg_scores}, not clip.json (S1/S2/S3 hash clip.json).
- Missing side in skeleton.json → exit 2: lands with C3 (before that, run_clip.sh only has a `{}` placeholder skeleton).
- S3 PR: S4 then poses only attempt windows ± 1 s; calibrate (no attempts) stays whole clip.
- Pass `facing` into `sagittal_angles`.
- Feet crop risk (S3 PR, when windows arrive): YOLOX boxes stop at the plate in setup (T1: ankle below box in 25 % of frames, toes p95 0.24 box-h). `pose.track_box` adds the previous pose extent, but each window starts with the box alone (T1 f0 ankle score 0.52, f160 0.69, f320 0.83). Check: window-only vs the S4 whole-clip poses on T1–T4, ankle/heel/toe diff + scores in each window's first second. If off: extend the first crop down to the floor (high percentile of box bottoms) or start each window a few frames earlier.
- S1 ∥ S2 parallel: optional. Sequential is fine for now; write it down as a todo.

## Tests (only if a clip cannot cover it)
- Each stage: a fixture npz in → expected files + exit code; exit 4 / 6 / 8 cases on synthetic data.

## Done when
On the live clips, attempts.json matches the current find_reps result (rep count) and 4_pose.mp4 looks right by eye.
