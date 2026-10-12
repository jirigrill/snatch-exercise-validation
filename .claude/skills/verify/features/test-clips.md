# Test clips T1–T7 (`vids/test/`)

Short 1-rep clips for fast `/verify` runs. `vids/` is gitignored: rebuild them from `vids/spike/` (T1–T5) and `vids/ladder/` (T6–T7) with the commands below.

T1–T5 sources: `vids/spike/20261007_*_jiri_v3_*.MOV` (side view, 240 fps, 1920x1080, rotation −90). T6–T7 sources: `vids/ladder/20261001_*_60fps.MOV` (60 fps; cover the S−1 rate checks). Keyframes every ~0.983 s, so `-c copy` snaps the start to the keyframe before `-ss`. The real start frame below was found by matching the clip's first decoded frame (`-f framemd5`) against the source.

| Id | Source stem | Covers | `-ss` / `-to` (s) | Real start (src frame) | Frames | Expected |
|---|---|---|---|---|---|---|
| T1 | `20261007_3_…powersnatch_5kg_3rep_success_0deg_right` | normal case, per-commit clip | 3.03 / 8.60 | 728 | 1361 | 1 attempt, power, completed |
| T2 | `20261007_4_…squatsnatch_5kg_3rep_success_0deg_right` | squat type | 2.92 / 8.85 | 701 | 1657 | 1 attempt, squat, completed |
| T3 | `20261007_10_…powersnatch_10kg_3rep_fail-bend-elbows_0deg_right` | failed lift | 3.00 / 8.00 | 720 | 1217 | 1 attempt, failed: elbow_unlocked |
| T4 | `20261007_7_…powersnatch_5kg_3rep_success_0deg_left` | other facing side | 2.86 / 8.02 | 687 | 1458 | 1 attempt, power, completed, side ≠ T1 |
| T5 | `20261007_2_…powersnatch_bar_1rep_success_0deg_right` | calibrate (C1–C3), S3 exit 6 | uncut (remux) | 0 | 3157 | skeleton.json; S3 → exit 6 |
| T6 | `20261001_3_…powersnatch_5kg_1rep_success_0deg_60fps` | 60 fps snatch, S−1 rate check | 2.58 / 6.68 | 155 | 248 | 1 attempt, completed |
| T7 | `20261001_2_…standup_5kg_1rep_success_0deg_60fps` | 60 fps expected failure | 1.50 / 6.50 | 90 | 302 | 0 reps |

Names: `T<n>_<source stem with 3rep→1rep>_240fps.MOV`; T6/T7: `T<n>_<source stem>_60fps.MOV`. The `_240fps` token stays: the remux rewrites the rate tags and S−1 checks against the token.

Cut points: rep 1 setup − 1 s to overhead_end + 1 s from `prototype/out/<src>/phases_v2.json`. T3 has no reps there (0 found on the source), so it was cut from the plate hub height in `plate.csv` (lift 4.3–6.8 s). T6: known source phases 215/232/276/341 (setup/transition/catch/lockout), cut setup − 1 s to lockout + 1 s. T7: ~5 s around the movement, picked from 1 fps / 2 fps sampled frames (stand-up at ~2–5 s).

## Rebuild
```
cd vids && mkdir -p test
ffmpeg -ss <start> -to <end> -i spike/<src>.MOV -c copy -tag:v hvc1 -map 0 test/<name>
```
Apple players only play HEVC tagged `hvc1`; the 60 fps ladder sources carry `hev1`, so the cut clips need the re-tag.
Check: `codec_tag_string` is `hvc1` for all 7 clips; `ffprobe -select_streams v:0 -show_entries packet=pts_time` gives uneven deltas (min 0.00375 s, max up to 0.0167 s), same 1920x1080 and rotation −90 as the source.
