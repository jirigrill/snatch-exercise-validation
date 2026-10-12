# Pose and phases

## Sub-features
- Lifter box (YOLOX) -> person.npz
- 17-keypoint pose (RTMPose-x) -> raw_pose.npz
- Sagittal joint angles -> angles.csv, angles.png
- Phases v1 (wrist height) -> phases.json; v2 (plate hub height) -> phases_v2.json
- Review images: phase_sheet.jpg, grabs/, overlay.mp4

## How to get to it (user POV)
A lifter films a side-on snatch (`vids/<date>_<n>_<who>_<variant>_<load>_<N>rep_<outcome>_<angle>.MOV`); the analyst runs the scripts on it and reads phase_sheet.jpg.

## Driving it with the shell harness
Old scripts, driven by hand (`run_clip.sh` drives pipeline v2 only; these move into v2 stages): `extract_person.py` → `extract_pose.py` → `track_plate.py` → `analyze.py` → `compare_phases.py`, each `<clip> <evidence dir>` from `prototype/`.
Proof: `OK evidence:` line; phases.json has `N` reps matching the clip name, events ordered setup < transition < catch < lockout; phase_sheet.jpg skeleton on the lifter in all 4 columns; `compare_phases.py` table shows v1/v2 transition, catch, lockout within a few frames.

## Gotchas
- `extract_pose.py` needs person.npz first.
- 240 fps clips: detector dominates (up to ~50 min). Use `--det-every` or the ladder clips.
- Phone video is rotated: ClipInfo shows 1080x1920 rotation -90; the code handles it, don't rotate yourself.
- analyze.py `spread` argument is only valid for 20261001_5_..._0deg.
