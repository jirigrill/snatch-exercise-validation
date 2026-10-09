# 36 — Per-lifter skeleton: filling in the near knee and wrist hidden by the plate

Run 2026-10-08 on the spike session (2026-10-07, `vids/spike/`), side-on (0°, camera on the lifter's right). Why: side-on is the chosen view (`33-d1-views.md`). In it, the near plate hides the near knee around the transition and the near wrist for the whole pull. Those joints feed the knee re-bend / knee-forward markers (A10/A11, `../research/11-technique-markers.md`) and the arm-bend checks.

**Bottom line.**
- **Knee: usable, and better than RTMPose's own guess.** Test: a real plate pasted onto the bar-only clips `_1_`/`_2_`, then RTMPose re-run on those frames (§3). At the transition (bar between knee and hip) the rebuilt knee is off by **0.9–1.2 cm median (p90 1.3–3.5 cm), knee angle 0.6–2.7°**. RTMPose's guess behind the pasted plate is off by **3.2–3.8 cm and 5–8°**, with a consistent bias: knee ~3 cm too far back, angle 5–8° too open. The rebuilt knee meets the proposed ≲2–3 cm criterion, and RTMPose's guess does not.
- **RTMPose's guess invents re-bends; the hybrid knee does not.** Under the pasted plate, RTMPose made a knee dip of ≥ 3° (v2 counts it as a transition) in 2 of 4 pulls where the true knee has none (true dips 0–2.2°). The **hybrid** knee (rebuilt where the knee is hidden and the leg is well conditioned, RTMPose elsewhere, cross-faded) matched the truth in 4/4. On the loaded clips, RTMPose's knee gives a v2 re-bend in 7 of 18 reps and the hybrid in 2 (and shallower). **So A10 from RTMPose's side-on knee is suspect.** Caveat: the bar-only truth has no real re-bend, so detecting a true re-bend (the positive case) is untested.
- **Fixed lengths are not good enough; use a length table.** Thigh and shank are taken from RTMPose's joint centres, so their projected length varies 5–8% with posture. Median per bin of hip–ankle distance (`LengthTable`) beats a fixed standing length (transition 1.0–1.4 vs 1.7–3.3 cm) and beats "max/p90 over the lift" (2.8–4.8 cm). A ±2% length error costs ~+1 cm at the transition and 3–6 cm near a straight leg.
- **Ill-conditioned near a straight leg, as expected.** The knee moves 1.0–1.6 px per px of length error at the transition (knee 120–140°) and 3–13 px/px above ~160°. Clipping (the circles don't meet) happens in 15–87% of second-pull frames, and errors there reach 6 cm. Side-on, the knee is never hidden above ~150° (0% hidden in the second pull), so the hybrid only rebuilds where the gain is ≤ 2.
- **Loaded clips (agreement, no truth):** rebuilt vs RTMPose's hidden knee at the transition differ by 1.7–2.7 cm median (C1 lengths), and the rebuilt knee sits **+0.1 to +2.4 cm forward, 0.6–5.9° more bent**. That is the same direction as RTMPose's bias in the paste test.
- **Wrist from the hub: works with a perspective-aware offset.** wrist ≈ hub + o₀ + B·(hub − image centre), with B ≈ −0.08 in y (the hand is deeper than the plate, so it projects nearer the image centre). Leave-one-pull-out error vs the visible wrist (collar as the hub stand-in): **0.4–2.7 cm median** (constant offset: 0.7–6.4 cm). In the paste test it beats RTMPose's wrist guess (0.4–2.7 vs 2.1–7.1 cm). Wrist–hub ≈ (+2, −14 … −16) cm, but it shrinks to −9 cm in the second pull (the wrist flexes over the bar), so its stability is ~1–3 cm, not < 1 cm.
- **Elbow (optional):** rebuilt from shoulder + true wrist, the position is within 1–3 cm, but the elbow angle is useless (±5–11°, gain 5–8, 10–100% clipped): the arm is near straight, so its angle is ill-conditioned. Side-on the elbow is visible above the plate anyway.

## 1. Method

Code: `prototype/src/snatch/studies/skeleton.py` (+ `tests/test_skeleton.py`), scripts `prototype/scripts/studies/skeleton_{camera,validate,wrist,paste,loaded,sheets}.py`. Outputs: `prototype/out/skeleton/`. Near side = right (r_* keypoints). Keypoints are smoothed (Savitzky–Golay 0.1 s) as in the rest of the pipeline.

| Step | What |
|---|---|
| Knee | Circle of thigh length around the near hip ∩ circle of shank length around the near ankle (`two_circle_knee`). Take the solution in front of the hip–ankle line, toward the facing direction (`height.facing`). If the circles don't meet, put the knee on the line (`clipped`). Conditioning: `knee_gain` = px of knee per px of thigh-length error. |
| Lengths | Three options. **fixed-standing**: median over upright frames (knee and hip > 165°). **fixed-p90**: 90th percentile over the lift. **table**: median thigh and shank in 12 bins of r = d / d_standing, d = hip–ankle (`length_table`, `LengthTable`), read only from visible inputs. The table carries to another clip by scaling with that clip's standing hip–ankle (`scaled`). |
| Hybrid | `fill_hidden`: rebuilt knee where the knee keypoint is inside the plate outline and the gain is ≤ 2, RTMPose elsewhere. A 25-frame (0.1 s) moving-average weight, so the switch adds no step. |
| Wrist | wrist = hub + offset, constant (`fit_offset`) or linear in the hub's image position (perspective). |
| Phases | From the bar (wrist on `_1_`/`_2_`, hub on the loaded clips; `pull_windows`, `phase_labels`). **setup** 0.25 s before liftoff; **first pull** liftoff → bar at the near knee; **transition** bar at knee → bar at hip; **second pull** bar at hip → peak knee extension; **catch** → v1/v2 lockout. These are windows, not the v2 transition frame. |
| Scale | cm = px / 352.8 × 100 (the session body scale, doc 35, k from the far plate). At k = 0.829, multiply by 0.975 (doc 35's ±2.5% ambiguity). The knee is ~10 cm nearer than the body midline, so its true scale is ~3% larger. All fits are in px. |

## 2. Camera between clips (`skeleton_camera.py`)

The background was matched (SIFT, similarity transform) against `_1_`'s first frame. The lifter and the floor zone were masked out.

| Clip | bg shift px | bg scale | bg roll | plate r at rest px | standing hip–ankle px (÷ `_1_`) |
|---|---|---|---|---|---|
| 20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right | 0, 0 | 1.000 | 0 | – | 304.4 (1.000) |
| 20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right | +24, −7 | 1.001 | +0.25° | – | 306.3 (1.006) |
| 20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right | +40, +1 | 0.999 | −0.22° | 95.6 | 302.3 (0.993) |
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | +25, −5 | 1.002 | −0.09° | 95.6 | 306.2 (1.006) |
| 20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right | −32, −7 | 1.004 | +0.09° | 97.5 | 307.8 (1.011) |
| 20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right | −20, −9 | 1.004 | +0.12° | 97.3 | 307.2 (1.009) |
| 20261007_10_jiri_v3_powersnatch_10kg_3rep_fail-bend-elbows_0deg_right | −22, −11 | 1.004 | +0.15° | 99.1 | 311.9 (1.025, n 92) |
| 20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right | +61, +29 | 0.990 | +1.29° | 101.8 | 315.8 (1.038) |
| 20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right | +60, +28 | 0.991 | +1.22° | 98.3 | 310.4 (1.020) |

- **`_1_`–`_4_`: same camera spot.** The background moves 20–40 px with scale 1.000 ± 0.002, i.e. the phone was panned by ~1° (or the stabilisation crop shifted) between takes. A pan does not change the lifter's px lengths.
- **`_8_`–`_10_`: back on the tape marks**, scale +0.4%.
- **`_11_`/`_12_`: the tripod moved**: 1.3° roll, scale −1%, hub at rest 40–50 px lower. This confirms doc 35's lens height change.
- **What decides px lengths is the lifter's depth, not only the camera.** Transfer `_1_`'s lengths with the clip's standing hip–ankle ratio (0.993–1.038; the posture is the same: upright, knee and hip > 165°). Without the ratio, `_11_` would be 3.8% off, which is worse than the ±2% test in §3. The shank alone reads 3–5% longer in `_8_`–`_12_` than in `_1_` (157–162 vs 154 px), so a per-clip table from the clip's own clear frames is the better choice where it has enough frames (§4).

## 3. Validation on the bar-only clips (truth = the visible knee)

`_1_` = 20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right (3 pulls to standing). `_2_` = 20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right (1 power snatch). Near-side scores are 0.76–0.89 (p10–p50) for hip, knee and ankle. `sheet_c1.jpg` shows the observed knee on the knee in every tile.

### 3a. Inputs clean (truth hip/ankle), lengths from other pulls

`_1_` pull k uses lengths from `_1_` without pull k (leave one pull out); `_2_` uses `_1_`. Median / p90 cm.

| Test | Model | setup | first pull | transition | second pull | catch |
|---|---|---|---|---|---|---|
| `_1_` pulls 1–3 | table | 0.2–1.4 / ≤ 1.6 | 0.7–1.1 / ≤ 1.7 | **1.1–1.4 / ≤ 1.7** | 1.3–2.4 / ≤ 5.4 | – |
| `_1_` pulls 1–3 | fixed-standing | 1.6–2.3 | 1.5–2.5 | 1.7–2.9 / ≤ 3.8 | 1.7–2.8 | – |
| `_1_` pulls 1–3 | fixed-p90 | 1.8–3.5 | 1.9–2.5 | 3.2–3.9 | 2.2–7.2 | – |
| `_2_` (lengths `_1_`) | table | 2.0 / 2.1 | 2.1 / 2.5 | **1.2 / 1.9** | 6.5 / 11.5 | 5.6 / 6.9 |
| `_2_` (lengths `_1_`) | fixed-standing | 2.6 | 3.6 | 2.8 / 3.6 | 6.3 | 6.6 |
| `_2_` (lengths `_1_`) | fixed-p90 | 3.1 | 4.2 | 2.8 | 2.5 | 7.3 |

Knee-angle error (table, transition) is 0.4–2.3°.

The `_2_` second pull and catch are bad, for two reasons. The leg is near straight (139–165°, 41% clipped). In the receiving squat, the thigh's projected length at a given hip–ankle distance differs from the deadlift-like setup that `_1_` calibrates. Side-on, the knee is visible in both phases (§4), so no fill is needed there. See `validate_curves.png`: the rebuilt angle tracks the observed one to ~160°, then sticks at 180°.

### 3b. Robustness (table model, transition, median cm)

| Case | `_1_` pulls (lengths `_1_` others) | `_2_` (lengths `_1_`) |
|---|---|---|
| clean | 1.1–1.4 | 1.2 |
| raw (unsmoothed) hip/ankle | 1.2–1.4 | 1.3 |
| noise σ 2 px on hip and ankle | 1.4–1.6 | 1.4 |
| noise σ 5 px | 2.4–2.9 | 1.7 |
| lengths +2% | 2.2–3.2 | 2.2 |
| lengths −2% | 2.1–2.5 | 2.1 |

Conditioning (table): gain at the transition is 1.2–1.6 px/px (p90 ≤ 2.0) with 0% clipped. In the second pull it is 1.0–4.2 (p90 up to 13.9) with 15–87% clipped.

### 3c. Real occlusion: plate pasted, RTMPose re-run (`skeleton_paste.py`)

A real 5 kg bumper disc was cut from `_3_` frame 1105 and resized to r = 96 px, the loaded clips' rest radius. It was pasted on the tracked near collar (§5) in every pull frame of `_1_`/`_2_`, and RTMPose-x was re-run on those frames (1179 frames). The skeleton uses the **pasted run's** hip and ankle. These are themselves partly hidden: of the hidden-knee frames, 9–20% have the hip inside the disc at the transition and 31–67% have the ankle inside in the first pull. Their guesses moved 0.3–1.9 cm. See `paste_sheet.jpg` (green = truth, red = RTMPose, cyan = skeleton).

| Clip, pull | Phase | Knee hidden | RTMPose knee cm (p90) | Skeleton cm (p90) | Angle err RTMPose / skeleton | RTMPose bias fwd, angle |
|---|---|---|---|---|---|---|
| `_1_` 1 | transition | 100% | 3.7 (4.5) | 1.2 (3.5) | 5.1° / 2.6° | −2.8 cm, +5.1° |
| `_1_` 2 | transition | 97% | 3.6 (4.4) | 1.2 (3.2) | 5.5° / 1.9° | −3.0 cm, +5.5° |
| `_1_` 3 | transition | 98% | 3.8 (5.8) | 0.9 (2.4) | 7.8° / 2.7° | −3.8 cm, +7.8° |
| `_2_` 1 | transition | 100% | 3.2 (4.9) | 1.0 (1.3) | 6.5° / 0.6° | −3.2 cm, +6.5° |
| `_1_` 1–3 | first pull | 39–97% | 0.6–1.6 | 1.0–1.5 | 0.8–1.3° / 1.2–2.5° | ≤ 1 cm |
| `_2_` 1 | first pull | 100% | 2.0 (2.6) | 1.5 (1.8) | 2.5° / 0.8° | −1.8 cm, +2.5° |

In the first pull the knee is at the plate's rim and RTMPose is about as good as the skeleton. At the transition the knee is behind the plate's centre, and RTMPose falls back to a straighter leg.

Re-bend (largest knee-angle dip after the bar passes the knee, setup → peak; v2 counts ≥ 3°):

| Pull | Truth | RTMPose (pasted) | Skeleton alone | Hybrid | Hybrid transition err |
|---|---|---|---|---|---|
| `_1_` 1 | 0.0° | 0.0° | 0.0° | 0.0° | 1.2 cm / 2.6° |
| `_1_` 2 | 2.2° | 2.3° | **6.1°** (near-straight artefact after the bar passes the hip) | 2.3° | 1.1 cm / 1.7° |
| `_1_` 3 | 0.0° | **4.4°** | 0.0° | 0.0° | 0.9 cm / 2.0° |
| `_2_` 1 | 1.4° | **5.9°** | 0.9° | 0.9° | 1.0 cm / 0.7° |

The skeleton alone can also invent a dip, near a straight leg. That is why the hybrid gates on gain ≤ 2 and uses RTMPose where the knee is visible.

## 4. Loaded clips: agreement, not accuracy (`skeleton_loaded.py`)

Hidden = the raw near keypoint inside the tracked plate outline (`views.ellipse_dist` < 1). Percent of phase frames, knee / hip / ankle:

| Clip | setup | first pull | transition | second pull | catch |
|---|---|---|---|---|---|
| `_3_` | 0 / 0 / 100 | 44 / 0 / 66 | 67 / 34 / 0 | 0 / 100 / 0 | 0 / 0 / 0 |
| `_4_` | 0 / 0 / 100 | 44 / 0 / 63 | 66 / 39 / 0 | 0 / 99 / 0 | 0 / 1 / 0 |
| `_8_` | 0 / 0 / 100 | 46 / 0 / 57 | 69 / 39 / 0 | 0 / 100 / 0 | 0 / 2 / 0 |
| `_9_` | 0 / 0 / 100 | 46 / 0 / 55 | 65 / 48 / 0 | 0 / 100 / 0 | 0 / 3 / 0 |
| `_10_` | 0 / 0 / 100 | 48 / 0 / 61 | 68 / 35 / 0 | 0 / 64 / 0 | – |
| `_11_` | 0 / 0 / 100 | 40 / 0 / 42 | 62 / 8 / 0 | 0 / 40 / 0 | 0 / 1 / 0 |
| `_12_` | 0 / 0 / 100 | 47 / 0 / 63 | 72 / 1 / 0 | 0 / 46 / 0 | 0 / 0 / 0 |

- The plate hides the ankle at setup, the knee from mid first pull through the transition, and the hip in the second pull. So the skeleton's inputs are partly guesses too: of the hidden-knee frames, 0–21% have the hip or ankle hidden. The paste test (§3c) has the same mix, so its errors include this.
- The knee is never hidden in the second pull or the catch, where the leg is straight or the bar is overhead. This is where the skeleton would be ill-conditioned (straight leg) or off (squat, below).

Rebuilt vs RTMPose's knee in hidden frames (median cm / p90; forward = rebuilt minus RTMPose along the facing direction; angle = rebuilt − RTMPose):

| Clip | Transition, C1 lengths | fwd | angle | Transition, own lengths | First pull, C1 lengths |
|---|---|---|---|---|---|
| `_3_` | 2.3 / 3.7 | +1.5 | −4.1° | 1.7 / 2.4 | 3.5 / 5.9 |
| `_4_` | 2.0 / 3.7 | +1.2 | −3.1° | 1.5 / 3.0 | 4.3 / 5.9 |
| `_8_` | 2.3 / 4.2 | +1.8 | −4.5° | 2.0 / 3.8 | 5.0 / 6.5 |
| `_9_` | 2.7 / 4.6 | +2.4 | −5.9° | 2.2 / 3.9 | 3.1 / 4.9 |
| `_10_` | 2.3 / 3.0 | +2.1 | −5.1° | 1.8 / 3.0 | 3.8 / 6.0 |
| `_11_` | 1.7 / 4.0 | +0.1 | −0.6° | 2.7 / 4.0 | 2.8 / 4.6 |
| `_12_` | 2.0 / 3.2 | +1.5 | −3.7° | 2.9 / 3.5 | 4.3 / 5.7 |

- **The direction matches the paste test:** RTMPose behind the plate puts the knee back and the leg straighter. On `_11_`/`_12_` (camera moved, hip barely hidden) the two agree best.
- **The far knee is no reference.** It is 3–5 cm from both, being the other leg at another depth.
- **First pull: 3–5 cm apart.** This is a mix of the hidden ankle (55–66% of first-pull frames) and the knee on the plate's rim (RTMPose is fine there in §3c). Not usable for a marker without a visible ankle.
- **Own lengths (`_3_`–`_12_` clear frames: knee, hip and ankle outside the outline, score ≥ 0.6).** These cover only standing and the catch. The transition bins (r 0.6–0.9) are thin, so the table interpolates there. They match `_1_`'s ×-scaled table to within ~5 px, except the shank, which is 3–5% longer in `_8_`–`_12_`.
- **Re-bend (v2 transition from the knee angle, hidden-only fill):** RTMPose gives a transition in 7/18 reps (`_3_` r1 3.1°, r2 4.9°; `_4_` r1 8.2°; `_8_` r1 8.1°; `_9_` r1 13.7°, r2 5.0°; `_11_` r1 3.3°). The hybrid with C1 lengths gives 2/18 (`_4_` r1 4.6°, `_9_` r1 8.1°), and with own lengths the same 2 (4.8°, 8.7°). Given §3c, the 5 that disappear are likely plate artefacts. That is a judgement, not proven: no truth here.

**Abduction / deep squat.** Projected length at the catch bottom (lowest hip ± 0.1 s, knee visible) ÷ standing:

| Clip | Knee at bottom | Thigh | Shank |
|---|---|---|---|
| `_4_` squat snatch | 91° | **0.83** | 0.98 |
| `_3_`, `_8_`, `_9_`, `_11_`, `_12_` power | 99–118° | 0.88–0.92 | 0.97–1.03 |

- The thigh shortens by 8–17% in the receiving position: the knee goes out, so the thigh leaves the image plane, and the hip keypoint moves. A fixed standing thigh would be badly wrong there. The `_1_` table (deadlift posture, 0.95 at small r) still errs 3–4 cm in the catch, while the clip's own table errs ~1 cm.
- The knee is visible in the catch, so this matters only if the skeleton is used beyond the hidden window. **The length depends on the posture, not just on d.** A table calibrated on pulls holds for pulls only.

## 5. Wrist from the hub (`skeleton_wrist.py`; paste test §3c)

- **No calibration is possible on the loaded clips.** The near wrist is inside the plate outline in 100% of pull frames (wrist–hub ~15 cm < r ≈ 22 cm), so the offset can't be measured where the plate is. RTMPose's guessed wrist − hub there is (+1.9…+4.5, −13.7…−16.1) cm, robust SD (1.0–1.8, 2.7–3.5) cm.
- **Stand-in on `_1_`/`_2_`: the near collar of the empty bar,** tracked by template matching, checked by eye in `wrist_sheet.jpg`. It sits where the plate's inner face would be, ~3 cm deeper than the outer face that `plate.npz`'s hub follows. That limits the result: the offset transfers up to a near-constant shift, and the stability is what carries over.

| Pull | Phase | Wrist − collar cm (x, y) | Robust SD | Constant offset err (LOO) | Perspective-linear err (LOO) |
|---|---|---|---|---|---|
| `_1_` 1–3 | setup | +1.5…+2.0, −15.7…−16.4 | 0.1–0.2 | 1.5–3.0 | 0.9–1.9 |
| `_1_` 1–3 | first pull | +2.4…+2.8, −15.1…−15.8 | 0.3–0.4 | 0.8–2.5 | 0.8–1.8 |
| `_1_` 1–3 | transition | +2.4…+3.9, −12.6…−13.3 | 0.2–0.4, 1.1–2.2 | 2.1–2.3 | 0.6–2.7 |
| `_1_` 1–3 | second pull | −0.3…+3.0, −9.2…−10.7 | 0.5–2.1 | 2.7–6.4 | 0.8–2.3 |
| `_2_` (fit `_1_`) | setup → second pull | +0.2…+2.8, −8.6…−16.2 | ≤ 1.8, ≤ 3.3 | 0.7–6.3 | 0.4–1.9 |

- Linear fit: dy/dY = −0.071…−0.082 and dx/dX = −0.13…−0.26. The y coefficient is the expected perspective factor 1 − Z_plate/Z_hand ≈ 0.08 (grip ~0.43 m, plate ~0.7 m from the bar centre, 4 m camera). The x coefficient also absorbs the wrist flexing as the bar moves in (second pull).
- In the paste test, hub + linear offset gets the hidden wrist within 0.4–2.7 cm (catch: 7.1 cm, not fitted there). RTMPose's guess is 2.1–7.1 cm off. This matters for D2 (`armbend.py` uses the hub directly, not the wrist), and only if a shoulder–elbow–wrist angle is wanted.

## 6. Decision

| Question | Answer |
|---|---|
| Rebuilt knee at the transition ≲ 2–3 cm and stable? | **Yes**: 0.9–1.4 cm median, p90 ≤ 3.5 cm (paste test and clean); ±2% length → ~2–3 cm; 2 px noise → +0.3 cm. |
| Is RTMPose's own guess as good? | **No**: 3.2–3.8 cm, biased back / straighter by 5–8°, and spurious ≥ 3° re-bends in 2/4 pulls. |
| Use for A10/A11? | **Yes, as the hybrid knee** (`fill_hidden`, gain ≤ 2), with the length table from a bar-only calibration clip at the same camera position and lifter depth (rescaled by standing hip–ankle), or the clip's own clear frames. A10's v2 transition should be recomputed from the hybrid knee. The re-bend's true-positive case is still to be tested. |
| Wrist? | hub + perspective-linear offset, ~1–2 cm. Calibrate it per lifter on a bar-only clip (needs the collar or bar-end tracker), not on loaded clips. |
| Elbow? | Not from the skeleton (angle ±5–11°); it is visible side-on. |

## 7. Caveats

- One lifter, one session, 4 bar-only pulls as truth (3 deadlift-like, 1 power snatch). None has a real knee re-bend, so the hybrid has only been shown not to invent one, not to find one.
- **Truth = RTMPose on the unoccluded knee.** That is a joint-centre estimate with its own error (~1 cm jitter, doc 33), not a marker.
- The paste test uses one plate texture, no far plate, no shadow or blur, the clean clip's YOLOX boxes, and a plate centred on the collar + 6 px. The hidden share at the transition is higher than on the real clips (97–100% vs 62–72%), so it is a slightly harder case.
- The table is posture-specific (pull vs squat catch, §4). A lifter whose setup differs a lot from the calibration clip (e.g. hips much lower) needs its own calibration.
- cm use the doc-35 body scale (k ambiguity ±2.5%). The knee is nearer than the body midline (~+3% scale). All decisions are made on px ratios, so this does not change any verdict.
- Phase windows here are bar-position windows (bar at knee → bar at hip), not v2 event frames.

## Reproduce

```bash
cd prototype
uv run python scripts/studies/skeleton_camera.py      # camera / depth check            (~1 min) -> out/skeleton/camera.md
uv run python scripts/studies/skeleton_validate.py    # synthetic occlusion, C1/C2     (~10 s)  -> validate.md, validate_curves.png
uv run python scripts/studies/skeleton_wrist.py       # collar track, wrist offsets     (~1 min) -> collar_{1,2}.npz, wrist.md, wrist_sheet.jpg
uv run python scripts/studies/skeleton_paste.py --rerun   # pasted plate + RTMPose (~2 min; without --rerun it reuses paste_{1,2}.npz) -> paste.md, paste_sheet.jpg
uv run python scripts/studies/skeleton_loaded.py      # loaded clips: hidden %, agreement, re-bend, lengths, wrist (~30 s) -> loaded.md
uv run python scripts/studies/skeleton_sheets.py      # sheet_c1.jpg, sheet_loaded.jpg  (~1 min)
uv run pytest
```

Visual checks done: `sheet_c1.jpg`: the observed knee is on the knee, and the rebuilt knee is within ~1–2 cm in all 9 tiles. `sheet_loaded.jpg`: hidden-knee frames, where the RTMPose (red), rebuilt-C1 (cyan) and rebuilt-own (yellow) knees all sit inside the plate within a few cm, and the rebuilt ones are slightly forward of RTMPose. `paste_sheet.jpg`: mid-transition, the red RTMPose knee sits behind the true knee and cyan sits on it. `wrist_sheet.jpg`: the collar track is on the collar ring in all pull frames.
