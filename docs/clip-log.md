# Clip log — repeatability prototype (#11)

Originals in `vids/` (gitignored, content never edited; renamed from iPhone names on 2026-10-05, see [Camera file names](#camera-file-names)). All: HEVC, 1920x1080, 240 fps (except 20261005_1: 3840x2160, 24 fps), rotation tag -90 (portrait). Camera on lifter's right side. Load "bar + N kg" = one N kg plate each side.

| Clip | Lifter | View | Reps | Load | Frames | Duration | Session* | Variant† | Role |
|---|---|---|---|---|---|---|---|---|---|
| 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg | jiri | side | 1 | bar only | 2943 | 12.3 s | hoodie | power | baseline (no occlusion); contains standing hold (static-pose proxy) |
| 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg | jiri | side | 0 (pull to standing hold, no snatch) | bar + 5 kg | 2553 | 10.6 s | hoodie | — (no snatch) | **static-pose clip**: standing hold, bar at hips, plates (same occlusion as main set) |
| 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg | jiri | side | 1 | bar + 5 kg | 2498 | 10.4 s | hoodie | power | main set |
| 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg | jiri | side | 1 | bar + 5 kg | 2644 | 11.0 s | hoodie | power | main set |
| 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg | jiri | side | 2 | bar + 5 kg | 3953 | 16.5 s | hoodie | power ×2 | main set |
| 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg | jiri | side | 2 | bar + 5 kg | 3837 | 16.0 s | grey tee | power ×2 | main set |
| 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg | jiri | off-axis (right-back) | 1 | bar + 5 kg | 2455 | 10.2 s | hoodie | power | degraded |
| 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg | jiri | off-axis (right-back) | 2 | bar + 5 kg | 4180 | 17.4 s | grey tee | power ×2 | degraded |

\*2026-10-01 session inferred from clothing/lighting (hoodie vs grey tee; 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg/20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg skylight lighting, exposure shift mid-20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg). Confirm.

†Variant from visual check of 0.25 s frame sheets (agent, 2026-10-01), **confirmed by the lifter 2026-10-02**: every rep has a knee dip under the bar but no deep squat catch. The pipeline also reports knee angle at the catch per rep (20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg: 107°, 102°). Spread is only computed within one variant — mixed variants would inflate the catch SD with technique, not model, variation.

2026-10-05 rows (made vs missed set, #20): view, reps, load, variant and outcome are taken from the file names and not yet checked against the video; frames and duration from ffprobe.

Pooled reps: main set 6 side-on plate reps; degraded 3 off-axis plate reps; baseline 1 bar-only rep.

## Rep list (`prototype/out/reps_proposed.csv`)
One row per rep (per lift for the standing-hold clip). Originals are not cut: a rep is a frame range in its clip, and per-rep pose runs only those frames (`extract_pose.py --reps out/reps_proposed.csv`); rests between reps are skipped, frame numbers stay those of the original clip.

| Column | Meaning |
|---|---|
| `start_frame`, `end_frame` | lift-off to bar back on the floor ([start, end), clip frames) |
| `pose_start`, `pose_end` | frames posed: the lift plus padding (1 s each side for the plate hub; 1.5 s before / 2 s after for pose, which finds lifts ~0.4 s late and up to ~0.9 s early) |
| `source` | how the lift was found: plate hub (track passed its check), pose (wrists above the chest on a sparse pass, every 8th frame; every 2nd for the 24 fps clip), or phases.json v1 (bar-only clip) |
| `variant`, `outcome`, `fail_cause` | copied from the file name, **per clip**: correct them per rep |
| `checked` | `no` until someone has looked at the rep; set to `yes` after checking the boundaries and the labels |

Made by `prototype/scripts/find_reps.py` → `prototype/out/reps_proposed.csv`. The rows are proposals, not hand-checked; a checked rep list is deferred to the gate 1 set (#20), with a hub/pose plot per clip in `prototype/out/reps_check/`.

Checks:
- On the 7 clips of 2026-10-01 with a snatch, both the hub and the pose method find the known reps.
- Per-rep pose = full-clip pose: `20261001_3` posed on its rep range only gives bit-identical keypoints from 0.15 s after the range start, and the same v2 phase frames (`prototype/out/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg/rep_pose_check.md`).
- 2026-10-05: the plate track failed its check on every clip tried with the default settings: the camera was further away, so the plate (radius ~96 px) was below the tracker's default minimum (110 px) and it followed the medicine balls behind it (see `recording-protocol.md`). With `track_plate.py --radius 70:140` it works (checked on `20261005_2`; the other clips are not re-run yet). Until then all reps of that session come from pose, and phase definition v2, which needs the hub, is not available for them.

## Model scope
All candidate pose models are run on these clips to compare performance, including ones whose licences block commercial use (see `research/09-pose-model-licensing.md`). Blocked-model results are research-only and must be labelled as such.

## Known limits
- No dedicated static standing clip. Best proxy: standing hold in 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg (plates, same session): **1.42 s, 340 frames, f1151–f1490** (hub height within 2 cm; see `results/14-ladder-and-plate.md`). Secondary: 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg (bar only), overhead lockout holds (quasi-static, includes real sway).
- Main set mixes two sessions (hoodie / grey tee).
- n = 6 reps: clear pass/fail only, not close calls.
- Near plate occludes lower legs at setup/pull in side-on plate clips.

## Camera file names
Original iPhone names, for matching back to the phone library. The `.aae` sidecars (`IMG_O<n>.aae`) were renamed to the same stem. Ladder copies in `vids/ladder/` are `<clip>_<fps>fps.MOV`.

| Clip | Camera file |
|---|---|
| 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg | IMG_4578.MOV |
| 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg | IMG_4579.MOV |
| 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg | IMG_4581.MOV |
| 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg | IMG_4583.MOV |
| 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg | IMG_4584.MOV |
| 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg | IMG_4585.MOV |
| 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg | IMG_4586.MOV |
| 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg | IMG_4587.MOV |
| 20261005_1_jiri_v2_standup_squatsnatch_2rep_success_0deg | jiri | side | 2 | not in name | 799 | 33.3 s | 2026-10-05 | squat | made; 4K 24 fps; name also says standup. **Removed 2026-10-06** (video and out/): 24 fps is too coarse |
| 20261005_2_jiri_v2_powersnatch_5kg_3rep_success_0deg | jiri | side | 3 | bar + 5 kg | 4943 | 24.6 s | 2026-10-05 | power | made |
| 20261005_3_jiri_v2_powersnatch_5kg_3rep_success_0deg | jiri | side | 3 | bar + 5 kg | 4922 | 24.6 s | 2026-10-05 | power | made |
| 20261005_4_jiri_v2_squatsnatch_5kg_3rep_success_0deg | jiri | side | 3 | bar + 5 kg | 5314 | 26.6 s | 2026-10-05 | squat | made |
| 20261005_5_jiri_v2_squatsnatch_5kg_3rep_success_0deg | jiri | side | 3 | bar + 5 kg | 5562 | 27.8 s | 2026-10-05 | squat | made |
| 20261005_6_jiri_v2_powersnatch_10kg_3rep_success_0deg | jiri | side | 3 | bar + 10 kg | 4024 | 20.1 s | 2026-10-05 | power | made |
| 20261005_7_jiri_v2_powersnatch_10kg_3rep_fail_faraway_0deg | jiri | side | 3 | bar + 10 kg | 4790 | 23.9 s | 2026-10-05 | power | missed: bar far away |
| 20261005_8_jiri_v2_powersnatch_10kg_3rep_fail_faraway_0deg | jiri | side | 3 | bar + 10 kg | 5031 | 25.2 s | 2026-10-05 | power | missed: bar far away |
| 20261005_9_jiri_v2_powersnatch_10kg_3rep_fail_not_fast_under_30deg | jiri | off-axis (+30°) | 3 | bar + 10 kg | 5632 | 28.2 s | 2026-10-05 | power | missed: not fast under |
| 20261005_10_jiri_v2_powersnatch_10kg_3rep_fail_not_fast_under_30deg | jiri | off-axis (+30°) | 3 | bar + 10 kg | 3768 | 18.8 s | 2026-10-05 | power | missed: not fast under |
| 20261005_11_jiri_v2_powersnatch_5kg_3rep_success_30deg | jiri | off-axis (+30°) | 3 | bar + 5 kg | 4637 | 23.2 s | 2026-10-05 | power | made |
| 20261005_12_jiri_v2_powersnatch_5kg_3rep_fail_faraway_30deg | jiri | off-axis (+30°) | 3 | bar + 5 kg | 4718 | 23.6 s | 2026-10-05 | power | missed: bar far away |
| 20261005_13_jiri_v2_powersnatch_5kg_3rep_fail_not_fast_under_30deg | jiri | off-axis (+30°) | 3 | bar + 5 kg | 3016 | 15.1 s | 2026-10-05 | power | missed: not fast under |
| 20261005_14_vladka_v1_powersnatch_5kg_3rep_success_0deg | vladka | side | 3 | bar + 5 kg | 2648 | 13.2 s | 2026-10-05 | power | made; second lifter |
| 20261005_1_jiri_v2_standup_squatsnatch_2rep_success_0deg | IMG_4602.MOV |
| 20261005_2_jiri_v2_powersnatch_5kg_3rep_success_0deg | IMG_4603.MOV |
| 20261005_3_jiri_v2_powersnatch_5kg_3rep_success_0deg | IMG_4604.MOV |
| 20261005_4_jiri_v2_squatsnatch_5kg_3rep_success_0deg | IMG_4605.MOV |
| 20261005_5_jiri_v2_squatsnatch_5kg_3rep_success_0deg | IMG_4606.MOV |
| 20261005_6_jiri_v2_powersnatch_10kg_3rep_success_0deg | IMG_4607.MOV |
| 20261005_7_jiri_v2_powersnatch_10kg_3rep_fail_faraway_0deg | IMG_4608.MOV |
| 20261005_8_jiri_v2_powersnatch_10kg_3rep_fail_faraway_0deg | IMG_4609.MOV |
| 20261005_9_jiri_v2_powersnatch_10kg_3rep_fail_not_fast_under_30deg | IMG_4610.MOV |
| 20261005_10_jiri_v2_powersnatch_10kg_3rep_fail_not_fast_under_30deg | IMG_4612.MOV |
| 20261005_11_jiri_v2_powersnatch_5kg_3rep_success_30deg | IMG_4613.MOV |
| 20261005_12_jiri_v2_powersnatch_5kg_3rep_fail_faraway_30deg | IMG_4615.MOV |
| 20261005_13_jiri_v2_powersnatch_5kg_3rep_fail_not_fast_under_30deg | IMG_4616.MOV |
| 20261005_14_vladka_v1_powersnatch_5kg_3rep_success_0deg | IMG_4617.MOV |
