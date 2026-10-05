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
| 20261005_1_jiri_v2_standup_squatsnatch_2rep_success_0deg | jiri | side | 2 | not in name | 799 | 33.3 s | 2026-10-05 | squat | made; 4K 24 fps; name also says standup |
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
