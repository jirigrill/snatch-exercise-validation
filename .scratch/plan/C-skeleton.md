# PR C: calibrate (C1–C3), S5 scale, S6 fill

No reuse from open PRs. Source code was in `src/snatch/studies/` and `scripts/studies/skeleton_*.py`, deleted with v1 in #68: restore what S5/S6 need with `git show 6469c5b:prototype/<path>`; findings are in `docs/results/35-body-height.md` and `36-skeleton-fill.md`.

## Calibrate mode
`pipeline.py --calibrate bar.MOV --athlete jiri`
- C1 = S1 stage, C2 = S4 stage (same code), outputs in `out/<bar clip>/`.
- C3 fit skeleton: move segment lengths + wrist offset out of `studies/skeleton.py` (+ `skeleton_wrist.py`, `segment_lengths.py`) into `snatch/skeleton.py`. Writes `athletes/<id>/skeleton.json` (per side) + `calibration_overlay.mp4`.
- `--only C3` refits without rerunning pose.

## S5 clip scale (new: `snatch/scale.py`)
- Idea from `scripts/studies/skeleton_loaded.py`.
- Standing window: longest ≥ 0.3 s with knee ≥ 170°, hip + ankle visible, hip still, searched over every posed frame of the attempt windows (decided in #67: the padding is the setup crouch before liftoff and mostly missing after, so the standing frames are the overhead hold). Else visible-knee frames.
- Check: the standing window lands in the overhead hold on T1–T4, T6 and T8 (both attempts), and T2 (squat) has a long enough hold after the recovery.
- Factor more than 15 % off the calibration → exit 5.
- Out: `scale.json`; overlay `4a_scale.jpg`.

## S6 fill hidden joints
- Move `two_circle_knee`, `knee_gain`, `fill_hidden`, `wrist_from_hub` from `studies/skeleton.py`, and `ellipse_dist` from `studies/views.py`.
- Inputs: raw_pose, plate, scale, skeleton. Out: `pose.npz` (hybrid + filled mask); overlay `4_filled.mp4`.
- Stage hash includes skeleton.json + scale.json (hook from A).

## Cleanup
Restored functions go straight into `snatch/` (no `studies/` any more); restore test_fill_hidden_switches_smoothly (test_skeleton.py at 6469c5b) with S6.

## Tests (only if a clip cannot cover it)
- Move the existing `test_skeleton.py` / `test_views.py` cases along with the code.
- New: scale standing vs knee fallback, exit 5, a filled mask that is correct on a synthetic occlusion.

## Done when
A bar-only clip → skeleton.json. A loaded clip → pose.npz whose filled knee matches the results in 36-skeleton-fill.
