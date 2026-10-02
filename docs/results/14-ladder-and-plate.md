# 14 — Frame-rate ladder and plate tracking

Ticket: [#14](https://github.com/jirigrill/snatch-exercise-validation/issues/14) (parent [#11](https://github.com/jirigrill/snatch-exercise-validation/issues/11)). Run 2026-10-02.

**Bottom line.**
- **Ladder:** all 24 files (8 clips × 120/60/30 fps) are built. Each is checked frame by frame and is pixel-identical to every 2nd/4th/8th frame of its 240 fps original. The originals are untouched.
- **Plate:** the near plate is tracked as an object in all 7 plate clips. Coverage is 100% on the 5 side-on clips. The 2 off-axis clips are partial: 4586 has stretches where the tracker follows something else.
- **Hold:** the standing hold in 4579 is **1.43 s (344 frames, f1147–f1490)**.
- **Phase definition v2** (hub height in place of wrist height, plus the v2.1 transition rule chosen by the lifter after seeing 4584) is written down and frozen. On 4584 it moves **setup ~0.3 s earlier** (v1 was late, see below). Transition, catch and lockout land on the same frames as v1.

Code: `prototype/src/snatch/{ladder,plate}.py`, `prototype/scripts/{build_ladder,track_plate,measure_hold,compare_phases}.py`.

## 1. Frame-rate ladder

Ladder frame k is original frame k × step (step 2/4/8), counted from frame 0 in display order. Pose indices therefore map back by multiplication. Files: `vids/ladder/IMG_<clip>_<fps>fps.MOV` (gitignored, 6.5 GB). Report: `prototype/out/ladder.json`.

**No re-encoding where none is needed.** iPhone 240 fps HEVC is coded in 4 temporal sub-layers (tid 0–3). Dropping all NAL units above a tid leaves a legal stream that decodes without changing any pixel. Where a sub-layer is exactly every Nth frame, its original packets are copied with their original timestamps. Where it is not, the chosen frames are re-encoded **losslessly** (x265 `lossless=1`). Both paths keep the rotation tag (−90°).

**Deviation from the ticket's wording:** the 30 fps files (all clips) and 4583/4586 at 120 fps are re-encoded, not cut from the original bitstream. Exact every-8th sampling cannot be cut from these streams. The re-encode is lossless and verified pixel-identical, so the intent ("no change to pixels") holds.

| Rate | Method | Clips |
|---|---|---|
| 120 fps | sub-layer tid ≤ 2 copy | 6 |
| 120 fps | lossless re-encode: the sub-layer copy decoded differently (the dropped trailing frame was a reference) and was caught by the check | 4583, 4586 |
| 60 fps | sub-layer tid ≤ 1 copy | all 8 |
| 30 fps | lossless re-encode: the tid-0 layer gains an extra frame at each CRA (every ~236 frames), so its step is 8 frames with a 4-frame step at each CRA, not every 8th | all 8 |

Two details make the copies valid:
- Many clips code their last frame in a low layer. Such extra frames after the last wanted one are dropped.
- Every file is verified: MD5 of each decoded, rotated frame (same decoder as the pose run) equals the original's frame k × step.

| Clip | 240 fps frames | 120 | 60 | 30 | Pixel-identical |
|---|---|---|---|---|---|
| 4578 | 2943 | 1472 | 736 | 368 | ✓ ✓ ✓ |
| 4579 | 2553 | 1277 | 639 | 320 | ✓ ✓ ✓ |
| 4581 | 2498 | 1249 | 625 | 313 | ✓ ✓ ✓ |
| 4583 | 2644 | 1322 | 661 | 331 | ✓ ✓ ✓ |
| 4584 | 3953 | 1977 | 989 | 495 | ✓ ✓ ✓ |
| 4585 | 2455 | 1228 | 614 | 307 | ✓ ✓ ✓ |
| 4586 | 4180 | 2090 | 1045 | 523 | ✓ ✓ ✓ |
| 4587 | 3837 | 1919 | 960 | 480 | ✓ ✓ ✓ |

Every count is ⌈n / step⌉ and matches the original's `nb_frames`. The originals in `vids/` were only read: mtimes are still 2026-10-01, and `vids/` is still gitignored.

**Decoder fix found on the way:** `snatch.video.frames` now passes `-fps_mode passthrough`. The 120 fps copies keep a 240 fps rate tag, and ffmpeg's rawvideo output was duplicating every frame to fill it. For the 240 fps originals, the output is byte-identical with and without the flag (checked on 4579). For all 8 originals, the decoded frame count with the flag equals `nb_frames`, which is the count the pose runs used.

```
cd prototype
uv run python scripts/build_ladder.py ../vids          # ~3 min per clip
```

## 2. Plate tracking

The plate is found by its outline, never from the wrists (`snatch/plate.py`):

1. **Candidates per frame:** Hough circles at half resolution, r 110–260 px. Each candidate also records the mean grey level inside it. The bumper plate is black, which separates it from round look-alikes such as the wall logo, the ball shelf and ducts.
2. **Track (Viterbi over all frames):** picks the smoothest path of plate-sized, dark circles, with an explicit "not found" state. Allowed moves are ≤ 30 px per frame, and gaps of up to 24 frames can be bridged if the position is continuous. The plate radius per clip is the median radius of the best dark candidate.
3. **Outline:** each tracked circle is refit at full resolution as an ellipse through rim edge pixels whose gradient points along the radius, with a shrinking inlier band. Short gaps in the track are refit around the circle interpolated across the gap, and count as found only if that fit succeeds.
4. **Per-clip sanity check:** the hub must travel ≥ 0.4 m vertically, be found in ≥ 90% of frames, and never jump. The result is saved as `status`.

Saved per clip in `prototype/out/<clip>/plate.npz`. Arrays have length n_frames (240 fps), with the same frame index as `raw_pose.npz`, in pixels of the rotated frame:

| Field | Meaning |
|---|---|
| `found` | plate outline present at this frame |
| `hub_x`, `hub_y` | outline centre = bar axis at the near plate's face. **Use as a keypoint.** |
| `a`, `b`, `angle` | ellipse semi-axes (px) and rotation (deg, OpenCV `fitEllipse` convention); a circle when a = b |
| `px_per_m` | 2·max(a, b) / 0.45 m: the major axis is the true diameter even when the plate is tilted |
| `ellipse_fit` | False where the refit failed and the Hough circle is used as the outline |
| `seed`, `seed_x/y/r` | 1 = tracked Hough circle, 2 = interpolated across a gap |
| `status`, `travel_m`, `jumps`, `r0` | clip-level sanity check |

Also per clip: `plate.csv` (the same data; gitignored, regenerate it), `plate_check.jpg` (the outline and hub drawn at 6 evenly spaced frames plus the highest and lowest hub positions and up to 2 missed frames; green = ellipse fit, yellow = circle fallback) and `bar_path.png` (hub path over the first frame, and hub x/y against time).

| Clip | View | Found | Ellipse fit | Plate r (px) | px/m (median) | b/a | Status |
|---|---|---|---|---|---|---|---|
| 4579 | side | 100.0% | 100.0% | 173 | 819 | 0.96 | ok |
| 4581 | side | 100.0% | 99.9% | 171 | 794 | 0.95 | ok |
| 4583 | side | 100.0% | 100.0% | 174 | 826 | 0.94 | ok |
| 4584 | side | 100.0% | 99.7% | 175 | 819 | 0.96 | ok |
| 4587 | side | 100.0% | 99.8% | 152 | 708 | 0.95 | ok |
| 4585 | off-axis | 97.1% | 95.6% | 133 | 620 | 0.89 | ok (gaps after the drop) |
| 4586 | off-axis | 97.8% | 97.0% | 132 | 617 | 0.91 | **check: 8 jumps** |
| 4578 | bar only | — | — | — | — | — | **no plate** |

**Precision.** Frame-to-frame jitter (raw minus smoothed) is 2.6–3.4 px on the side-on clips, about 3–4 mm. The near wrist keypoint jitters 1.9–7.4 px on the same clips. After the same smoothing, the gap is large: at rest before the lift in 4584, hub speed SD is 40 px/s against 297 px/s for the wrist. The wrist wanders while it is hidden; the hub does not. A scale of ~820 px/m means 1 px ≈ 1.2 mm.

**Assumption to confirm:** the 5 kg plates are 450 mm in diameter (as stated in the ticket). If they are smaller, `px_per_m` scales by 450 / true diameter. Hub positions and outlines are unaffected.

### Where plate detection fails

| Clip | What fails | Reason |
|---|---|---|
| **4578** | Everything: no plate, so no hub. `plate.npz` was deleted. `plate_check.jpg` and `bar_path.png` are kept as evidence: the tracker latched onto balls and the hoodie, and the sanity check flagged 7 jumps. | Bar only. The bar end/sleeve (~50 mm across, ~35 px) was **not attempted**. It is end-on to the camera only part of the time, and the bar tilts and rotates in the hands (see the 4578 contact sheet), so it is not a circle-detector target. **4578 keeps phase definition v1 (wrist timing).** |
| **4586** (off-axis) | Both lifts are tracked. At least four stretches follow the lifter's black shorts instead of the plate: ~2.1–3.3 s, **~4.9–5.7 s (rep 1 overhead)**, ~8.7–9.3 s, ~15.6–16.5 s. Flagged automatically (jumps at f999, 1189, 1380, 1580, 2245). | Seen from behind and to the right, the plate is an ellipse (b/a ≈ 0.9) that is smaller (r ≈ 132 px), and the black shorts look like a dark disc of the same size. Do **not** use the 4586 hub without masking these stretches. |
| 4585 (off-axis) | Tracked through the lift. Gappy for ~1 s after the drop, while the plate bounces and rolls. | Motion blur and the bar rolling. Passes the sanity check. |

Off-axis clips are the "degraded" condition in #11, so a partial result there is a finding, not a blocker.

```
uv run python scripts/track_plate.py ../vids/IMG_4584.MOV out/4584   # ~2-4 min per clip
```

## 3. Standing hold in 4579 (noise-floor sample)

**1.433 s = 344 frames, f1147–f1490 (4.779–6.208 s).** Output: `prototype/out/4579/hold.json`, from `scripts/measure_hold.py`.

Definition: the longest run where the hub is found and above the knee keypoints (bar off the floor, at the hips), and its smoothed height stays within a **2 cm band** (15 px at the plate's own scale). Horizontal sway is allowed, since it is part of standing still: the hub drifts 40 px ≈ 5 cm forward and back. During the hold, knee angle is 170.5–180° and the hub sits 62 px (~8 cm) below the hip keypoints.

| Band | Hold length |
|---|---|
| 1 cm | 211 frames (0.88 s) |
| **2 cm** | **344 frames (1.43 s)** |
| 3 cm | 384 frames (1.60 s) |

A speed threshold does not work here: the 50 px/s "still" threshold used for liftoff gives only 23 frames, because the hub's frame-to-frame jitter alone crosses it.

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

The rationale (from #12): seen from the side, the hands sit inside the plate's outline. The wrists are the least confident keypoints (near 0.65–0.74, far 0.47–0.61). The hub is visible and is on the bar the hands grip. Clips without a plate (4578) keep v1.

**Provenance of the transition rule (v2.1). This was not decided blind.** With only the swap (the ticket's "nothing else changes"), v2 lost rep 2's transition on 4584. The cause: the hub is the bar, which sits lower than the wrist joint, so it passes the knee keypoint ~38 frames later than the wrist did (f2617 against f2579). That is *after* the knee's local maximum before the re-bend (f2611). The re-bend's prominence was measured only inside the search window, so its left shoulder was cut off and it measured 1.4° instead of 5.8°. The fix measures prominence on the whole setup → peak segment and keeps the "after the bar passes the knees" condition as an acceptance filter. **The lifter chose it on 2026-10-02 after seeing the 4584 result, before #15.** v1 is unchanged.

### v1 vs v2 on 4584

`prototype/out/4584/phases_v1_v2.md`, `phases_v2.json`; `scripts/compare_phases.py out/4584`.

| Rep | Event | v1 | v2 | v2 − v1 |
|---|---|---|---|---|
| 1 | setup | f1001 (4.171 s) | f927 (3.862 s) | **−74 frames (−308 ms)** |
| 1 | transition | f1065 | f1065 | 0 |
| 1 | catch | f1238 | f1238 | 0 |
| 1 | lockout | f1471 | f1471 | 0 |
| 2 | setup | f2553 (10.637 s) | f2483 (10.346 s) | **−70 frames (−292 ms)** |
| 2 | transition | f2630 | f2630 | 0 (only-swap v2: not detected) |
| 2 | catch | f2781 | f2781 | 0 |
| 2 | lockout | f3010 | f3010 | 0 |

(The overhead run, which only defines the rep, shifts by −6 to +15 frames.)

**Setup: v1 was late, not v2.** At v1's setup frame the plate is already off the floor: the hub is 129 px (~16 cm) above its resting height at f1001, and 103 px (~13 cm) at f2553. At v2's setup frame the hub has risen 5 px (f927) and 0 px (f2483), which is the true start of the bar's rise. While hidden behind the plate, the wrist keypoint stalls and lags the bar. Check: `prototype/out/4584/setup_v1_v2.jpg`, crops at rest, v2 setup, mid-rise and v1 setup for both reps. **Consequence for #12:** the "setup" angles in #12 were sampled ~0.3 s after liftoff, with the bar 13–16 cm up.

Two more notes on the comparison:
- v1 uses the mean of both wrists (as in #12); v2 uses the near plate's hub only.
- v2 timing is only as good as the hub. 4586's bad stretches (§2) would corrupt its timing, and nothing in `plate.npz` masks them; only the `status`/`jumps` fields flag the clip.

## Files

| Path | Content | In git |
|---|---|---|
| `vids/ladder/*.MOV` | 24 ladder files | no (`vids/` ignored) |
| `prototype/out/ladder.json` | per clip and rate: method, frames, expected, pixel_identical, rotation, size | yes |
| `prototype/out/<clip>/plate.npz` | per-frame hub, outline, px/m, status (7 plate clips) | yes |
| `prototype/out/<clip>/plate_check.jpg`, `bar_path.png` | check images (all 8, incl. the 4578 failure) | yes |
| `prototype/out/<clip>/plate.csv` | the same data as `plate.npz` | no (regenerate) |
| `prototype/out/4579/hold.json` | hold length and stats | yes |
| `prototype/out/4584/phases_v1_v2.md`, `phases_v2.json`, `setup_v1_v2.jpg` | v1 vs v2 | yes |

Pose output (`raw_pose.npz`) for clips other than 4584 stays local, as before.
