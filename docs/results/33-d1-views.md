# 33 — D1 camera view: side-on vs 30° vs 45°

Ticket: [#22](https://github.com/jirigrill/snatch-exercise-validation/issues/22) (D1 in `../research/12-feasibility-grill.md` §5; rule in `../recording-protocol.md` § Spike session). Run 2026-10-08 on the spike session SP1 (2026-10-07).

**Bottom line.**
- **Visibility: 45° passes, 30° fails.** At 45° the near hip, knee and wrist are in clear view at the transition and through the pull in all 3 reps (keypoint scores 0.85–0.95). At 30° the near hip and knee sit on the plate's rim at the transition and the near wrist is behind the plate for the whole pull, which is the same problem as side-on.
- **Metric part: not tested.** The static roll test (50 ± 1 cm) and the vertical static test were not filmed. **The proxy below is not that test.**
- **The proxy says the oblique bar path is not metric as it stands.** The plate tracker's outline is on the rim side-on, but at rest it is about 9% too small at 30° and about 22% too big at 45° (checked by eye on the full-resolution frame). Peak bar height reads 147.7 cm at 30° against 135.8 cm side-on, for the same lifter and load in back-to-back sets. That is 12 cm, about 4× the rep-to-rep SD, and it matches the 9% scale error. A 9% scale error is 4.5 cm on a 50 cm roll, so 30° would fail the ±1 cm rule. At 45° the hub is lost on the lifter's dark clothes and the background in the second pull even with a pose prior, so no 45° bar marker can be trusted.
- **D1 verdict: no-go for now. Side-on stays for the gate set.** No oblique view meets both parts: 45° shows the joints but loses the bar, and 30° does neither. 45° is the only candidate worth a second look, and only after the static tests are filmed and the tracker is fixed for 45° (§5).

Clips (`vids/spike/`, squat snatch, bar + 5 kg = 25 kg, 3 reps each, camera on the lifter's right, 240 fps, 1080 × 1920):

| View | Clip | Set |
|---|---|---|
| 0° side-on | 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | 4 |
| 45° | 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | 5 |
| 30° | 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | 6 |

Only one pass was filmed (0 → 45 → 30), not the interleaved double pass, so view and set order (fatigue, warm-up) are confounded. 3 reps per view.

Code: `prototype/src/snatch/studies/views.py` (+ `tests/test_views.py`), `prototype/scripts/studies/{d1_views,d1_sheets,d1_near_plate}.py`. Numbers: `prototype/out/d1_views.md`, `prototype/out/<clip>/d1_views.json`; path plot `prototype/out/d1_paths.png`.

## 1. Pipeline notes for these clips

- **Camera distance.** The plate radius is ~97 px side-on (px/m 429). The camera was tape-measured at 4 m from the bar centre (lifter, 2026-10-08), and this fits the optics: the near plate is ~0.7 m nearer than the bar centre, so 429 px/m × ~3.3 m gives a focal length of ~1400 px, as expected for the iPhone main camera at 1080p. The 2026-10-01 clips (~173 px) were filmed from closer, at a distance nobody measured. The default range 110–260 px was tuned on those clips. The default search range (110–260 px) then locked onto the dumbbell rack: 53% found, 116 jumps. It passes with `--radius 70:140` (100% found, 0 jumps).
- **`run_all.sh` lane 2 skipped these clips.** `touch out/$c/.rerun_plate` fails when the clip's out dir doesn't exist yet, and lane 2 starts before lane 1 creates it. I ran the plate step by hand (commands below). Logged in `out/run_all/<clip>.log`.
- **Oblique plate runs** (`ellipse`): 30° with `--radius 60:120`, 45° with `--radius 45:72`. Both fail the sanity check. At 30° the tracker switches to the far plate, which is in view in oblique shots: 20% of lift frames. At 45° it follows the far plate or a stack of black sandbags behind the lifter. 50:110 found the sandbags (79% found); 45:72 found the far plate (97% found, but the wrong plate).
- **Near-plate prior (diagnostic only).** `d1_near_plate.py` runs the same `plate.detect` on masked frames. Inside each lift, only pixels within 3.5 × r_max of the near wrist, on the near wrist's side of the line between the wrists, are kept. Outside the lifts nothing is tracked. The output is `plate_near.npz`; `plate.npz` is not touched. This uses the wrists, which `snatch.plate` deliberately avoids, so it is not a pipeline step. All oblique numbers below use it.
- **Phases: v1 (wrists) for all three views**, so the views are compared like for like (as in #15's off-axis rule). v2 needs a hub that is valid outside the lifts, and that fails at 30°/45°. Of the side-on v2 reps, 2 of 3 have no transition (the squat-snatch issue, #26). Where there is no transition, the transition window is centred on the frame where the hub passes the knees.

## 2. Keypoints at the transition and in the pull

Near side = right (camera on the right). Windows per rep: **transition** = ±0.1 s around the v1 transition (knee re-bend), or around the hub passing the knees; **pull** = liftoff → peak knee extension. **Behind plate** = % of window frames with the near keypoint inside the tracked plate outline (the plate is nearest to the camera, so that joint is hidden and its keypoint is a guess). Score = mean RTMPose score, near (far). Jitter = RMS of raw minus smoothed (Savitzky–Golay 0.1 s), in mm at the plate's scale. Mean over 3 reps.

**Transition**

| View | Hip: behind % / score | Knee: behind % / score | Wrist: behind % / score | Hip jitter mm |
|---|---|---|---|---|
| 0° | 25 / 0.73 (0.69) | **81** / 0.76 (0.71) | **100** / 0.71 (0.65) | 3.6 |
| 30° | **48** / 0.71 (0.73) | **53** / 0.79 (0.85) | **99** / 0.75 (0.88) | 6.3 |
| 45° | 21* / 0.75 (0.75) | 23* / 0.85 (0.88) | 37* / 0.88 (0.93) | 8.7 |

**Pull**

| View | Hip | Knee | Wrist | Elbow | Shoulder |
|---|---|---|---|---|---|
| 0° | 26 / 0.71 | 57 / 0.72 | **100** / 0.69 | 0 / 0.78 | 0 / 0.79 |
| 30° | 22 / 0.73 | 21 / 0.80 | **100** / 0.72 | 1 / 0.83 | 0 / 0.79 |
| 45° | 11* / 0.76 | 12* / 0.85 | 24* / 0.87 | 10* / 0.89 | 2* / 0.82 |

\* **45°: these "behind" values are false hits.** In those frames the 45° near-plate track sits on the lifter's shorts or shirt (seen in `d1_zoom.jpg` and `plate_near_check.jpg`). In the frames themselves, the near plate is clear of the near leg, and the near hand is beside the plate's rim, not behind it.

**Visual check** (`out/<clip>/d1_sheet.jpg`: setup, hub at knee, transition, mid 2nd pull, peak extension per rep; `d1_zoom.jpg`: full-resolution crops at the transition and mid 2nd pull, raw and with keypoints):

| View | Near hip + knee at the transition | Near wrist in the pull |
|---|---|---|
| 0° | knee behind the plate in all 3 reps; hip at the plate's edge | behind the plate in all 3 |
| 30° | both on the plate's rim, partly hidden, in all 3 reps | behind the plate (at the rim only overhead) |
| 45° | **both in clear view** in all 3 reps | **in clear view**, beside the plate |

Other checks:
- **Left/right swaps: none** in any view (raw near keypoint closer to the far track than to its own, tracks ≥ 5 cm apart: 0% of frames).
- **Hip jitter grows with angle** (3.6 → 6.3 → 8.7 mm at the transition), while the knee, wrist and elbow get steadier at 45° (1.4–1.7 mm against 3.5–4.4 side-on).
- **Segment lengths are not a plausibility test off-axis.** The projected thigh shortens as the leg turns: CV 4.9% at 0°, 12.4% at 30°, 20.2% at 45°. Shank: 2.5 / 5.5 / 4.2%.
- **The far arm shows in oblique views.** Far wrist score 0.88 (30°) and 0.93 (45°), against 0.60–0.65 side-on. Relevant to D2.
- Joint angles at 45° are projected. Because the sagittal planes are parallel, the same horizontal stretch (1/cos θ) that rectifies the plate also rectifies the body under weak perspective. That has not been validated.

## 3. Plate tracking

| View | Plate file | Found (in lifts) | Far plate / other in lifts | Jumps | Hub jitter at rest x/y | View angle, rest median (p10–p90 all frames) | By eye on a rest frame |
|---|---|---|---|---|---|---|---|
| 0° | `plate.npz` (`--radius 70:140`) | 100% (100%) | 0% | 0 | 0.1 / 0.2 mm | 0° (circle) | rim fit, r 96 px both |
| 30° | `plate_near.npz` (60:120) | 90% of lift frames | 6% | 4 | 7.3 / 8.5 mm | **30.2°** (26–38) | ~34° (b/a 0.83); tracked major 78 px vs **~86 px** true (**−9%**) |
| 45° | `plate_near.npz` (50:100) | 86% of lift frames | many on body/background | 4 | 15.8 / 15.9 mm | **38.7°** (23–42) | ~43° (b/a 0.73); tracked major 91 px vs **~74 px** true (**+22%**), centre ~9 cm off toward the sleeve |

Without the prior (`plate.npz`): at 30°, 93% found but 29 jumps and 20% of lift frames on the far plate. At 45°, the far plate or the sandbags, as in §1.

- **Measured vs nominal angle.** 30° comes out right (30.2°), and 45° comes out at ~39–43°. The tape chord setup is within ±5° of nominal (protocol: "±5° is enough"). The per-frame spread is wide (23–42° at 45°), so a single frame's b/a is not usable for rectification; only a clip median is.
- **Why oblique fails** (crops in `plate_check.jpg`, `plate_near_check.jpg`): both plates are in view, the rim against the dark floor is faint, the protruding sleeve adds rim-like edges at 45°, and in the second pull the near plate crosses the lifter's dark shorts and shirt.
- Side note: on its existing `plate.npz`, the 2026-10-05 "30deg" clip `20261005_9_jiri_v2_powersnatch_10kg_3rep_fail_not_fast_under_30deg` measures ~12° (b/a, rest median), so the earlier "30°" clips were close to side-on. (One-off check, not saved.)

## 4. Proxy for the static metric test (not the 50 ± 1 cm test)

**This is not the D1 metric test.** The static roll and vertical static tests were not filmed. The proxy compares the rectified bar path of the same lifter, load and lift across the three back-to-back sets. A real difference in technique between sets cannot be told apart from a measurement error. Rectification: x × major/minor of the clip's resting outline (= 1/cos θ), y as is, scale = major axis / 0.45 m (camera level; the resting outline's tilt of −18° and −46° comes from looking down at the plate and is not used). v1 phases. Mean ± SD over 3 reps; [unrectified].

| View | Peak height above setup, cm | Hub x at 25 cm up | at 50 cm up | at 75 cm up | Xloop cm | drop cm |
|---|---|---|---|---|---|---|
| 0° | **135.8 ± 2.1** | −0.5 ± 0.3 | −1.9 ± 1.6 | −1.0 ± 1.9 | 11.9 ± 2.2 | 12.0 ± 3.6 |
| 30° | **147.7 ± 3.4** | +4.1 ± 1.1 [+3.5] | +3.5 ± 1.4 [+3.0] | +3.3 ± 1.8 [+2.8] | 42 ± 24 | 64 ± 45 |
| 45° | 117 ± 39 | +10.3 ± 11.8 | +4.2 ± 8.3 | +39.7 ± 5.8 | 23 ± 28 | 78 ± 39 |

- **Vertical scale at 30° is off by ~9%.** Peak height is +11.9 cm (+8.8%) against side-on. The tracked resting major axis is 78 px against ~86 px by eye (−9%). With the by-eye scale, 30° peak height becomes ~135 cm, which matches side-on. **At ±1 cm on 50 cm, the scale has to be right to 2%. Side-on it is (rim fit by eye), and the oblique tracker is 9–22% off.**
- **Horizontal: the first pull agrees to ~4–6 cm, beyond the rep SD (1–2 cm).** 30° puts the bar 3–4 cm in front of the setup point where side-on has it 0.5–2 cm behind. Scale alone doesn't explain this (×1.09 on a few cm). Possible causes: a hub offset from a tilted or partial fit, sideways bar travel (sin 30° = 0.5 of it lands in x), perspective, or a real difference between sets. The test can't tell them apart.
- **Second pull, turnover and catch (X2, Xloop, Xnet, drop) are unusable at 30° and 45°.** The hub is lost or wrong where the plate crosses the torso and head, and gaps get filled across it (`d1_paths.png`). Side-on, the whole path is smooth and repeatable.
- **Rep-to-rep spread at rest** (hub before liftoff, x/y): 0° 2.9/2.2 cm, 30° 7.2/0.4 cm, 45° 2.2/0.7 cm. Mostly where the bar was set down.

## 5. D1 verdict

| Part of the rule | 30° | 45° |
|---|---|---|
| Near hip **and** knee at the transition | **fail** (on the plate rim, ~50% of frames inside the outline) | **pass** (clear in 3/3 reps) |
| **or** near wrist in the pull | **fail** (behind the plate, 100%) | **pass** (clear, beside the plate) |
| Rectified hub moves 50 ± 1 cm (static test) | **not tested** (not filmed); proxy: scale −9%, ≈ 4.5 cm on 50 cm → would fail | **not tested**; proxy: tracker loses the near plate mid-pull, scale +22% → would fail |
| **D1** | **no-go** | **no-go as it stands** (visibility yes, metric no) |

**Recommendation for the gate set: side-on stays.** Also:
- **At the protocol's 4 m the plate radius is ~97 px**, not the ~173 px of the 2026-10-01 clips. The default plate search (110–260 px) has to change to ~70–140 px for all clips filmed to the protocol.
- **If 45° is to be reopened** (it is the only view that shows A10/A11 and the wrist):
  1. film the static roll and vertical tests from 45°;
  2. make the oblique outline fit reliable: a near-plate prior that `snatch.plate` accepts, a scale check against the vertical diameter, and handling of the sleeve and clothing edges;
  3. repeat with interleaved sets.

  Until then, A10/A11 and arm bend stay "more work" and D2 (shoulder-to-hub, side-on) is the route for arm bend.

## Reproduce

```
cd prototype
# plate, by hand (run_all.sh lane 2 skipped these clips; radius for the 4 m camera)
uv run python scripts/track_plate.py ../vids/spike/20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right.MOV out/20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right --radius 70:140
uv run python scripts/track_plate.py ../vids/spike/20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right.MOV out/20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right ellipse --radius 60:120
uv run python scripts/track_plate.py ../vids/spike/20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right.MOV out/20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right ellipse --radius 45:72
# near-plate prior, oblique only (~10 min each)
uv run python scripts/studies/d1_near_plate.py ../vids/spike/20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right.MOV out/20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right --radius 60:120
uv run python scripts/studies/d1_near_plate.py ../vids/spike/20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right.MOV out/20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right --radius 50:100
# numbers and sheets
uv run python scripts/studies/d1_views.py --v1 --near out/20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right out/20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right out/20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right
uv run python scripts/studies/d1_sheets.py ../vids/spike/<clip>.MOV out/<clip> --near   # each of the 3
```

## Files

| Path | Content |
|---|---|
| `prototype/out/<clip>/plate.npz`, `plate_check.jpg`, `bar_path.png` | standard plate run (commands above) |
| `prototype/out/<clip>/plate_near.npz`, `plate_near_check.jpg` | near-plate prior run (30°, 45°) |
| `prototype/out/<clip>/d1_views.json` | per-rep phase frames, keypoint and segment stats, bar markers (rectified and not), x at height |
| `prototype/out/<clip>/d1_sheet.jpg`, `d1_zoom.jpg` | visual check |
| `prototype/out/d1_views.md`, `d1_paths.png` | all three views together |
