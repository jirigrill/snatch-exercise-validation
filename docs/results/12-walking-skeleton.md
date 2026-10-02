# 12 — Walking skeleton: RTMPose-x on clip 4584 → angles → spread

Ticket: [#12](https://github.com/jirigrill/snatch-exercise-validation/issues/12) (parent [#11](https://github.com/jirigrill/snatch-exercise-validation/issues/11)). Run 2026-10-01.

**Bottom line.** The pipeline runs end to end on the Mac and gives plausible numbers. Clip 4584 has 2 reps, both power snatches. All four phases are found in both reps, including the transition. 13 of the 16 joint×phase SDs are ≤ 3° (smoothed). The three above 3°: setup knee at 9.4°, where the near plate hides the shin and ankle, catch knee at 3.6° and catch elbow at 4.3°. **n = 2 is far too few for a verdict.** This run checks that the pipeline works; it is not a result.

Code: `prototype/` (uv project). Outputs: `prototype/out/4584/`.

## Mac readiness

| Item | Value |
|---|---|
| Machine | Mac16,12, Apple M4, 10 cores (4P + 6E), 16 GB RAM |
| OS | macOS 26.6.2 |
| Free disk | ~26 GB (data volume, at run time) |
| Python | 3.12.10 via uv 0.12.2 |
| Packages | numpy 2.5.3, scipy 1.18.1, opencv-python-headless 5.0.0, onnxruntime 1.30.0, rtmlib 0.0.16, matplotlib 3.11.2 |
| ffmpeg | 9.0.1 (Homebrew; built without `drawtext`, cosmetic only) |
| Model | `rtmpose-x_simcc-body7_pt-body7_700e-384x288` (ONNX, 189 MB) + detector `yolox_x_8xb8-300e_humanart` (ONNX, 378 MB), downloaded by rtmlib to `~/.cache/rtmlib` |
| PyTorch / MMPose | Not installed, not needed (ONNX Runtime path) |

**Where inference runs.** onnxruntime has `CoreMLExecutionProvider` available (Apple Silicon: Neural Engine/GPU).

| Model | CoreML | CPU |
|---|---|---|
| RTMPose-x (pose) | **0.018 s/frame** ✓ | 0.066 s/frame |
| YOLOX-x (person detector) | **fails**: `CoreML static output shape ({1,1,1,8400,8400}) and inferred shape ({1,8400}) have different ranks` | 0.34 s/frame (benchmark), 0.42–0.74 s/frame in full runs |

So pose runs on CoreML and the detector runs on CPU only. The detector sets the runtime: the full 4584 run (3953 frames) took **2917 s (49 min)**. Re-running pose alone on saved detector boxes took **85 s**. Reproduce the benchmark with `uv run python scripts/bench.py ../vids/IMG_4584.MOV`.

## Pipeline

1. **Decode** (`snatch/video.py`): ffmpeg applies the display-matrix rotation (−90°) automatically. Frames are portrait, 1080×1920, 240 fps.
2. **Detect + pose** (`snatch/pose.py`): YOLOX-x boxes. The lifter is the box that best overlaps the previous one, or the largest box if none overlap. Each box is merged with the previous frame's keypoint extent plus 10% padding (see "Blockers" #3), then RTMPose-x gives COCO-17 keypoints.
3. **Angles** (`snatch/angles.py`): near side = lifter's right (camera on the right). Hip, knee and elbow are the interior angle at the joint (180° = straight). Hip = shoulder-hip-knee, knee = hip-knee-ankle, elbow = shoulder-elbow-wrist. Trunk = hip→shoulder line measured from image vertical (0° = upright, positive = leaning forward). This assumes the phone was held level.
4. **Smoothing** (`snatch/signals.py`): fill gaps by linear interpolation, then a Savitzky-Golay filter (0.1 s window, order 2) on keypoint coordinates.
5. **Phases** (`snatch/phases.py`), then **spread** (`snatch/spread.py`): sample SD (ddof = 1) across reps at each phase frame.

Run:

```
cd prototype
uv run python scripts/extract_pose.py ../vids/IMG_4584.MOV out/4584                 # ~50 min
uv run python scripts/analyze.py ../vids/IMG_4584.MOV out/4584                      # ~1 min
```

## Phase definition v1 (frozen; later tickets reuse it)

Phases are found from smoothed signals: wrist, nose and hip height (mean of left and right), knee height, and the near-side knee angle.

| Event | Definition |
|---|---|
| Rep | A continuous stretch of ≥ 0.25 s with the wrists above the nose. One stretch = one rep. |
| **Setup** (liftoff) | Anchor on the last frame before that stretch where the wrists are still below the hips (mid-pull, bar rising). Then step back to the start of that continuous rise: the first frame where the wrists rise faster than 50 px/s (~8 cm/s). |
| **Transition** (double knee bend) | The deepest local minimum of the knee angle, with prominence ≥ 3°. It is searched only between the moment the wrists rise above the knees and the peak knee extension before the wrists pass the nose. No such minimum = **transition not detected**. |
| **Catch** | Lowest hip (largest image y) between that peak extension and the end of the overhead stretch. |
| **Lockout** | First frame after the catch where the knee angle is within 5° of its maximum for the rest of the overhead stretch. |

Deliberate choices that later tickets inherit:
- **"Setup" means liftoff**: the start of the bar's continuous rise, not the static start position held before it. Hips often rise just before the bar breaks the floor, so the static position and liftoff can differ.
- **"Lockout" means legs straight.** Only the knee is checked. Elbow extension and how stable the bar is overhead are not.
- **Wrist height is used only to time phases**, as a stand-in for the bar. It is never reported as a bar measurement, so the #11 rule "bar tracked as an object, never from the wrist" still holds. When plate tracking lands (#14), the bar can replace the wrist for timing.
- **The transition frame is found from the near knee angle**, and the near knee is behind the plate at that moment. So the *timing* of the transition, not only the angle there, depends on a guessed keypoint.

Why it looks like this: three earlier versions failed on real data. Each failure is now a unit test:
- The bar floats near the top before the wrists pass the nose, which broke a search that walked back from the overhead start.
- The wrist sits lower during the reach-down than at the final grip, which broke a "floor level" rule.
- A plate-occluded knee dip right after liftoff was picked as the transition.

### Phase times found (4584)

| Rep | Setup | Transition | Catch | Lockout | Transition detected |
|---|---|---|---|---|---|
| 1 | f1001 (4.171 s) | f1065 (4.438 s) | f1238 (5.158 s) | f1471 (6.129 s) | yes |
| 2 | f2553 (10.637 s) | f2630 (10.958 s) | f2781 (11.588 s) | f3010 (12.542 s) | yes |

Visual check: `prototype/out/4584/phase_sheet.jpg` (rows = reps, columns = phases) and `grabs/*.jpg`. Both reps show matching positions at every phase: liftoff, bar at upper thigh/hip (close to the power position: trunk 18–20°, hip 129–131°), power catch under the bar, standing lockout. The skeleton sits on the lifter in every frame checked, so the rotation is applied correctly. A human check of these phase frames is ticket #13.

## SD across the 2 reps (degrees)

**Caveat: n = 2.** With two reps, SD = |difference| / √2. The #11 verdict bands (≤ 3° repeatable, 3–5° marginal, > 5° not) are shown for orientation only. **No verdict is drawn from this table.**

Smoothed angles (primary):

| Joint | Setup | Transition | Catch | Lockout |
|---|---|---|---|---|
| Hip | 1.1 | 1.4 | 1.9 | 0.8 |
| Knee | **9.4** | 0.7 | 3.6 | 0.8 |
| Elbow | 2.5 | 2.7 | 4.3 | 1.5 |
| Trunk | 0.6 | 1.7 | 2.9 | 2.7 |

Raw (unsmoothed) angles at the same frames:

| Joint | Setup | Transition | Catch | Lockout |
|---|---|---|---|---|
| Hip | 1.5 | 2.1 | 1.6 | 1.3 |
| Knee | 7.7 | 1.7 | 4.3 | 0.4 |
| Elbow | 1.0 | 4.3 | 5.0 | 1.1 |
| Trunk | 1.4 | 1.7 | 2.3 | 3.0 |

Per-rep values: `prototype/out/4584/spread.md`. Catch depth (knee at the catch) is 107° and 102°, which fits a power catch and matches the visual variant label in `docs/clip-log.md`.

How to read this:
- **Setup knee (9.4°) is the weak spot.** The near plate hides the near shin and ankle. RTMPose places the ankle on the plate hub (see `grabs/rep*_setup_*.jpg`), so the knee angle at setup is a guess. This matches the clip-log limit "near plate occludes lower legs at setup/pull".
- **Transition knee (0.7°) is repeatable but not visibly measured.** At the transition the near knee is also behind the plate. A low SD here means the model guesses consistently. It does not mean the angle is right. That is the distinction #11 is built on: repeatable, not accurate.
- **Catch spread (knee 3.6°, elbow 4.3°)** includes real variation in power-catch depth between the two reps, not only model noise.
- **Elbow at lockout reads 164–166°, not ~180°.** Probably 2D projection or the wrist keypoint landing on the bar. It is consistent across reps, so it doesn't affect the spread.
- Raw vs smoothed values differ by up to 2.6° per rep (rep 2 transition elbow). Smoothing matters at 240 fps; #15 should report both.

## Files

| File | Content |
|---|---|
| `out/4584/raw_pose.npz` | Raw model output used for the analysis: keypoints (3953×17×2 px), scores, detector box, tracked crop box, people count, run metadata |
| `out/4584/raw_pose_untracked.npz` | First run, before the crop fix (detector box only). Kept for comparison: 343 frames differ by > 20 px on some keypoint |
| `out/4584/angles.csv` | Per frame: 4 angles raw + smoothed, all 17 keypoints x/y/score, people count |
| `out/4584/phases.json` | Phase frames and times, per-rep values, SD tables, mean near-side keypoint score at each phase |
| `out/4584/angles.png` | Angle and height traces with the phase markers |
| `out/4584/phase_sheet.jpg`, `grabs/` | Overlays at each phase frame. Yellow = near side, grey = far side, red dot = score < 0.3, blue = detector box, magenta = tracked crop |
| `out/4584/overlay.mp4` | Full overlay video, every 4th frame at 60 fps (real time). **Gitignored** (3.4 MB); regenerate with `analyze.py` |

## Blockers and slowdowns

1. **YOLOX-x does not run on CoreML** (rank-mismatch error above), so the detector runs on CPU at 0.4–0.7 s/frame. That is ~50 min per 16 s clip. For #15 (≈ 27 k frames across all clips) this is ~4–6 h of detector time. Options: run the detector every Nth frame and rely on the tracked crop between runs; use a smaller detector (YOLOX-m/l); or export YOLOX with static shapes for CoreML. Detector boxes are saved, so a detector run only has to happen once per clip. Later pose-model runs can reuse them (`extract_pose.py <clip> <out> <old raw_pose.npz>`).
2. **First full run lost.** The background job hit a 30-min default time limit at frame 3200/3953 and saved nothing. Rerun with a longer limit. #15 should save partial output as it goes.
3. **Plates make YOLOX cut the box short at setup.** In rep 2 the box stopped above the knees, so the legs were guessed. Fixed by merging the box with the previous frame's keypoint extent. Pose was then re-run on the saved boxes (85 s).
4. **Phase detection needed 3 rounds of fixes** (see "Phase definition v1"). Each is now a regression test.
5. **Plate occlusion of the near wrist, knee and ankle** during setup and pull. Wrist height uses the mean of both wrists. Setup and transition knee values are model guesses; see above.
6. **Detector throughput varied** from 0.42 s/frame (first run) to 0.74 s/frame (second run) on the same clip. Cause not investigated (possibly thermal throttling or other load).
7. Minor: Homebrew ffmpeg has no `drawtext` filter, so overlay text uses OpenCV.

## Licensing

Per `docs/research/09-pose-model-licensing.md`, RTMPose code and rtmlib are Apache-2.0, but the body7 weights' licence is **UNVERIFIED**. Treat these results as research-only until the weights are checked.
