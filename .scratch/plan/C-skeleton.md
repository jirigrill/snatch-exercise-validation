# PR C: calibrate (C1–C3), S5 scale, S6 fill

No reuse from open PRs. Source code was in `src/snatch/studies/` and `scripts/studies/skeleton_*.py`, deleted with v1 in #68: restore what S5/S6 need with `git show 6469c5b:prototype/<path>`; findings are in `docs/results/35-body-height.md` and `36-skeleton-fill.md`.

## Calibrate mode
`pipeline.py --calibrate bar.MOV --athlete jiri`
- C1 = S1 stage, C2 = S4 stage (same code), outputs in `out/<bar clip>/`.
- C3 fit skeleton: move segment lengths + wrist offset out of `studies/skeleton.py` (+ `skeleton_wrist.py`, `segment_lengths.py`) into `snatch/skeleton.py`. Writes `athletes/<id>/skeleton.json` (per side) + `calibration_overlay.mp4`.
- `--only C3` refits without rerunning pose.

## S5 clip scale (new: `snatch/scale.py`)
- Idea from `scripts/studies/skeleton_loaded.py`.
- Standing window: per attempt, longest ≥ 0.3 s with knee ≥ 165° (= `skeleton.STAND_DEG`, the calibration's standing rule), hip + ankle visible and not inside the plate outline, searched over every posed frame of the attempt windows (decided in #67: the padding is the setup crouch before liftoff and mostly missing after, so the standing frames are the overhead hold). Factor = median over all windows' frames.
- No hip-still rule (decided 2026-10-19: first run had 1 %, T2's hip sways ~5 % in the hold while the legs are straight, and sway barely changes hip–ankle; `spread` shows an unsteady leg length). First-run knee limit 170° found nothing on T3 (p99 168°).
- Else visible-knee frames (kept for a failed lift that never stands up): hip, knee, ankle seen and none inside the plate outline (`plate.npz`, `ellipse_dist`); the first run used the score only and took the plate hub for the ankle on T2.
- Clips from another or unknown camera distance must work (decided 2026-10-19): no limit on the factor itself. The guard against another person is a proportions check, which doesn't depend on distance: thigh / shank on the frames used vs the skeleton's thigh / shank at the same d/d_ref, off by > 10 % (placeholder) → exit 5.
- Neither method has enough frames → `method: none`, factor null, no stop (decided 2026-10-19). T7 (standup): the plate covers the hip on every straight-leg frame; it must still reach S8 (no_overhead needs only the plate track). S6 fills nothing then and marks hidden joints hidden; S8 treats hidden like filled (low_confidence). No overlay for method none, or one saying so.
- Out: `scale.json` {factor, method, n_frames, spread, frames, thigh_shank, thigh_shank_cal}; overlay `5_scale.jpg`.

### S5 done when (verify, `check_pipeline.py` S5 check)
1. Frames: `method = standing` on T1, T2, T6 and T8, with a window in each attempt (T8: both). T3 (failed lift, knee ≥ 165° for only 0.025 s): `visible_knee`, the case the fallback is for. T7: `method: none`, run goes on. Every frame used, recomputed in the check from raw_pose + plate.npz: knee ≥ 165° (standing) and near hip and ankle (visible_knee: also knee) not inside the plate outline. Changed 2026-10-19 from "plate above the head": the window runs on while the bar is lowered with the legs straight, which the factor doesn't mind (spread 0.5–1.3 %). T4 stops at `side` (exit 2) before S5.
2. Plate ratio: factor / median plate px/m over the frames used within ±5 % of T1's for clips from T1's session (date prefix 20261007: T2, T3, T8); other sessions (T6, T7) only report it. Decided 2026-10-19: the plate sits nearer the camera than the body, so a closer camera lowers the ratio (geometry from 35-body-height's k = 0.829: −4 to −12 % at ~1.6× closer; T6 −8.1 %, T7 −8.0 %). T6 must still reach S5 with method standing; the proof for another distance is S6's hide-a-seen-knee test on T6. Multi-clip root only; per-commit T1 reports the ratio.
3. Proportions: thigh_shank within 10 % of thigh_shank_cal on every clip that reaches S5.
4. Unit tests: visible-knee fallback (R3), exit 5 on proportions off (R1); no frames → method none is covered by T7.
5. Eye review of `5_scale.jpg`: the hip–ankle line sits on the hip and ankle, legs straight.
- If T6 stops before S5 (facing not in the filename, S4 `side`), stop and report: the unknown-distance check then needs another clip.
- The hide-a-visible-knee test (hide a seen knee, fill it, compare) is S6's done check, not S5's.

## S6 fill hidden joints
- Restore `fill_hidden` from `studies/skeleton.py` (`two_circle_knee`, `knee_gain`, `ellipse_dist` are already in `snatch/`; `wrist_from_hub` not: knee only, see decisions).
- Inputs: raw_pose, plate, scale, skeleton. Out: `pose.npz` (hybrid + filled mask); overlay `6_filled.mp4`.
- Done check (tests skeleton × S5 factor × fill together): on frames where the knee is seen, hide it, fill it, compare with the seen knee (px error, knee-angle error). Run on T1–T3, T6 and T8; T6 covers the other camera distance.
- Stage hash includes skeleton.json + scale.json (hook from A).
- scale.json `method: none` (T7): fill nothing, mark hidden joints hidden in the mask.

### S6 decisions (2026-10-19)
- Frame count first (S1–S5 on T1–T3, T6, T8, 2026-10-19): visible-knee frames at the transition are too few to gate on (T6: 2, T1: 13–37), and the deep catch (knee < 90°) is no proxy (rebuilt knee 4–10 cm too high there; never hidden, so never filled). Hidden knees sit at 95–150° (median 128°). With S5's one factor the rebuilt knee at 90–150° was 2–4 cm off on T1's session and 4–6 cm on T6: one factor scales the leg but can't fix its proportions (T6 thigh/shank 5 % off the skeleton's).
- Fix: S5 also measures a thigh and a shank multiplier (on top of the factor) from the clip's visible-knee frames at 90–150°; fewer than 20 such frames → both 1 (`segment_source: factor_only`). Held-out test: T1 2.3→1.5 cm, T2 2.9→2.4, T3 3.1→2.5, T6 6.2→1.8, T8 2.3→1.7.
- Pass gate (done check): visible knee at 90–150° outside the plate, inside S6's fill condition (circles meet, gain ≤ 2), two-fold hold-out by time (multipliers fitted on one half, knee rebuilt on the other). FAIL above 3 cm median per clip; target 2 cm and the knee-angle error reported per clip; under 40 frames: reported, not gated. px → cm: body 352.8 px/m (doc 35, T5's session) × factor. Same gate on T6 as on T1–T3, T8.
- Hidden: near hip/knee/ankle inside the S2 plate ellipse with a 10 % margin (`ellipse_dist < 1.1`, named constant).
- Knee only. `wrist_from_hub` is not restored in S6; wrist fill is a later plan item if S7/S8 need a wrist angle.
- Re-bends: per attempt, start to bar peak, the hybrid knee may have no more ≥ 3° dips than RTMPose's knee (doc 36: RTMPose invents them behind the plate). Loaded clips have no truth behind the plate, so RTMPose is the comparison.
- Airborne frames (T5 f1695–1698, shank +6 % on toes): report the reading only, no gate.
- `6_filled.mp4` (spec colours): plate outline, RTMPose near leg grey, filled knee purple, hidden-not-filled joints a yellow-orange ring, a legend on the frame.
- Open: T2 (squat) and T3 (10 kg) stay at ~2.5 cm with the multipliers; chase later if S7/S8 disagreements point at the knee.

## Cleanup
Restored functions go straight into `snatch/` (no `studies/` any more); restore test_fill_hidden_switches_smoothly (test_skeleton.py at 6469c5b) with S6.

## Tests (only if a clip cannot cover it)
- Move the existing `test_skeleton.py` / `test_views.py` cases along with the code.
- New: scale standing vs knee fallback, exit 5 (no frames; proportions off), a filled mask that is correct on a synthetic occlusion.

## Done when
A bar-only clip → skeleton.json. A loaded clip → pose.npz whose filled knee matches the results in 36-skeleton-fill (gate: S6 decisions above).
