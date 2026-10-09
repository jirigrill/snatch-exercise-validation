# 33 — GitHub repo review: what can we reuse?
Status: research note, nothing built · Date: 2026-10-08 · Builds on: `09-pose-model-licensing.md`, `11-technique-markers.md`, `32-reference-layers.md`

## Bottom line

- **No repo gives us code or weights we should adopt.** Ours is ahead on every hard part: 240 fps handling, near-plate ellipse + hub tracking, frozen phase definition, time-based smoothing, rep-to-rep spread.
- **Licences block most of it anyway:** 5 of 10 have no licence (all rights reserved), barpath is GPL-3.0, ultralytics is AGPL-3.0. Only PerfectRep (Apache-2.0) and CV-Weightlifting-Coach (MIT) are clean, and neither helps.
- **Useful = ideas to re-implement ourselves**, ranked:

| # | Idea | Source | Helps | Effort |
|---|---|---|---|---|
| 1 | Small single-class **plate/hub detector** (fallback for off-axis tracking, initialiser) and a **fast person detector** replacing YOLOX-x (~0.4 s/frame) | ultralytics idea; build on a permissive base | `plate.py` (-30° failure), `person.py` (speed) | Medium |
| 2 | **Fault taxonomy** names/checklist (early arm bend, premature jump, high catch, hitching, ...) | barpath `FAULT_DEFS` | cause list in doc 12 §4 | Low |
| 3 | **Changepoint (PELT)** on bar-velocity difference as cross-check for turnover/catch timing | barbell-speed-estimator | `markers.py`, `phases.py` | Low, experiment |
| 4 | **DTW** between a rep and a reference trajectory | barpath | `spread.py`, layer 3 of doc 32 | Low |
| 5 | **3D lift** of RTMPose COCO-17 to estimate elbow flexion | PerfectRep (really MotionBERT upstream) | `armbend.py` | High, doubtful |
| 6 | "Mark the frame where the fault is most visible" | barpath `error_markers.py` | diagnosis output UX | Low |

- **Gaps no repo fills:** labelled misses, more lifters, heavier loads, catch/turnover stability, arm bend in side view.

## Correction to my earlier message

I said the Springer-paper repo had a sample dataset and YOLO. The linked repo (#5) is a different, earlier ISACE25 student project: no YOLO, no weights, no dataset, no perspective correction. The Springer paper's code is still unreleased, as far as I can tell.

## Summary table

| # | Repo | Task | Licence | Stars / last push | Verdict |
|---|---|---|---|---|---|
| 1 | TeaganTurner/Weightlifting-Form-Analyzer | MediaPipe rule thresholds, no snatch | none | 0 / 2026-09 | Nothing |
| 2 | SravB/Computer-Vision-Weightlifting-Coach | OpenPose deadlift score, 11 training images | MIT | 51 / 2019 | Nothing |
| 3 | scribewire/barpath | Snatch/clean/jerk bar path + 15 rule faults | **GPL-3.0** | 7 / 2026-08 | Ideas only (2, 4, 6) |
| 4 | RubenAMtz/ai-sports-assistant | OpenPose BODY_25 per-frame phase + grade | none | 31 / 2023 | Nothing |
| 5 | dhairya0609/Barbell-Trajectory-Tracking... | MedianFlow manual-ROI bar path, Type 1–4 | none | 0 / 2025-07 | Nothing |
| 6 | AndrewBoessen/PerfectRep | MotionBERT fork, powerlifting 3D | Apache-2.0 (Fit3D data: non-commercial) | 10 / 2024-08 | Experiment only (5) |
| 7 | JdoubleU2/YOLOv8-Pose-...-Clean-n-Jerk | YOLOv8 class = phase, 679 frames | none (+AGPL dep) | n/a / 2025 | Nothing |
| 8 | ultralytics/yolov8 | Docs-only landing repo | **AGPL-3.0** | n/a / 2026-09 | Idea (1), not code |
| 9 | hasanpeal/PostureCoach | Sitting posture, 4 keypoints | none | n/a / 2025-08 | Nothing |
| 10 | julianty/barbell-speed-estimator | Bar velocity (VBT), 3 pipelines | none | n/a / 2026-08 | Idea (3) |

Stars were not checked for repos 7–10 (GitHub MCP failed). Nothing was run and no weights were downloaded; findings are from reading code. Clones: `$CLAUDE_JOB_DIR/tmp/repos/` (deleted with the job).

---

## 1. [TeaganTurner/Weightlifting-Form-Analyzer](https://github.com/TeaganTurner/Weightlifting-Form-Analyzer)

- Course project, 1337 LOC, one commit, no tests/data/weights. MediaPipe Pose, rule thresholds for squat/curl/press/lunge/deadlift. No snatch.
- Angles from normalised image coords (ignores aspect ratio, `angle_calculator.py:15-33`). Reps = `find_peaks` on an angle (`rep_counter.py:36`). Clip-level min/max checks, no phases (`form_analyzer.py:47-205`). Left/right averaged blindly, wrong for a side view.
- **Use:** nothing. `angles.py`, `reps.py`, `spread.py` are already better.

## 2. [SravB/Computer-Vision-Weightlifting-Coach](https://github.com/SravB/Computer-Vision-Weightlifting-Coach)

- 2019 hobby project. OpenPose (Caffe, weights not shipped), argmax heatmap keypoints (integer-pixel, `OpenPoseVideo.py:56-63`), Ridge regression on 11 images (6 good, 5 bad deadlifts), unnormalised pixel features.
- Its one domain idea, bar-to-foot distance scaled by forearm length, is disabled (`and False`).
- **Use:** nothing. `height.py` already does body-proportion scaling better.

## 3. [scribewire/barpath](https://github.com/scribewire/barpath)

- Most complete of the set: YOLO endcap detection + MediaPipe + LK-flow stabilisation, 15 rule-based faults (p90 of pro lifts), DTW vs pro baselines, GUI, ~18K LOC, 11 test files, alpha. **GPL-3.0**, so no copying. Weights are LFS pointers (not fetched). Baselines are per-lifter `trajectory.npy` (~6 KB each).
- Phases are argmin/argmax on smoothed pixel signals with fixed thresholds (`kinematics.py:242-312`, `classics_phase_detection.py:62-130`), the same fragility as our catch/turnover marks, and cruder than `phases.py`. Assumes ~30 fps. No validation, no ground truth.
- Faults are "unlike pros" (p90), not mechanical cause. One rule is logically muddled (`incomplete_extension`: comment says "too late", description says "too early").
- **Use (ideas only, re-implement):**
  - `FAULT_DEFS` (`step4_helpers/compiled_analyzer.py:30-170`) → naming/checklist for the closed cause list (doc 12 §4).
  - DTW rep-vs-reference → `spread.py` / layer 3 (doc 32). ~20 lines.
  - `error_markers.py` → pick the frame where a fault is most visible, for the output UI.
- **Not useful:** stabilisation (our camera is fixed), pose, phases, bar tracking (box centre vs our hub).

## 4. [RubenAMtz/ai-sports-assistant](https://github.com/RubenAMtz/ai-sports-assistant)

- Kivy app, 2023, abandoned. OpenPose BODY_25 → 276 pairwise joint distances (`data_processing.py:29-49`), min-max over the whole video (outlier-sensitive), XGBoost phase classifier + Keras 1–5 "grade" (`inference.py:10-24`). Per frame, no temporal model. No licence, weights tied to BODY_25 and absolute pixels. No accuracy numbers.
- **Use:** nothing. Only transferable idea: pairwise-distance features (normalised by torso length) as a second opinion on phase boundaries. Needs labels we don't have.

## 5. [dhairya0609/Barbell-Trajectory-Tracking-for-Performance-Analysis-During-Snatch-Movement-in-Weightlifting](https://github.com/dhairya0609/Barbell-Trajectory-Tracking-for-Performance-Analysis-During-Snatch-Movement-in-Weightlifting)

- Not the Springer paper's code. Student scripts + ISACE25 PDF. Manual-ROI OpenCV MedianFlow (`tracker.py:20-21`), no re-detection. Hard-coded scale `45/90` (`metrics.py:32`) and `FPS = 59.94` (`:34`). No perspective correction (listed as future work, README:100-102), no YOLO, no data.
- Type 1–4 classifier is on x(t) reversals, unsmoothed, and **disabled** (`metrics.py:87-88` hard-codes "Type 2"). Metrics block copy-pasted 4×, `theta1` overwritten (`:137-140`). "70% on 10 videos" is not evidence.
- **Use:** nothing. Our `markers.py` already has X1/X2/Xloop/Xnet/drop. Its fixed-window Ycatch (min Y in 80–480 samples after Ymax) is no better than our catch mark.

## 6. [AndrewBoessen/PerfectRep](https://github.com/AndrewBoessen/PerfectRep)

- MotionBERT (DSTformer, 5 layers, 243-frame clips) fine-tuned on Fit3D (47 gym exercises, no weightlifting). Apache-2.0 code; Fit3D data is academic/non-commercial. Checkpoint on Google Drive only (not downloaded). 3 test files, none for the model.
- **Input:** 17 H36M joints (x, y, conf) × 243 frames, COCO→H36M via `coco2h36m` (`dataset_wild.py:15-58`). RTMPose COCO-17 output fits in format; needs an adapter (loader expects a JSON, has an x/y swap at `:64`). Expect ~25–30 fps, so subsample 240 fps by 8.
- Rep segmentation (AIFit autocorrelation, `rep_segmentation.py`) is unused and assumes periodic reps. "Form analysis" is design text only, no scoring code.
- **Use:** only as an **experiment** for hidden arm bend (`armbend.py`): lift RTMPose → 3D, compare elbow angle to manual labels. Domain shift (bar/plate occlusion, deep catch) likely swamps the gain, so start from upstream MotionBERT or another maintained lifter, not this fork. `coco2h36m` is a handy 20-line mapping if we try.

## 7. [JdoubleU2/YOLOv8-Pose-Estimation-Clean-n-Jerk](https://github.com/JdoubleU2/YOLOv8-Pose-Estimation-Clean-n-Jerk)

- Course project. Fine-tunes YOLOv8-pose with the phase as the detection class (14 clean-and-jerk phases, 679 frames, Roboflow set from TikTok-style videos, provenance unclear). `app.py` reads only `boxes.cls`, no smoothing/state machine. README reports pose mAP50 0.25–0.3 and F1 0.5; adjacent phases confuse. `kpt_shape [16,3]` with identity `flip_idx`. Weights are an LFS pointer. No licence + AGPL dependency.
- **Use:** nothing. Only data point: even this dataset confuses catch/turnover-adjacent phases, so our instability is a hard problem, not a bug.

## 8. [ultralytics/yolov8](https://github.com/ultralytics/yolov8)

- Docs-only landing repo; code is in `ultralytics/ultralytics` (not read). **AGPL-3.0**, commercial use needs the paid Enterprise licence. Matches doc 09. Speed/accuracy claims below are general knowledge, not verified.
- **Idea 1 (best of the set):** train a small single-class plate/hub detector on frames from our own clips (our ellipse fit can auto-label the on-axis frames). It would back up `plate.py` when off-axis tracking breaks and could initialise it. A fixed camera + one lifter also makes a nano person detector (~10 ms) viable in place of YOLOX-x (~0.4 s/frame).
- **Licence-safe route:** build on Apache/permissive bases (YOLOX-tiny/s, already in our stack via rtmlib; RT-DETR). Prototype on Ultralytics only if it is labelled research-only and swapped before shipping.
- YOLO-pose is not a drop-in for RTMPose-x (less accurate on occluded limbs, overhead bar, deep squat). Built-in trackers add nothing for one lifter.

## 9. [hasanpeal/PostureCoach](https://github.com/hasanpeal/PostureCoach)

- Seated-posture good/bad classifier: YOLOv8n-pose, 4 keypoints, 2 classes, 573 train images. Stock Ultralytics fine-tune (`training/train.py`, hard-coded Mac path at `:20`), no geometry logic. Claimed 97.95% mAP on 55 near-duplicate val images. README lists `client/ server/ pi/` that don't exist. No licence.
- **Use:** nothing. A good/bad classifier would also need labelled misses we don't have, and we want a cause, not a binary.

## 10. [julianty/barbell-speed-estimator](https://github.com/julianty/barbell-speed-estimator)

- Bar velocity for squat/bench/deadlift: `yolo_pose` (wrist-midpoint proxy, px/s), `yolo_seg` (plate mask + BotSORT, m/s), `sam2` (author: unreliable). No licence, one commit, no tests, no validation.
- **Scale** (`yolo_seg/yolo_velocity.py:312-328`): mask bbox extent on one frame ÷ 450 mm, one scalar for the whole clip, no perspective/depth. Ours (`plate.py` ellipse + `height.py` depth `k`) is better.
- **Velocity:** rolling-median outliers + Savitzky–Golay (window 36, poly 3) + first difference (`utils.py:77-100`). Gaps give velocity 0. Our `signals.py` (time-based window, gap fill) is better.
- **Rep detection:** PELT (`ruptures`, `rpt.Pelt(model="l2")`) on position difference, then merge/filter with a 0.6 displacement ratio (`yolo_pose/detect_concentric.py:17-52`). Hand-tuned, author admits false positives, designed for slow periodic lifts.
- **Use:** PELT on the bar-velocity difference as a **cross-check** for turnover/catch timing (`markers.py`, `phases.py`), re-implemented, experiment only. A learned plate segmenter as off-axis fallback is the same idea as #8, no code to take (stock COCO weights, no plate class).

---

## Suggested follow-ups

1. Spike the plate/hub detector (idea 1) on a permissive base, auto-labelled from `plate.npz` on side-on clips. Measure on the two -30° clips.
2. Read the barpath `FAULT_DEFS` against doc 12 §4 and add any missing cause names with our own metrics.
3. Try PELT and DTW as cheap experiments against the frozen phase marks. Don't change phase definition v2.
4. Park the 3D lift until gate 1 passes.
5. Ask the Springer-paper authors for code/data (still the most relevant external asset).
