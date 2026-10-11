# Test clips T1–T5 (`vids/test/`)

Short 1-rep clips for fast `/verify` runs. `vids/` is gitignored: rebuild them from `vids/spike/` with the commands below.

All sources: `vids/spike/20261007_*_jiri_v3_*.MOV` (side view, 240 fps, 1920x1080, rotation −90). Keyframes every ~0.983 s, so `-c copy` snaps the start to the keyframe before `-ss`. The real start frame below was found by matching the clip's first decoded frame (`-f framemd5`) against the source.

| Id | Source stem | Covers | `-ss` / `-to` (s) | Real start (src frame) | Frames | Expected |
|---|---|---|---|---|---|---|
| T1 | `20261007_3_…powersnatch_5kg_3rep_success_0deg_right` | normal case, per-commit clip | 3.03 / 8.60 | 728 | 1361 | 1 attempt, power, completed |
| T2 | `20261007_4_…squatsnatch_5kg_3rep_success_0deg_right` | squat type | 2.92 / 8.85 | 701 | 1657 | 1 attempt, squat, completed |
| T3 | `20261007_10_…powersnatch_10kg_3rep_fail-bend-elbows_0deg_right` | failed lift | 3.00 / 8.00 | 720 | 1217 | 1 attempt, failed: elbow_unlocked |
| T4 | `20261007_7_…powersnatch_5kg_3rep_success_0deg_left` | other facing side | 2.86 / 8.02 | 687 | 1458 | 1 attempt, power, completed, side ≠ T1 |
| T5 | `20261007_2_…powersnatch_bar_1rep_success_0deg_right` | calibrate (C1–C3), analyze exit 6 | uncut (remux) | 0 | 3157 | skeleton.json; analyze → exit 6 |

Names: `T<n>_<source stem with 3rep→1rep>_240fps.MOV`. The `_240fps` token stays: the remux rewrites the rate tags and S−1 checks against the token.

Cut points: rep 1 setup − 1 s to overhead_end + 1 s from `prototype/out/<src>/phases_v2.json`. T3 has no reps there (0 found on the source), so it was cut from the plate hub height in `plate.csv` (lift 4.3–6.8 s).

## Rebuild
```
cd vids && mkdir -p test
ffmpeg -ss <start> -to <end> -i spike/<src>.MOV -c copy -map 0 test/<name>
```
Check: `ffprobe -select_streams v:0 -show_entries packet=pts_time` gives uneven deltas (min 0.00375 s, max up to 0.0167 s), same 1920x1080 and rotation −90 as the source.

## Measured (current scripts, `run_clip.sh`, M4, pose lock held)
| Id | Runtime | v1 reps | v2 reps | v1 event shift vs source − offset (frames) |
|---|---|---|---|---|
| T1 | 152 s | 1 | 0 | setup +7, transition −1, catch −3, lockout +16 |
| T2 | 100 s | 1 | 0 | setup 0, transition −3, catch −45, lockout 0 |
| T3 | 81 s | 0 (run fails: no phase_sheet.jpg) | 2 | source has 0 reps too |
| T4 | 85 s | 1 | 0 | setup +16, transition 0, catch −16, lockout +1 |

T1 plays about 30 s in a video player (240 fps slow motion, ~5.7 s real time); its pipeline runtime was 152 s.

## Known issue (fixed in T-B)
Done criterion "events = source − offset (± 1 frame)" fails on the cut clips: v1 events shift by up to 45 frames (T2 catch −45, T1 lockout +16, T4 setup +16 / catch −16), and v2 finds 0 reps on T1, T2 and T4. This is a pipeline bug, not a cut problem; T-B fixes it and re-checks the shift. `src/` unchanged in P0.

Evidence: `.scratch/verify/p0-20261011T084802Z/` (logs, sheets per clip, clip_sheet.jpg).
