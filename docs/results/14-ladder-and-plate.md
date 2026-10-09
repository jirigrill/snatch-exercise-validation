# 14 — Frame-rate ladder and plate tracking

Ticket: [#14](https://github.com/jirigrill/snatch-exercise-validation/issues/14) (parent [#11](https://github.com/jirigrill/snatch-exercise-validation/issues/11)). Run 2026-10-02.

**Bottom line.**
- **Ladder:** all 24 files (8 clips × 120/60/30 fps) are built. Each is checked frame by frame and is pixel-identical to every 2nd/4th/8th frame of its 240 fps original. The originals are untouched.
- **Plate:** the near plate is tracked as an object in all 7 plate clips. **Revised 2026-10-02:** the first outline fit was visibly off the rim in many frames (see §2, "Correction"). After the fix, the 5 side-on clips are found in 100% of frames with the outline on the rim and hub jitter 0.7–1.6 px. **The 2 off-axis clips (20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg, 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg) are not reliable** on the floor. That is accepted for now, and they are phased with v1 in #15 (§4).
- **Hold:** the standing hold in 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg is **1.42 s (340 frames, f1151–f1490)**.
- **Phase definition v2** (hub height in place of wrist height, plus the v2.1 transition rule chosen by the lifter after seeing 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg) is written down and frozen. On 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg it moves **setup ~0.3 s earlier** (v1 was late, see below). Transition, catch and lockout land on the same frames as v1.

Code: `prototype/src/snatch/{ladder,plate}.py`, `prototype/scripts/{track_plate,compare_phases}.py`, `prototype/scripts/studies/{build_ladder,measure_hold}.py`.

## 1. Frame-rate ladder

Ladder frame k is original frame k × step (step 2/4/8), counted from frame 0 in display order. Pose indices therefore map back by multiplication. Files: `vids/ladder/<clip>_<fps>fps.MOV` (gitignored, 6.5 GB). Report: `prototype/out/ladder.json`.

**No re-encoding where none is needed.** iPhone 240 fps HEVC is coded in 4 temporal sub-layers (tid 0–3). Dropping all NAL units above a tid leaves a legal stream that decodes without changing any pixel. Where a sub-layer is exactly every Nth frame, its original packets are copied with their original timestamps. Where it is not, the chosen frames are re-encoded **losslessly** (x265 `lossless=1`). Both paths keep the rotation tag (−90°).

**Deviation from the ticket's wording:** the 30 fps files (all clips) and 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg/20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg at 120 fps are re-encoded, not cut from the original bitstream. Exact every-8th sampling cannot be cut from these streams. The re-encode is lossless and verified pixel-identical, so the intent ("no change to pixels") holds.

| Rate | Method | Clips |
|---|---|---|
| 120 fps | sub-layer tid ≤ 2 copy | 6 |
| 120 fps | lossless re-encode: the sub-layer copy decoded differently (the dropped trailing frame was a reference) and was caught by the check | 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg |
| 60 fps | sub-layer tid ≤ 1 copy | all 8 |
| 30 fps | lossless re-encode: the tid-0 layer gains an extra frame at each CRA (every ~236 frames), so its step is 8 frames with a 4-frame step at each CRA, not every 8th | all 8 |

Two details make the copies valid:
- Many clips code their last frame in a low layer. Such extra frames after the last wanted one are dropped.
- Every file is verified: MD5 of each decoded, rotated frame (same decoder as the pose run) equals the original's frame k × step.

| Clip | 240 fps frames | 120 | 60 | 30 | Pixel-identical |
|---|---|---|---|---|---|
| 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg | 2943 | 1472 | 736 | 368 | ✓ ✓ ✓ |
| 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg | 2553 | 1277 | 639 | 320 | ✓ ✓ ✓ |
| 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg | 2498 | 1249 | 625 | 313 | ✓ ✓ ✓ |
| 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg | 2644 | 1322 | 661 | 331 | ✓ ✓ ✓ |
| 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg | 3953 | 1977 | 989 | 495 | ✓ ✓ ✓ |
| 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg | 2455 | 1228 | 614 | 307 | ✓ ✓ ✓ |
| 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg | 4180 | 2090 | 1045 | 523 | ✓ ✓ ✓ |
| 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg | 3837 | 1919 | 960 | 480 | ✓ ✓ ✓ |

Every count is ⌈n / step⌉ and matches the original's `nb_frames`. The originals in `vids/` were only read: mtimes are still 2026-10-01, and `vids/` is still gitignored.

**Decoder fix found on the way:** `snatch.video.frames` now passes `-fps_mode passthrough`. The 120 fps copies keep a 240 fps rate tag, and ffmpeg's rawvideo output was duplicating every frame to fill it. For the 240 fps originals, the output is byte-identical with and without the flag (checked on 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg). For all 8 originals, the decoded frame count with the flag equals `nb_frames`, which is the count the pose runs used.

```
cd prototype
uv run python scripts/studies/build_ladder.py ../vids          # ~3 min per clip
```

## 2. Plate tracking

The plate is found by its outline, never from the wrists (`snatch/plate.py`):

1. **Candidates per frame:** Hough circles at half resolution, r 110–260 px. Each candidate also records the mean grey level inside it. The bumper plate is black, which separates it from round look-alikes such as the wall logo, the ball shelf and ducts.
2. **Track (Viterbi over all frames):** picks the smoothest path of plate-sized, dark circles, with an explicit "not found" state. Allowed moves are ≤ 30 px per frame, and gaps of up to 24 frames can be bridged if the position is continuous.
3. **Outline, pass A:** at full resolution, a RANSAC circle over rim edge pixels (edges whose gradient points along the radius). The radius is limited to ±6% of the tracked Hough radius, smoothed over 0.25 s. The limit rules out the lettering ring (~0.8 r) and blur-inflated circles. A least-squares refit on the inliers follows. An ellipse replaces the circle only if it explains ≥ 15% more rim pixels.
4. **Outline, pass B (consistency):** refit every frame with the radius held within ±2.5% of pass A's radius, smoothed over time. The plate is thick enough that its tread shows on one side. That gives two near-equal circles (near face and outer silhouette), and without this pass the fit flipped between them frame to frame.
5. Short gaps in the track are refit around the circle interpolated across the gap, and count as found only if that fit succeeds.
6. **Per-clip sanity check:** the hub must travel ≥ 0.4 m vertically, be found in ≥ 90% of frames, and never jump. The result is saved as `status`.

Off-axis clips run with `model="ellipse"`: a RANSAC ellipse, with pass B holding both semi-axes within 6% of their smoothed tracks (`track_plate.py <clip> <out> ellipse`).

Saved per clip in `prototype/out/<clip>/plate.npz`. Arrays have length n_frames (240 fps), with the same frame index as `raw_pose.npz`, in pixels of the rotated frame:

| Field | Meaning |
|---|---|
| `found` | plate outline present at this frame |
| `hub_x`, `hub_y` | outline centre = bar axis at the near plate's face. **Use as a keypoint.** |
| `a`, `b`, `angle` | semi-axes (px) and rotation (deg, OpenCV `fitEllipse` convention); a circle when a = b |
| `px_per_m` | 2·max(a, b) / 0.45 m: the major axis is the true diameter even when the plate is tilted |
| `ellipse_fit` | False where the refit failed and the Hough circle is used as the outline |
| `seed`, `seed_x/y/r` | 1 = tracked Hough circle, 2 = interpolated across a gap |
| `status`, `travel_m`, `jumps`, `r0`, `model` | clip-level sanity check and outline model |

Also per clip:
- `plate_check.jpg`: **zoomed full-resolution crops** around the plate at ~18 frames (14 evenly spaced, the highest and lowest hub, up to 2 missed). Green = rim fit, yellow = circle fallback.
- `bar_path.png`: hub path over the first frame, and hub x/y against time.
- `plate.csv`: the same data as `plate.npz` (gitignored, regenerate it).

| Clip | View | Model | Found | Plate r (px) | px/m (median) | Hub jitter x/y (px), before → after | Status |
|---|---|---|---|---|---|---|---|
| 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg | side | circle | 100.0% | 173 | 767 | 3.4/2.8 → **1.6/1.6** | ok |
| 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg | side | circle | 100.0% | 171 | 775 | 2.9/2.6 → **1.1/1.4** | ok |
| 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg | side | circle | 100.0% | 174 | 793 | 3.2/2.7 → **0.8/1.1** | ok |
| 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg | side | circle | 100.0% | 175 | 784 | 3.4/2.8 → **0.8/1.0** | ok |
| 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg | side | circle | 100.0% | 152 | 674 | 2.9/2.6 → **0.7/0.7** | ok |
| 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg | off-axis | ellipse | 93.3% | 133 | 606 | 7.1/4.6 → 8.6/7.5 | **check: 42 jumps** |
| 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg | off-axis | ellipse | 96.1% | 132 | 627 | 9.9/13.3 → 11.5/15.0 | **check: 119 jumps** |
| 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg | bar only | — | — | — | — | — | **no plate** |

Jitter is the SD of raw minus smoothed (Savitzky-Golay 0.1 s) over found frames. It measures consistency, not accuracy. Accuracy is checked by eye on the zoomed sheets: every sampled frame of the 5 side-on clips has the outline on the rim.

**Precision.** After the fix, side-on hub jitter is 0.7–1.6 px (~1–2 mm). The near wrist keypoint jitters 1.9–7.4 px on the same clips. At rest before the lift in 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg, smoothed hub speed SD is 15 px/s against 297 px/s for the wrist. The scale is ~780 px/m on the hoodie-session clips, so 1 px ≈ 1.3 mm.

**Assumption to confirm:** the 5 kg plates are 450 mm in diameter (standard bumper size, not measured). If they are smaller, `px_per_m` scales by 450 / true diameter. Hub positions and outlines are unaffected.

### Correction (2026-10-02): the first outline fit was off the rim

The first version (commit 6d7a77e) refit an unconstrained 5-parameter ellipse through all rim-like edges. At full resolution it was visibly off the plate in many frames, e.g. 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg f324/f510/f1021/f2042 and 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg f357/f713/f1427. It mixed in the lettering ring and the tread crescent, came out slightly oval on side-on plates (b/a 0.94–0.96, where the true value is ~1.0), and scattered the hub by 3–4 px frame to frame. The thumbnail check images were too small to show it.

Compared with the fixed hub, the old one was off by a median of 5–7 px and a 95th percentile of 14–19 px on the side-on clips. Phase frames on 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg moved by at most 2 frames (rep 1 setup f927 → f925). The hold went from 344 to 340 frames. px/m went down by ~4%, because the old ellipse's major axis was inflated.

### Where plate detection fails

| Clip | What fails | Reason |
|---|---|---|
| **20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg** | Everything: no plate, so no hub. `plate.npz` was deleted. `plate_check.jpg` and `bar_path.png` are kept as evidence: the tracker latched onto balls and the hoodie, and the sanity check flags it. | Bar only. The bar end/sleeve (~50 mm across, ~35 px) was **not attempted**. It is end-on to the camera only part of the time, and the bar tilts and rotates in the hands, so it is not a circle-detector target. **20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg keeps phase definition v1 (wrist timing).** |
| **20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg, 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg** (off-axis) | The outline is right overhead, against the bright wall. On the floor (setup, pull, after the drop) it wanders: oversized or tilted ellipses, and in 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg stretches on the lifter's black shorts. Flagged automatically (42 and 119 jumps). **Their hub must not be used for v2 timing as it stands.** | Seen from behind and to the right, the plate is an ellipse (b/a ≈ 0.84) whose rim on the dark floor is faint, while the tread, the legs and the shorts add rim-like edges. Neither the circle nor the ellipse model separates them reliably. |

Off-axis clips are the "degraded" condition in #11, so a partial result there is a finding, not a blocker. For how #15 phases them, see "Decision for #15" in §4.

```
uv run python scripts/track_plate.py ../vids/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg.MOV out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg           # ~2-4 min per clip
uv run python scripts/track_plate.py ../vids/20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg.MOV out/20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg ellipse   # off-axis
```

## 3. Standing hold in 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg (noise-floor sample)

**1.417 s = 340 frames, f1151–f1490 (4.796–6.208 s).** Output: `prototype/out/20261001_2_jiri_v1_standup_5kg_1rep_success_0deg/hold.json`, from `scripts/studies/measure_hold.py`.

Definition: the longest run where the hub is found and above the knee keypoints (bar off the floor, at the hips), and its smoothed height stays within a **2 cm band** (15 px at the plate's own scale). Horizontal sway is allowed, since it is part of standing still: the hub drifts 26 px ≈ 3.5 cm forward and back. During the hold, knee angle is 170.5–180° and the hub sits 64 px (~8.5 cm) below the hip keypoints.

| Band | Hold length |
|---|---|
| 1 cm | 241 frames (1.00 s) |
| **2 cm** | **340 frames (1.42 s)** |
| 3 cm | 380 frames (1.58 s) |

A speed threshold is too strict here: the 50 px/s "still" threshold used for liftoff gives at most 147 frames (0.61 s), because normal standing sway crosses it.

So the static sample is ~1.4 s × 240 fps ≈ 340 frames, but only ~1.4 s of real time. Frame-to-frame values within it are strongly correlated, so it is a short noise-floor sample, not 340 independent ones.

## 4. Phase definition v2 (frozen 2026-10-02, before #15)

**v2 = v1 with every use of wrist height replaced by the near plate's hub height, plus one change to how the transition is measured (v2.1, below).** Everything else is unchanged: same events, same thresholds (≥ 0.25 s overhead, 50 px/s still, 3° re-bend prominence, 5° lockout tolerance), same order, same smoothing (fill gaps, Savitzky-Golay 0.1 s order 2). Written down in `snatch/phases.py` (module docstring and `find_reps_v2`).

| Event | v2 rule |
|---|---|
| Rep | ≥ 0.25 s continuous with the **hub** above the nose |
| Setup | last frame before that with the **hub** below the hips, then step back to the start of the continuous rise (> 50 px/s) |
| Transition | deepest knee-angle minimum with prominence ≥ 3° **measured on the whole setup → peak-extension segment**, accepted only if it falls after the **hub** passes above the knees |
| Catch | lowest hip between that peak and the end of the overhead run |
| Lockout | first frame after the catch with knee within 5° of its overhead maximum |

The rationale (from #12): seen from the side, the hands sit inside the plate's outline. The wrists are the least confident keypoints (near 0.65–0.74, far 0.47–0.61). The hub is visible and is on the bar the hands grip. Clips without a plate (20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg) keep v1.

**Provenance of the transition rule (v2.1). This was not decided blind.** With only the swap (the ticket's "nothing else changes"), v2 lost rep 2's transition on 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg. The cause: the hub is the bar, which sits lower than the wrist joint, so it passes the knee keypoint ~38 frames later than the wrist did (f2617 against f2579). That is *after* the knee's local maximum before the re-bend (f2611). The re-bend's prominence was measured only inside the search window, so its left shoulder was cut off and it measured 1.4° instead of 5.8°. The fix measures prominence on the whole setup → peak segment and keeps the "after the bar passes the knees" condition as an acceptance filter. **The lifter chose it on 2026-10-02 after seeing the 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg result, before #15.** v1 is unchanged.

### v1 vs v2 on 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg

`prototype/out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg/phases_v1_v2.md`, `phases_v2.json`; `scripts/compare_phases.py out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg`.

| Rep | Event | v1 | v2 | v2 − v1 |
|---|---|---|---|---|
| 1 | setup | f1001 (4.171 s) | f925 (3.854 s) | **−76 frames (−317 ms)** |
| 1 | transition | f1065 | f1065 | 0 |
| 1 | catch | f1238 | f1238 | 0 |
| 1 | lockout | f1471 | f1471 | 0 |
| 2 | setup | f2553 (10.637 s) | f2483 (10.346 s) | **−70 frames (−292 ms)** |
| 2 | transition | f2630 | f2630 | 0 (only-swap v2: not detected) |
| 2 | catch | f2781 | f2781 | 0 |
| 2 | lockout | f3010 | f3010 | 0 |

(The overhead run, which only defines the rep, shifts by −6 to +15 frames.)

**Setup: v1 was late, not v2.** At v1's setup frame the plate is already off the floor: the hub is 135 px (~17 cm) above its resting height at f1001, and 106 px (~14 cm) at f2553. At v2's setup frame the hub has risen 4 px (f925) and 3 px (f2483), which is the true start of the bar's rise. While hidden behind the plate, the wrist keypoint stalls and lags the bar. Check: `prototype/out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg/setup_v1_v2.jpg`, crops at rest, v2 setup, mid-rise and v1 setup for both reps. **Consequence for #12:** the "setup" angles in #12 were sampled ~0.3 s after liftoff, with the bar 14–17 cm up.

Two more notes on the comparison:
- v1 uses the mean of both wrists (as in #12); v2 uses the near plate's hub only.
- v2 timing is only as good as the hub.

### Decision for #15: off-axis clips (lifter, 2026-10-02)

The off-axis hub is unreliable on the floor (§2), which is exactly where v2 times setup and the transition window. For now that is acceptable: 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg and 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg are not filmed from the right side, so a perfect plate fit is not expected. #15 handles them as follows:

- **20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg and 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg are phased with v1 (wrist timing).**
- **#15 also runs v1 on the side-on main-set clips.** It's cheap, because it uses the same pose output.
- **The degraded-take SD ratio is v1 against v1:** off-axis SD (v1) / main-set SD (v1). Using v2 for the main set would mix two phase definitions, which differ by ~0.3 s at setup, so part of the ratio would come from the definition rather than the camera angle.
- **All main side-on results use v2,** as frozen.
- 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg (bar only) keeps v1, as before.

## Files

| Path | Content | In git |
|---|---|---|
| `vids/ladder/*.MOV` | 24 ladder files | no (`vids/` ignored) |
| `prototype/out/ladder.json` | per clip and rate: method, frames, expected, pixel_identical, rotation, size | yes |
| `prototype/out/<clip>/plate.npz` | per-frame hub, outline, px/m, status (7 plate clips) | yes |
| `prototype/out/<clip>/plate_check.jpg`, `bar_path.png` | zoomed check images and bar path (all 8, incl. the 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg failure) | yes |
| `prototype/out/<clip>/plate.csv` | the same data as `plate.npz` | no (regenerate) |
| `prototype/out/20261001_2_jiri_v1_standup_5kg_1rep_success_0deg/hold.json` | hold length and stats | yes |
| `prototype/out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg/phases_v1_v2.md`, `phases_v2.json`, `setup_v1_v2.jpg` | v1 vs v2 | yes |

Pose output (`raw_pose.npz`) for clips other than 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg stays local, as before.

### Per-clip output set (added 2026-10-02, before #15)

Every clip folder `prototype/out/<clip>/` now has the same set, where it applies:

| File | Made by | In git | Clips |
|---|---|---|---|
| `raw_pose.npz` | `extract_pose.py` | yes | all 8 |
| `plate.npz` | `track_plate.py` | yes | 7 plate clips (not 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg) |
| `plate_check.jpg`, `bar_path.png` | `track_plate.py` | yes | all 8 |
| `plate.csv` | `track_plate.py` | no | 7 plate clips |
| `angles.csv`, `angles.png`, `phases.json` (v1 marks) | `analyze.py` | yes | all 8 |
| `grabs/*.jpg`, `phase_sheet.jpg` (pose + v1 marks) | `analyze.py` | yes | all with reps (not 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg) |
| `overlay.mp4` | `analyze.py` | no (~3 MB each; ~15 s to regenerate) | all 8 |
| `phases_v2.json`, `phases_v1_v2.md` | `compare_phases.py` | yes | 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg, 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg, 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg (not 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg: no plate; not 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg/20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg: hub unreliable, v1 for #15) |
| `spread.md`, `values`/`sd` in `phases.json` | `analyze.py … spread` | yes | **20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg only** (#12). Left to #15 for the others, so across-rep SD is not seen before #15 runs |
| `hold.json` | `measure_hold.py` | yes | 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg only |
| `setup_v1_v2.jpg` | one-off (#14), no script | yes | 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg only |
| `raw_pose_untracked.npz` | first pose run before the crop fix (#12) | yes | 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg only |

`overlay.mp4` shows the pose (as in `grabs/`) plus: plate outline and hub (green; **orange** with "plate: check" where the sanity check failed, 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg/20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg), the hub path over the last 2 s, the near elbow-to-hub segment, v1 (yellow) and v2 (green) phase marks as 0.25 s banners and as ticks on a timeline, a 10 cm scale bar from `px_per_m`, and "HOLD" over the 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg hold. v2 is shown only where the plate status is `ok`. The video is display only: nothing in it changes a phase rule or a value.

```
uv run python scripts/analyze.py ../vids/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg.MOV out/20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg spread   # 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg only
uv run python scripts/analyze.py ../vids/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg.MOV out/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg          # other clips
uv run python scripts/compare_phases.py out/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg                        # side-on plate clips
```
