# 30 — Quick frame-rate estimate: 240 fps results subsampled to 120/60/30

Ticket: [#30](https://github.com/jirigrill/snatch-exercise-validation/issues/30) (parent [#9](https://github.com/jirigrill/snatch-exercise-validation/issues/9), [#11](https://github.com/jirigrill/snatch-exercise-validation/issues/11); a first look ahead of [#15](https://github.com/jirigrill/snatch-exercise-validation/issues/15)). Run 2026-10-05.

**Bottom line.**
- **120 fps holds up.** Phase marks (except the catch), bar displacements, peak bar velocity and most joint angles stay within half the rep-to-rep spread of 240 fps.
- **60 fps is marginal.** Bar displacements and setup/lockout stay usable. Peak bar velocity becomes marginal (reads 0.05 m/s low on average), and angles at the transition fail.
- **30 fps is unusable** for most markers. Only Xnet, drop and the lockout time stay usable; C1, the knee at the catch and the elbow/trunk at lockout are marginal. The transition was missed once in 48 runs, and setup time and the hip, elbow and trunk at the transition move by more than the spread.
- **The catch mark and turnover (D4) fail at every rate, 120 included.** That comes from how they are defined, not from the frame rate (see §2). They need a more stable definition before any rate can be judged.
- **Approximation only.** Pose and plate were tracked at 240 fps and then thinned. #15 gives the exact answer.

Code: `prototype/src/snatch/markers.py` (bar markers B2–B5, B8, C1, D4 and the verdict rule), `prototype/scripts/fps_estimate.py`. Output: `prototype/out/fps_estimate.{md,json}`.

## 1. Method

- **Clips:** the 6 side-on reps of 4581, 4583, 4584 (2) and 4587 (2). 6 light power snatches, one lifter.
- **Subsampling:** every 2nd/4th/8th frame of `raw_pose.npz` and `plate.npz`, at **every start offset** (2/4/8 per rate). Offset 0 is the ladder file (#14), pixel for pixel; the other offsets show how much the result depends on where the frames happen to fall.
- **Re-run at the lower rate:** Savitzky–Golay smoothing with the same 0.1 s window (13/7/3 frames at 120/60/30; at 30 fps a 3-frame window with order 2 does not smooth at all), phases v2 unchanged, then the markers. Times are mapped back to the 240 fps clock.
- **Markers** (doc 11 rows, from the smoothed hub; operational details in `snatch/markers.py`):
  - phase marks: setup, transition, catch, lockout (v2);
  - D4 turnover: peak upward bar speed → lowest bar speed (Ahn & Kipp). Doc 11's alternative end point, the bar catch, is shown too;
  - C1 peak upward bar speed;
  - B2 X1, B3 X2, B4 Xloop, B5 Xnet, B8 drop. The X1 window ends at the v2 transition: in these reps the bar keeps moving toward the lifter through the second pull, so a window to peak height would put X1's end at the peak and make X2 always 0;
  - hip, knee, elbow and trunk angles at each phase mark.
- **Comparison:** Δ = lower-rate value − 240 fps value, same rep. Rep-to-rep spread = SD across the 6 reps at 240 fps (for phase marks: SD of the mark's time after the rep's overhead start).
- **240 fps unchanged:** the script reproduces `phases_v2.json` for every rep and stops if it does not. No 240 fps output file was changed.
- **Verdict rule, fixed before the results were seen** (`snatch.markers.verdict`): ratio = max |Δ| over all reps and offsets ÷ SD at 240. **Usable** ≤ 0.5, **marginal** ≤ 1, **unusable** above that, or if any rep was not detected. A group takes the most common verdict of its markers (plurality), ties to the worse. A plurality can hide failing members, so §4 names them.

## 2. Two markers fail at any rate: the catch mark and D4

- **Catch (lowest hip)** moves up to ±104 ms even at 120 fps. The two 120 fps offsets of the *same* rep disagree by up to 129 ms (4584 rep 2: +104 vs −25 ms).
  - At 240 fps (checked ad hoc, not in the script), the bottom of the receiving squat has several local hip-height maxima within 2 px of the deepest one, spread over 70–200 ms (all 6 reps). The mark is an argmax over near-ties, so dropping half the frames can move it to another tie.
  - The joint angles at the catch move much less (median |Δ| ≤ 0.6° at 120 fps), because the pose barely changes across that plateau. The elbow is the exception (up to 6.8°); likely it is still moving while the hips sit at the bottom (not checked).
- **D4** inherits the same weakness at both ends:
  - start: 4581 has two near-equal peaks in bar speed about 80 ms apart (a two-peak curve, C2), and the 120 fps offset 0 picks the earlier one;
  - end: the lowest bar speed and the bar catch are extrema too. Bias is +11…+26 ms at every rate.
- **So:** catch-based and D4 timing need a definition that does not pick from near-ties (for example a threshold crossing, or the centre of the plateau) before #15 can say which rate they need. That would change the frozen v2 catch rule. This ticket only flags it.

## 3. Results

Bias = mean Δ. Median and max |Δ| are over all reps × offsets, detected reps only. "off 0" = the ladder file alone.

### 120 fps (2 offsets × 6 reps)

| marker | unit | SD 240 | bias | median \|Δ\| | max \|Δ\| | max \|Δ\| off 0 | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| setup | ms | 52 | 2 | 4 | 8 | 8 | 0.16 | usable |
| hip at setup | ° | 3.9 | -0.1 | 0.1 | 0.5 | 0.2 | 0.12 | usable |
| knee at setup | ° | 3.9 | 0.1 | 0.4 | 1.3 | 0.7 | 0.32 | usable |
| elbow at setup | ° | 1.9 | 0.0 | 0.1 | 0.2 | 0.1 | 0.10 | usable |
| trunk at setup | ° | 2.3 | 0.0 | 0.3 | 0.5 | 0.4 | 0.20 | usable |
| transition | ms | 26 | -2 | 4 | 8 | 8 | 0.32 | usable |
| hip at transition | ° | 2.5 | -0.7 | 0.9 | 3.3 | 3.3 | 1.35 | unusable |
| knee at transition | ° | 3.1 | 0.0 | 0.1 | 0.2 | 0.2 | 0.07 | usable |
| elbow at transition | ° | 4.2 | 0.4 | 0.4 | 2.6 | 2.6 | 0.62 | marginal |
| trunk at transition | ° | 1.4 | 0.5 | 0.9 | 2.3 | 2.3 | 1.72 | unusable |
| catch | ms | 69 | 9 | 23 | 104 | 104 | 1.50 | unusable |
| hip at catch | ° | 3.2 | 0.3 | 0.5 | 1.9 | 1.8 | 0.60 | marginal |
| knee at catch | ° | 5.2 | 0.1 | 0.1 | 0.9 | 0.8 | 0.17 | usable |
| elbow at catch | ° | 3.9 | 0.1 | 0.6 | 6.8 | 6.8 | 1.76 | unusable |
| trunk at catch | ° | 1.6 | -0.1 | 0.2 | 1.2 | 0.8 | 0.70 | marginal |
| lockout | ms | 152 | 1 | 4 | 17 | 12 | 0.11 | usable |
| hip at lockout | ° | 2.4 | -0.1 | 0.1 | 0.6 | 0.4 | 0.25 | usable |
| knee at lockout | ° | 0.6 | 0.1 | 0.2 | 0.4 | 0.4 | 0.79 | marginal |
| elbow at lockout | ° | 5.8 | 0.0 | 0.3 | 0.8 | 0.8 | 0.14 | usable |
| trunk at lockout | ° | 2.5 | -0.0 | 0.1 | 0.5 | 0.2 | 0.21 | usable |
| B2 X1 | cm | 1.0 | 0.0 | 0.0 | 0.1 | 0.0 | 0.06 | usable |
| B3 X2 | cm | 1.6 | 0.0 | 0.0 | 0.1 | 0.1 | 0.08 | usable |
| B4 Xloop | cm | 2.5 | 0.1 | 0.3 | 0.4 | 0.4 | 0.15 | usable |
| B5 Xnet | cm | 5.9 | -0.0 | 0.1 | 0.3 | 0.1 | 0.04 | usable |
| B8 drop | cm | 1.3 | -0.0 | 0.0 | 0.1 | 0.1 | 0.11 | usable |
| C1 peak bar velocity | m/s | 0.16 | -0.03 | 0.03 | 0.05 | 0.05 | 0.30 | usable |
| D4 turnover (to lowest bar velocity) | ms | 55 | 23 | 13 | 79 | 79 | 1.44 | unusable |
| D4 turnover (to bar catch), alt. | ms | 48 | 16 | 12 | 87 | 87 | 1.83 | unusable |

### 60 fps (4 offsets × 6 reps)

| marker | unit | SD 240 | bias | median \|Δ\| | max \|Δ\| | max \|Δ\| off 0 | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| setup | ms | 52 | 11 | 12 | 21 | 17 | 0.40 | usable |
| hip at setup | ° | 3.9 | -0.3 | 0.3 | 1.5 | 0.5 | 0.39 | usable |
| knee at setup | ° | 3.9 | 0.5 | 0.7 | 3.3 | 1.0 | 0.83 | marginal |
| elbow at setup | ° | 1.9 | 0.2 | 0.2 | 1.3 | 0.6 | 0.72 | marginal |
| trunk at setup | ° | 2.3 | 0.3 | 0.3 | 1.0 | 0.5 | 0.43 | usable |
| transition | ms | 26 | -2 | 4 | 17 | 8 | 0.64 | marginal |
| hip at transition | ° | 2.5 | -0.7 | 1.6 | 6.7 | 3.3 | 2.72 | unusable |
| knee at transition | ° | 3.1 | 0.1 | 0.1 | 0.5 | 0.4 | 0.16 | usable |
| elbow at transition | ° | 4.2 | 0.4 | 1.3 | 5.1 | 2.4 | 1.22 | unusable |
| trunk at transition | ° | 1.4 | 0.6 | 1.1 | 4.5 | 2.3 | 3.30 | unusable |
| catch | ms | 69 | 28 | 23 | 171 | 96 | 2.46 | unusable |
| hip at catch | ° | 3.2 | 0.4 | 0.6 | 1.6 | 0.8 | 0.50 | marginal |
| knee at catch | ° | 5.2 | 0.1 | 0.4 | 1.5 | 1.4 | 0.30 | usable |
| elbow at catch | ° | 3.9 | 0.3 | 1.0 | 7.1 | 4.0 | 1.82 | unusable |
| trunk at catch | ° | 1.6 | -0.2 | 0.3 | 1.1 | 0.5 | 0.66 | marginal |
| lockout | ms | 152 | 5 | 4 | 25 | 12 | 0.16 | usable |
| hip at lockout | ° | 2.4 | -0.2 | 0.2 | 1.0 | 0.6 | 0.40 | usable |
| knee at lockout | ° | 0.6 | 0.3 | 0.3 | 1.2 | 1.2 | 2.15 | unusable |
| elbow at lockout | ° | 5.8 | 0.0 | 0.5 | 1.9 | 0.7 | 0.33 | usable |
| trunk at lockout | ° | 2.5 | -0.0 | 0.1 | 0.6 | 0.2 | 0.26 | usable |
| B2 X1 | cm | 1.0 | 0.0 | 0.0 | 0.2 | 0.1 | 0.20 | usable |
| B3 X2 | cm | 1.6 | -0.0 | 0.1 | 0.2 | 0.2 | 0.14 | usable |
| B4 Xloop | cm | 2.5 | 0.1 | 0.3 | 1.0 | 0.5 | 0.41 | usable |
| B5 Xnet | cm | 5.9 | -0.1 | 0.1 | 0.4 | 0.3 | 0.07 | usable |
| B8 drop | cm | 1.3 | -0.0 | 0.0 | 0.1 | 0.1 | 0.11 | usable |
| C1 peak bar velocity | m/s | 0.16 | -0.05 | 0.05 | 0.12 | 0.07 | 0.75 | marginal |
| D4 turnover (to lowest bar velocity) | ms | 55 | 26 | 31 | 162 | 125 | 2.96 | unusable |
| D4 turnover (to bar catch), alt. | ms | 48 | 18 | 21 | 129 | 108 | 2.71 | unusable |

### 30 fps (8 offsets × 6 reps)

| marker | unit | SD 240 | bias | median \|Δ\| | max \|Δ\| | max \|Δ\| off 0 | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| setup | ms | 52 | 28 | 29 | 62 | 42 | 1.19 | unusable |
| hip at setup | ° | 3.9 | -0.8 | 0.6 | 4.4 | 0.5 | 1.12 | unusable |
| knee at setup | ° | 3.9 | 1.4 | 1.6 | 6.7 | 2.6 | 1.69 | unusable |
| elbow at setup | ° | 1.9 | 0.5 | 0.5 | 3.4 | 1.0 | 1.81 | unusable |
| trunk at setup | ° | 2.3 | 0.8 | 0.9 | 2.3 | 1.7 | 1.00 | unusable |
| transition | ms | 26 | -0 | 8 | 29 (1 missing) | 25 | 1.12 | unusable |
| hip at transition | ° | 2.5 | -0.3 | 2.8 | 11.2 (1 missing) | 8.9 | 4.55 | unusable |
| knee at transition | ° | 3.1 | -0.2 | 0.7 | 2.1 (1 missing) | 2.1 | 0.68 | unusable |
| elbow at transition | ° | 4.2 | 0.2 | 2.1 | 7.5 (1 missing) | 7.5 | 1.80 | unusable |
| trunk at transition | ° | 1.4 | -0.1 | 2.2 | 7.4 (1 missing) | 6.0 | 5.43 | unusable |
| catch | ms | 69 | 25 | 50 | 167 | 58 | 2.40 | unusable |
| hip at catch | ° | 3.2 | 0.9 | 1.0 | 5.7 | 2.0 | 1.82 | unusable |
| knee at catch | ° | 5.2 | 0.5 | 0.8 | 3.6 | 3.0 | 0.70 | marginal |
| elbow at catch | ° | 3.9 | 0.1 | 1.5 | 11.6 | 2.2 | 3.01 | unusable |
| trunk at catch | ° | 1.6 | -0.5 | 0.6 | 3.2 | 1.6 | 1.93 | unusable |
| lockout | ms | 152 | 12 | 12 | 42 | 25 | 0.27 | usable |
| hip at lockout | ° | 2.4 | -0.6 | 0.6 | 2.7 | 1.7 | 1.13 | unusable |
| knee at lockout | ° | 0.6 | 0.9 | 0.7 | 3.3 | 1.2 | 5.85 | unusable |
| elbow at lockout | ° | 5.8 | 0.0 | 0.6 | 4.0 | 1.9 | 0.68 | marginal |
| trunk at lockout | ° | 2.5 | -0.1 | 0.2 | 1.4 | 0.8 | 0.56 | marginal |
| B2 X1 | cm | 1.0 | 0.1 | 0.0 | 0.5 (1 missing) | 0.2 | 0.46 | unusable |
| B3 X2 | cm | 1.6 | -0.0 | 0.1 | 0.5 (1 missing) | 0.3 | 0.34 | unusable |
| B4 Xloop | cm | 2.5 | 0.0 | 0.6 | 2.5 | 1.2 | 1.01 | unusable |
| B5 Xnet | cm | 5.9 | -0.2 | 0.2 | 0.8 | 0.5 | 0.13 | usable |
| B8 drop | cm | 1.3 | -0.1 | 0.1 | 0.3 | 0.2 | 0.22 | usable |
| C1 peak bar velocity | m/s | 0.16 | -0.07 | 0.07 | 0.14 | 0.12 | 0.88 | marginal |
| D4 turnover (to lowest bar velocity) | ms | 55 | 17 | 42 | 179 | 125 | 3.26 | unusable |
| D4 turnover (to bar catch), alt. | ms | 48 | 11 | 38 | 142 | 142 | 2.97 | unusable |

### Group verdicts by the rule

| group | 120 fps | 60 fps | 30 fps |
|---|---|---|---|
| phase marks | usable | usable | unusable |
| turnover (D4) | unusable | unusable | unusable |
| peak bar velocity (C1) | usable | marginal | marginal |
| bar displacements (B2–B5, B8) | usable | usable | unusable |
| joint angles at phases | usable | usable | unusable |

## 4. Verdict per rate

Group verdicts by the rule are in the last table. Where a group's majority hides failing members, they are named.

| group | 120 fps | 60 fps | 30 fps |
|---|---|---|---|
| phase marks | **usable** (3 of 4); catch unusable (§2) | **usable** by plurality, 2 of 4: transition marginal, catch unusable | **unusable**; only lockout usable |
| turnover (D4) | **unusable**, from its definition (§2) | **unusable** | **unusable** |
| peak bar velocity (C1) | **usable** (−0.03 m/s bias) | **marginal** (−0.05 m/s, up to 0.12) | **marginal** (−0.07 m/s, up to 0.14) |
| bar displacements (B2–B5, B8) | **usable** (all ≤ 0.4 cm) | **usable** (≤ 1.0 cm) | **unusable**: X1/X2 lost with the missed transition, Xloop up to 2.5 cm; Xnet and drop usable |
| joint angles at phases | **usable** at setup, the knee at every phase but lockout, most of lockout; hip and trunk at transition, elbow at catch **unusable** (max 2.3–6.8°, median ≤ 0.9°); the rest marginal | **usable** by plurality, but only 7 of 16 (4 marginal, 5 unusable): usable are setup hip/trunk, lockout except the knee, knee at transition and catch; **unusable** at the transition except the knee, elbow at catch, knee at lockout | **unusable** almost everywhere |

Notes on reading the ratios:
- Small 240 fps spreads make some ratios large. The knee at lockout has SD 0.6°, because v2 defines lockout by the knee (within 5° of its maximum), so its value is partly fixed by definition (doc 11, A17). A 1.2° error at 60 fps is "unusable" against that spread.
- The rule uses the worst case over all offsets. The median |Δ| is often 2–6× smaller. A single 30 fps video is typically closer than the worst case, but there is no way to know which kind of video it is.
- C1 is biased **low** at every rate. Fewer samples and the same smoothing window flatten the speed peak. A fixed correction is not justified from 6 reps.

## 5. What it implies

**YouTube generalization set** (mostly 30 fps, some 60):
- At 30 fps only **Xnet, drop and lockout time** carry over. Transition and setup angles, Xloop, X1/X2 and timing do not. A 30 fps set could check bar-path claims (Xnet, drop), not the angle-based or timing-based ones.
- Prefer **60 fps** sources. They keep the bar displacements, the setup and lockout marks, hip/trunk at setup and most of lockout. The transition mark and C1 are marginal there, knee/elbow at setup marginal, and transition angles (except the knee) still fail.
- Never pool 30/60 fps clips with 240 fps clips for a marker this table marks unusable at that rate.

**App recording requirements:**
- **Record at ≥ 120 fps.** That is the lowest rate at which this estimate keeps transition timing and peak bar velocity usable. 60 fps loses the transition hip/trunk angles and makes C1 marginal.
- 240 fps stays the reference until #15 runs. The catch-mark and D4 issue (§2) is not fixed by a higher rate.
- This agrees with doc 05's arithmetic (30 fps ruled out) and doc 11's C1 row (fps ≥ 120). It now rests on measurement, not only arithmetic.

## 6. Caveats

- **Approximation.** At a real lower rate:
  - the plate Viterbi (≤ 30 px per 240 fps frame, 24-frame gap bridging) would see 2–8× larger steps per frame;
  - the pose crop tracking would follow a different box;
  - motion blur from a longer 30/60 fps exposure is not simulated.
  All three are expected to make lower rates worse, not better [inference]. #15 runs pose on the ladder files and gives the exact answer.
- **6 light power-snatch reps, one lifter, one day.** The spread is small, so the bar for "usable" is strict. A heavier or more varied set would have a larger spread and looser verdicts.
- **Absolute bar values were not checked.** Xnet is −15 to −31 cm (Shah's typical range is 0–17 cm), X1 is 0–2.3 cm and X2 0–3.6 cm (each 0 in half the reps). This ticket only compares rates with each other.
- X1/X2 depend on the v2 transition, so a missed transition also loses them (the one 30 fps miss).
- **At 30 fps there is no smoothing.** The 0.1 s window is 3 frames, which a 2nd-order Savitzky–Golay fit passes through unchanged. The 30 fps rows mix the lower rate with unsmoothed keypoints. A wider window might help at 30 fps; it was not tried, because the ticket keeps the window the same in seconds.
- **Rule wording.** The rule was first written as "majority", but the code always took the plurality. The two differ for the 60 fps phase marks (2 of 4) and joint angles (7 of 16), which is why §4 gives the counts.
