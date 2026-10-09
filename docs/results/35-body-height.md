# 35 — Body height of L1 from video

Ticket: [#22](https://github.com/jirigrill/snatch-exercise-validation/issues/22) (method: `../research/32-reference-layers.md` § Layer 2 "Body height from video", segment lengths § Layer 1b). Run 2026-10-08 on the spike session (2026-10-07, `vids/spike/`), side-on clips. The lifter will confirm or correct the result.

**Bottom line.**
- **Estimate: 174.5 ± 3 cm with lifting shoes, ≈ 172 ± 3 cm barefoot** (sole and heel ~2.5 cm). This is the top of the outline, i.e. the top of the hair. A stadiometer presses the hair flat and may read ~1 cm less (a guess, not measured).
- **The scale is the uncertainty, not the measurement.** Within one scale, the 7 standing windows of `_1_` agree within 0.5 cm, and `_2_` reads 1.2 cm lower. The depth ratio k (scale at the body ÷ scale at the near plate) can be found two ways, and they differ by 2.6%:
  - **image** (far-plate radius and floor line, both measured in the clip): k ≈ 0.808, which gives **176.6 cm**;
  - **tape + bar spec** (camera 4 m from the bar centre, near plate face 0.685 m nearer): k ≈ 0.829, which gives **172.2 cm**.
  - The estimate is the midpoint. Its ± covers both values plus the lateral-offset and floor errors.
- **The lifter's tape-measured height decides which k is right.** About 176.5 cm in shoes means the image ratio is right, and the plate sat farther out on the sleeve or the bar was closer than 4 m. About 172 cm means the tape geometry is right, and the image ratios are biased by ~2.5%. The same k scales every bar-path metre in D1 and B6, so this one number matters beyond height.
- **Lifter's answer (2026-10-08): 172–173 cm barefoot** (self-reported, not taped at the session; logged as `height_cm` = 172.5). What the video should read is the top of the hair in shoes: 172.5 + soles ~2.5 + hair ~1 ≈ **176 cm** (range ~174.5–177.5, because the soles and hair are not measured). The image ratio (176.6) falls inside that range and the tape geometry (172.2) does not, so **k ≈ 0.808–0.81 is taken as correct**. It follows that the near plate sat ~8 cm farther from the bar centre than a plate against the collar, or the camera was a little nearer than 4 m. Either way, measure k from the far plate in each clip rather than from the tape. The ~2.5% bias of the tape geometry applies to any metric derived from it.
- The YOLOX person box is no use for the top of the head: it reads 190–197 cm, because the box runs ~20 cm above the head. The head top comes from a foreground mask instead (§1).

## 1. Method

Code: `prototype/src/snatch/studies/height.py` (+ `tests/test_height.py`), `prototype/scripts/studies/{body_height,height_summary,segment_lengths}.py`. Per-clip output: `prototype/out/<clip>/height.json` and `height_sheet.jpg`.

| Step | What |
|---|---|
| Frames | Upright (near knee ≥ 163°, hip ≥ 165°, trunk within 12° of vertical) and still (nose < 0.3 m/s, ankles < 0.15 m/s), held ≥ 0.15 s; one frame per 0.1 s. Two kinds: **hips** (wrists below the shoulders) and **overhead** (wrists above the nose, at lockout). |
| Head top | The highest foreground pixel above the eyes, in the columns from behind the ear to between ear and nose. Foreground is the frame minus a median background built from setup frames. Columns that run on into an arm, the bar or a plate are dropped (`head_top`). |
| Floor | (a) The lowest neon-green shoe pixel, moved up by the perspective shift of half the stance plus half a shoe width (stance from the two ankles' height difference; `floor_from_sole`). (b) From the near plate resting on the floor, which gives the camera height (`floor_from_plate`). (a) is used for the direct height. (a) and (b) agree to 0–7 px in the spike clips. |
| Near-plate scale | Lockout: circle-equivalent radius √(a·b) of a fresh fit per frame (`find_near_plate`; `plate.npz` sometimes follows the air-bike wheels). Rest: `plate.npz` px/m with the bar on the floor. The two differ by ~1% (S_lock 354.6, S_rest 350.9 px/m at the body). The scale used is their mean. |
| Depth ratio k | **Image:** at lockout, the far plate is fitted next to the near one (`fit_far_plate`). With equal 450 mm bumpers placed symmetrically, k = 2 / (1 + r_near/r_far) (`midline_ratio`). Median per clip. |
| Direct height | Head top to the midline floor, in **hips** frames. Only the bar-only clips `_1_` and `_2_` have such frames. In the plated clips the lifter never stands still with the bar at the hips, and at lockout the arms and plates hide the top of the head. These two clips have no plate, so they use the session scale: the median over the 6 plated right-side clips (same tripod spot). |
| Eye-based height | Lockout frames of the plated clips: near-eye keypoint to the midline floor, plus the head top's height above the eye (42 px, median of the 43 direct frames). Each clip uses its own k and plate scale. |

## 2. Geometry and sensitivity

The scale at the body is S = k × (near-plate px/m), and the height ∝ 1/k. Facts: camera tape-measured 4 m from the bar centre, side-on, lens near hip height (1.03–1.04 m from the resting plate; 1.11 m in `_11_`/`_12_`, so the tripod was moved for those). Near plate radius ~97 px (430–450 px/m).

| Source of k | k | Height (direct, shoes) | Notes |
|---|---|---|---|
| Far plate, per clip (as run) | 0.809–0.816, median 0.811 | 176.0 | Fit checked by eye at 3× zoom (frames 1589 and 3332 of `_3_`): it sits on the far rim |
| Far plate, face-corrected | 0.808 | 176.6 | The visible rims are the near plate's **outer** face and the far plate's **inner** face, so their midpoint is t/2 nearer than the bar centre: × (1 − t/2Z), t ≈ 3 cm |
| Floor line (check, not used) | 0.793–0.819, median 0.807 | ≈ 176.8 | (midline floor row − cy) / (resting plate's bottom row − cy). Assumes cy = image centre |
| Tape + 20 kg bar spec | 0.829 | 172.2 | Z = 4.0 m. Near plate's outer face at 0.655 m (sleeve start) + ~0.03 m (plate thickness) = 0.685 m from the centre. k = (4 − 0.685)/4 |
| ± 0.1 m camera distance | ±0.0045 | ∓0.9 | dk = s/Z² · dZ |
| ± 0.03 m plate position on the sleeve | ∓0.0075 | ±1.6 | Plate not pushed against the collar |

- **The two image ratios agree with each other (0.808, 0.807) and not with the tape geometry.** Take Z = 4 m. Then the far-plate ratio puts the near plate's face 0.77 m from the bar centre, 8 cm farther out than a plate against the collar. Take s = 0.685 m instead. Then the distance would be 3.57 m, not 4 m. The data can't tell which input is off.
- **The focal length can't settle it.** f = px/m × Z_near gives 1393 px at the image ratio and 1429 px at the tape geometry. Both are plausible for the iPhone 15 Pro main camera at 1080p with stabilisation crop.
- **Per-clip k is the better choice inside the session.** With one fixed k for every clip, the eye-based heights spread 3.8 cm (171.6–175.4 at k = 0.829). With each clip's own far-plate k they spread 2.9 cm. The near-plate scale moves from clip to clip (430–450 px/m: the bar is set down at a slightly different depth), and the far plate follows it.
- **Lateral offset:** if the lifter's sagittal plane is ±3 cm off the bar centre, the scale changes by ±0.75% (±1.3 cm). This is included in the ± below.

## 3. Results

### Per window (direct, `hips` frames, head top to the sole-based floor; session scale 352.8 px/m, k from the far plate as run)

| Clip | Window start (frame) | Frames | Height cm |
|---|---|---|---|
| 20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right | 1196 | 11 | 176.6 |
| | 1509 | 2 | 176.6 |
| | 1608 | 5 | 177.1 |
| | 1991 | 4 | 176.8 |
| | 2946 | 7 | 176.6 |
| | 3167 | 5 | 176.6 |
| | 4087 | 6 | 177.0 |
| 20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right | 741 | 3 | 175.4 |

The raw numbers in `height.json` for `_1_`/`_2_` use 357.0 px/m (major-axis plate scale) and read 1.2% lower. The pooled numbers below use 352.8 px/m.

### Per clip (cm with shoes; median, IQR, n frames)

| Clip | k far (n) | k floor | Direct | Eye-based (lockout) | Eye-based at k = 0.829 |
|---|---|---|---|---|---|
| 20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right | – (session scale) | – | **176.6** (176.6–177.0), 40 | – | (172.8 direct) |
| 20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right | – (session scale) | – | **175.4** (175.0–175.4), 3 | – | (171.6 direct) |
| 20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right | 0.8159 (23) | 0.801 | – | 176.7 (176.3–177.3), 23 | 173.9 |
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | 0.8130 (17) | 0.806 | – | 177.4 (176.1–178.0), 17 | 173.9 |
| 20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right | 0.8108 (18) | 0.809 | – | 177.4 (177.0–178.0), 18 | 173.5 |
| 20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right | 0.8089 (12) | 0.807 | – | 176.4 (176.1–177.5), 12 | 172.1 |
| 20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right | 0.8105 (8) | 0.793 | – | 175.5 (175.1–175.7), 8 | 171.6 |
| 20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right | 0.8154 (5) | 0.819 | – | 178.4 (178.0–178.6), 5 | 175.4 |
| 20261007_7_jiri_v3_powersnatch_5kg_3rep_success_0deg_left (left side) | 0.8103 (15) | 0.818 | – | 175.6 (175.3–175.8), 15 | 171.6 |

Not used:
- `20261007_10_..._fail-bend-elbows_0deg_right`: 0 frames. The bar never got above the nose (failed lockouts) and no standing hips frame was still, so it has no far plate and no k. It is left out of the session scale (its NaN broke the bar-only runs).
- `_5_`/`_6_` (30°/45°): not side-on.

| Pooled | k from far plate (as run) | k = 0.808 (face-corrected) | k = 0.829 (tape + bar) |
|---|---|---|---|
| Direct (2 clips, 43 frames) | 176.0 (175.4–176.6) | 176.6 | 172.2 |
| Eye-based (7 clips, 98 frames) | 176.7 (175.5–178.4) | 178.0 | 173.5 |

The eye-based reading is ~1.3 cm above the direct one. At lockout the head is pushed through and tilted forward, so the head-top offset above the eye taken from standing frames doesn't quite fit. Direct is the primary value.

**Final.** Direct, midpoint of the two k values: (176.6 + 172.2) / 2 = **174.4 → 174.5 cm with shoes**. ± 3 cm = half the k gap (2.2), the lateral offset (1.3) and the floor model (~1), added in quadrature (2.7). Barefoot: −2.5 ± 0.5 cm (lifting-shoe sole and heel; not measured) → **≈ 172 ± 3 cm**.

### Cross-check from an earlier session (distance unknown)

`20261005_6_jiri_v2_standup_10kg_2rep_success_0deg` has standing frames with its own plate. The near plate reads 433 px/m, the same as the spike clips (430–450), so with the same focal length the near plate was at the same depth, and k carries over. This is an assumption: same phone and zoom, same bar. It has no far plate (no lockout), so it was run with `--k 0.811`: **178.4 cm** (IQR 178.0–178.6, n = 47; sole floor 177.1, plate floor 179.7). The two floor estimates differ by 15 px there (vs 0–7 px in the spike clips), so its floor is less certain. It is ~2 cm above the spike direct value at the same k, which is within the ±3 cm. At k = 0.829 it would read ≈ 174.5.

## 4. Visual check

- `prototype/out/20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right/height_sheet.jpg` (8 frames). Red dot and line: head top. Green dot: lowest shoe pixel. Cyan: midline floor from the sole. Magenta: floor from the plate. Yellow: YOLOX box. Checked: the head top sits on top of the hair in every tile, and the sole point is on the bottom edge of the near (green) shoe. The YOLOX box top is far above the head.
- Plated clips (e.g. `prototype/out/20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right/height_sheet.jpg`) show the lockout frames. Yellow dot: near eye (eye-based). Green ellipse: near plate. Magenta circle: far plate. Checked: the far-plate circle sits on the far rim, between the near plate and the head. At full resolution, 3× zoom, the error is < 1 px on a 67 px radius; a 1 px error would move k by ~0.6%.

## 5. Segment lengths (cm, near-side keypoints, standing frames, scale = clip's `px_per_m_mid`, k from the far plate)

| Clip | Frames | Shank | Thigh | Torso | Upper arm | Forearm | Hip–ankle | Ear–ankle |
|---|---|---|---|---|---|---|---|---|
| 20261007_1_..._standup_bar_... (hips) | 40 | 43.0 | 42.7 | 51.0 | 24.2 | 23.9 | 85.3 | 153.0 |
| 20261007_3_..._5kg_..._right (lockout) | 23 | 43.0 | 42.8 | 55.8 | 25.9 | 12.0 | 86.0 | 155.4 |
| 20261007_4_..._squatsnatch_... (lockout) | 17 | 43.5 | 42.6 | 55.6 | 23.8 | 19.0 | 86.2 | 155.6 |
| 20261007_8_..._7-5kg_... (lockout) | 18 | 44.0 | 41.9 | 55.3 | 23.2 | 17.5 | 85.8 | 154.9 |
| 20261007_9_..._10kg_... (lockout) | 12 | 42.9 | 41.7 | 53.7 | 23.7 | 19.4 | 84.5 | 152.7 |
| 20261007_7_..._0deg_left (lockout, left) | 15 | 42.6 | 42.0 | 54.2 | 24.7 | 20.5 | 84.5 | 151.3 |

- Shank (43 ± 0.5), thigh (42 ± 0.5) and hip–ankle (85 ± 1) are stable.
- Torso reads ~5 cm longer at lockout than standing with the bar at the hips. The shoulders are shrugged up at lockout.
- Forearm and upper arm at lockout are foreshortened: the arm points partly toward the camera. Use the standing (`_1_`) values.
- These are keypoint-to-keypoint lengths (RTMPose joint centres), not bony landmarks. They scale with the same k: × 0.975 at k = 0.829.

## 6. Caveats

- k is unresolved (§2); the lifter's measured height resolves it.
- The head top is the top of the hair (curly, a few cm of volume).
- The direct value comes from bar-only clips at the session scale. That assumes the lifter stood over the same floor mark as in the plated clips.
- The shoe offset (2.5 cm) is assumed, not measured.
- The floor model assumes a 10 cm ankle height and a 5 cm half shoe width; an error of ±5 cm in stance or shoe width moves the floor by ~5 px (~1.3 cm). The sole and plate floors agree to 0–7 px, so the real error is likely ≤ 1 cm.
- There is one session and one camera spot (plus `_11_`/`_12_` after the tripod was moved), so this is not a test of repeatability across days.

## Reproduce

```bash
cd prototype
P="20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right 20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right 20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right 20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right 20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right"
for c in $P; do uv run python scripts/studies/body_height.py ../vids/spike/$c.MOV out/$c; done   # ~15 s each
L=20261007_7_jiri_v3_powersnatch_5kg_3rep_success_0deg_left
uv run python scripts/studies/body_height.py ../vids/spike/$L.MOV out/$L --side l
S=$(for c in $P; do printf "out/%s," $c; done); S=${S%,}
for c in 20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right 20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right; do
  uv run python scripts/studies/body_height.py ../vids/spike/$c.MOV out/$c --scale-from $S; done
ALL="$(for c in $P; do printf "out/%s " $c; done) out/$L out/20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right out/20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right"
uv run python scripts/studies/height_summary.py --scale-clips $S $ALL              # k from the far plate
uv run python scripts/studies/height_summary.py --scale-clips $S --k 0.829 $ALL    # tape + bar geometry (also 0.808, 0.824, 0.833)
uv run python scripts/studies/segment_lengths.py out/20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right ...
uv run python scripts/studies/body_height.py ../vids/20261005_6_jiri_v2_standup_10kg_2rep_success_0deg.MOV out/20261005_6_jiri_v2_standup_10kg_2rep_success_0deg --k 0.811
```

Run in zsh, `$P`/`$ALL` need `${=P}`; or run the block in bash.
