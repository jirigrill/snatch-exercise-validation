# Spike analyses (D1, D2, body height, knee skeleton)

## Sub-features
All scripts live in `prototype/scripts/studies/`.
- D2 early arm bend: `scripts/studies/arm_bend.py label=out/<clip> …` -> out/<clip>/arm_bend.json, out/d2_arm_bend/{reps.csv,curves.png,summary.md}
- Body height: `scripts/studies/body_height.py ../vids/spike/<clip>.MOV out/<clip> [--side r|l]` -> height.json, height_sheet.jpg
- D1 camera views: `scripts/studies/d1_views.py [--v1|--v2] [--near] out/<clip> …` -> d1_views.json, out/d1_views.md
- Knee skeleton fill-in: `scripts/studies/skeleton_validate.py [--seed 0]` -> out/skeleton/validate.{json,md}

## How to get to it (user POV)
Analyst compares views/clips from the 2026-10-07 spike (`vids/spike/`, results in `docs/results/33-36`).

## Driving it with the shell harness
These read a finished pipeline dir `out/<clip>/` (raw_pose.npz, plate.npz). They are not part of `run_clip.sh`. Run `run_clip.sh` on a `vids/spike/` clip first (240 fps: slow), or point them at the committed `prototype/out/<clip>` dirs; they **write into `out/<clip>`**, so copy the dir to a scratch location and run from a copy of `prototype/` when you must not touch committed results, or verify with `git status`/`git diff prototype/out` that outputs are unchanged.
Proof: output file exists, numbers match `docs/results/3x-*.md` for the same clips (e.g. D2 summary vs `34-d2-arm-bend.md`).

## Gotchas
- Clip names are hard-coded in places (`skeleton_validate.py` needs the 20261007_1 and _2 bar-only clips' raw_pose.npz).
- `arm_bend.py` reads clips from `../vids/spike` or `../vids`.
