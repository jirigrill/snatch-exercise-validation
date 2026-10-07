# 32 — Reference for "correct": what to compare a lift against
Status: design note, nothing built · Date: 2026-10-07 · Ticket: none yet (number provisional) · Builds on: `11-technique-markers.md`, `12-feasibility-grill.md`, `../results/30-fps-estimate.md`

## Bottom line

- **There is no perfect snatch to compare against** (`12` § "Why there is no universal perfect lift"). The literature describes elite group averages; it doesn't prescribe a template for one body.
- **The lifter's own made reps are a biased reference.** A lifter who does the same thing wrong every time can still make the lift, and the fault becomes the norm.
- Two different questions, two different references:

| Question | Reference | Solvable from one phone? | In gate 1? |
|---|---|---|---|
| **A** Why did *this* rep fail? | Relative: what works for this lifter | Yes | **Yes** (it is gate 1) |
| **B** Is the technique *capping* the lifter's max? | Absolute: what works in general | Partly | **No** |

- **Fix: three reference layers plus efficiency metrics**, not one reference. Layers 1 and 3 belong to the cause engine (#27) and gate 1. Layer 2 and the efficiency metrics answer B and stay out of gate 1.
- **A full model of the ideal snatch for one lifter is not usable** (Korayem 2010: circular optimum, thin validation, needs strength data a phone can't give). A **proportion model** (layer 1b: static key positions from segment lengths) is kept, reported only, and tested against layer 3 on gate-1 data.
- **Order:** finish measurement first, but only to "good enough for the gate-1 markers", not "perfect" (§4).

## Conclusion: can we model a "perfect snatch" for one athlete?

**Not a validated one, with today's literature and one phone. A coarse, personalized "plausible zone": yes.** (Based on a web search plus full reads of Korayem, Nejadian & Rostami ×2, Butters, and abstracts of newer papers. Not a systematic review; Jon 2024 is unread.)

| Part | Verdict | Why |
|---|---|---|
| Ideal bar trajectory | **No** | Models (Nejadian, Korayem, arXiv 2025) reproduce the known shape by design; validation is one simulated lifter vs a group-mean shape, no error numbers, no real athlete. Elite lifters succeed with all 4 bar-path types (Shah), so there is a family of acceptable paths, not one |
| Ideal body movement (dynamics) | **No** | Needs per-joint torque–velocity data a phone can't give; the optimum depends on the chosen cost (min torque, min height, …); nobody has shown that distance from a model predicts misses |
| Plausible static positions from proportions | **Partly** | Butters: femur and shank/femur ratio explain part of start hip height (r² ≈ 0.34–0.5, n = 20, in-sample); proportions reach bar path only through hip height. So: wide angle ranges for setup and catch, not a tight target |
| Physical limits that hold for everyone | **Yes** | Layer 1: bar close, bar over the base at the catch, catch below the peak |
| The lifter's own best heavy reps | **Yes** | Layer 3: answers "why did this rep fail", the question gate 1 tests |

**Why a "perfect" model fails on logic, not only data:** "perfect" depends on a goal (minimum torque, minimum bar height, maximum load) and on strength, mobility and style. The models pick one criterion. The made-vs-missed literature finds few consistent differences (Garhammer, Mastalerz), so even a perfect model would have nothing proven to be checked against.

**Consequence for the app:**
- Use layers 1, 1b and 3. Layer 1b is reported only, and tested on gate-1 data: if its deltas separate made and missed lifts better than layer 3's, extend it; if not, drop it.
- A Korayem-style dynamic model is out of scope until gate 1 passes and 1b has shown value.
- It remains possible that someone has validated a model the search missed; nothing read suggests it.

## 1. The three layers

| Layer | Reference | Catches | Blind to | Needs |
|---|---|---|---|---|
| **1 Physical bands** | Mechanical limits that hold for every lifter | Gross faults, even on made reps, even if habitual | Subtle faults inside the bands | Measurement noise known (bands get a noise margin) |
| **2 Elite ranges** | Literature ranges (Harbili, Mastalerz, Shah), normalized to body height | "Unusual compared with elite lifters" | Whether unusual is wrong for this body; small, elite-only samples | **Absolute** accuracy in cm, lifter height |
| **1b Proportion model** | Static key positions solved from the lifter's segment lengths (§1b) | Positions that don't fit this body's proportions, even if habitual | Dynamics, timing, strength; whether the model's position is right (unvalidated) | Segment lengths from pose, ankle and hub visible |
| **3 Best own reps** | Top of the lifter's own made-rep distribution, ranked by measured efficiency, at heavy load | Deviations from what already works best for this lifter | Faults present in every rep | Repeatability, ≥ 5 heavy made reps, load as %1RM |

### Layer 1: physical bands

The universal bands from `12` § 1, mapped to markers:

| Band | Markers | Status |
|---|---|---|
| Bar stays close | B3 (X2), B4 (Xloop), B5 (Xnet) | now (`snatch/markers.py`) |
| Bar over the base at catch and lockout | B10, E2 | now (needs ankle keypoint at catch) |
| Full extension before the turnover | A10, A11 vs D4 start | blocked: hip/knee hidden at transition (D1, #23) |
| Catch below the bar's peak | B8 drop > 0, timing of hip catch vs bar peak | now; catch mark unstable (#31) |

- Threshold = band edge **plus** a measurement-noise margin. Without the margin, noise alone triggers false alarms on made lifts, which gate 1 counts against the app.
- Numeric band edges aren't fixed yet. Take candidates from the Shah ranges in `11` (B3 3–14 cm, B4 3–12 cm, B5 0–17 cm), then check them against the false-alarm rule of gate 1.

### Layer 2: elite ranges (question B only)

| Marker | Elite value | Normalize by |
|---|---|---|
| B6 peak bar height | 1.16 ± 0.05 m (Harbili men); Shah 70–85% of body height | Lifter height |
| B8 drop | 0.14 ± 0.03 m (Harbili men); Shah 6.5–25 cm, "less is better" | Lifter height or peak height |
| B2–B4 horizontal | See `11` B2–B4 | None (cm) or lifter height |
| C1 peak bar speed | 1.69 ± 0.07 m/s (men) | Load (%1RM): speed falls with load |
| D4 turnover | 0.235 ± 0.016 s (Harbili) | — (definition unstable, #31) |

- **Body height from video:** standing frame, top of the person outline (`snatch/person.py`) to the lowest ankle or heel keypoint. The body is ~0.6–0.8 m farther from the camera than the near plate, so the plate scale needs a depth correction (from D = 4 m and the bar geometry); without it the height reads ~15–20% high. Expected error after correction ~1–3% (estimate), small against Shah's 70–85% band. Computing B6 ÷ height in pixels from one video cancels the 450 mm plate assumption. The tape-measured `height_cm` (spike session, #22) checks the estimate; in the product, the user enters their height and the video estimate is a plausibility check.
- Report as "outside the elite range", never as "wrong".
- Mastalerz and Harbili found **no made/missed difference** in B6, B8, C1. So these ranges describe elite style; they don't predict misses. One more reason to keep them out of gate 1.

### Layer 3: best own reps, not average own reps

- Pool only made reps at **≥ 85% 1RM**. A light rep doesn't show what holds under load.
- Rank them by an efficiency score (§2) and take the **top third** as the reference (median and spread per marker).
- Fewer than 5 qualifying reps → no layer 3; fall back to layers 1 and 2 (`12` hard limit 5).
- This removes bad *occasional* reps from the reference. It cannot remove a fault present in *every* rep. Only layer 1 (and layer 2 as a hint) sees that.

### Layer 1b: proportion model (personalized geometry, no dynamics)

**Why not a full "ideal snatch" model.** The only paper that models an optimal snatch for a given lifter is Korayem et al. (`../papers/MODELING OF THE SNATCH WEIGHTLIFTING.pdf`, MathSport 2010 preprint). It is a 2D optimal-control model with joint torque limits (Yeadon 2006 torque–velocity functions), personalized by body mass and height only, solving for minimum effort plus bar-path terms. It isn't usable as a reference:

| Problem | Detail |
|---|---|
| Circular optimum | The cost function contains terms that force the double knee bend, with ratios r1, r2 fitted to experimental data, so it reproduces elite technique by construction |
| Thin validation | One simulated case (60 kg lifter, 143 kg); "good agreement" by eye with group-mean curves (Gourgoulis 2000); no error numbers, no individual lifters |
| Incomplete | Lift-off to start of catch only; no foot-off; sagittal plane only |
| Inputs not filmable | Per-joint torque–velocity capacity needs a dynamometer; from a phone the model falls back to generic strength |
| No outcome link | Not shown that distance from the model predicts misses or that moving toward it raises 1RM |
| Cost | Months of optimal-control and muscle-model work, before gate 1 |

**Literature search (2026-10-07, web search, abstracts and one thesis read; not exhaustive).** No validated individual snatch model was found.

| Source | What it is | Use for 1b |
|---|---|---|
| Nejadian & Rostami, ISBS 2007 (two papers, full text read: Pontryagin; genetic algorithm). A 2008 journal version and a dynamic-programming version exist, abstracts only | 5-link model (shank, thigh, trunk, upper arm, forearm; segment values from Chaffin & Anderson regression formulas) minimizing joint torque from lift-off to start of catch. Cases: 55 kg / 1.6 m / 90 kg bar; 70 kg / 1.7 m / 90 kg bar (GA) | Same method and weakness as Korayem. Validation is one simulated lifter vs the *shape* of Garhammer's (2001) trajectory ("typical toward–away–toward"); no error numbers, no real lifter. Both papers are 2–4 pages. Their claim that the result "can be produced by a real weightlifter" rests on the equations of motion, not on data |
| Jon et al. 2024, *Engineering Reports* (6-link anthropometric model, barbell trajectory) | Newer version of the same approach | Page returned 403; **not read** |
| arXiv 2510.19841 (2025), minimal optimal-control model of the snatch pull | Vertical bar trajectory only; first and second pull; "agrees well" with video data | Abstract only: no personalization, sample size or error numbers stated. Bar vertical only, no body angles |
| PMC10437953 (optimal force–velocity profile) | Barbell-level model; one personal parameter (threshold bar velocity); simulations on published data from 13 elite lifters; no new data | Bar force and speed only; no bar path or joint angles |
| Butters, MSc thesis (UCLan; not checked whether peer-reviewed) | 20 experienced men at 85% 1RM, 3D motion capture; stepwise regression of segment lengths on start position | **Directly relevant**, below |

**Butters thesis (full text read, incl. discussion), the one empirical link between proportions and position:**
- Design: 20 experienced men (age 29.5 ± 5.3 y, 77.5 ± 8.0 kg), **3 single lifts at 85% 1RM in one session**, 3D motion capture; stepwise regression of segment lengths on the start position (SP). Abbreviations: AFL = absolute femur length, MHBD = max horizontal bar displacement from SP to end of the first pull, GRF° = ground-reaction-force vector angle at SP.
- Femur length (AFL) predicts start hip height (r² = 0.34, p < 0.01); shank-to-femur ratio adds r² = 0.20 (p = 0.05).
- Relative femur length (0.45), relative trunk length (0.69) and shank-to-femur ratio (0.77) predict GRF° at the start.
- **Correction to the first version of this note:** no *anthropometric* variable predicted MHBD, but **absolute hip height did** (r² = 0.37, adj. 0.34; b = −0.23: higher hips, less backward travel). So proportions reach bar path only **indirectly**: femur → hip height → MHBD. The thesis calls this suggestive, not tested.
- Bar paths were mostly backward (toward the lifter) in the sample; lifters with different femur lengths reached similar bar paths with different hip heights.
- **Case study (descriptive, one lifter, trials 1 vs 3):** hips rose between trials, torso leaned further over the bar, bar path went forward. Says the start position is "more than hip height": hip height, knee bend and torso lean together.
- Limitations the thesis states: 3 lifts per lifter, so the start position may not be each lifter's repeatable one; male, one weight-class range, so no transfer to women or heavier lifters; marker placement reliability not tested. Added here: stepwise selection on many candidate predictors (in-sample r², overfitting risk). Made vs missed was **not** analysed, so nothing here shows a start position causes a miss.
- Its recommendation (force angle at the start of about 1.5–2° "will result in the most optimal bar path") is the author's advice from correlations, not a tested threshold. Not used.

**What this changes:**
- Proportions explain **part** of the start position (hip height r² ≈ 0.3–0.5), not most of it. The layer 1b range at setup must be wide, and 1b can only be a coarse check, not a tight target.
- **The setup can't be judged from hip height alone**: the same hip height gives different bar paths for different femur lengths. 1b has to solve hip, knee, and torso angle together, not one number. This fits the layer 1b design (angles from constraints), and rules out a simple "hip height should be X% of body height" rule.
- Bar travel in the first pull depends on proportions only through the start position. The bar-path markers still need measured references (layers 1 and 3), not a proportion formula.
- Still no model validated on individual lifters against made/missed outcomes. The decision stands: 1b geometry only, reported, tested against layer 3 on gate-1 data.
- **Still unread:** Jon 2024 (paywalled); the 2008 Nejadian journal version.

**What is kept: geometry from limb lengths.** The main reason a universal template fails is proportions (`12` § "Why there is no universal perfect lift"). That part can be modelled without dynamics:

1. Segment lengths per lifter from pose: shank, thigh, torso, upper arm, forearm (median over standing and lockout frames; perspective-corrected like body height, §Layer 2).
2. Solve static key positions as a small constrained geometry problem, using rules from the literature or coaching ([C] where no paper):

| Position | Constraints | Output |
|---|---|---|
| Setup | Bar over the mid-foot; shoulders slightly ahead of the bar (A4); arms vertical, straight; bar at its floor height | Trunk, hip, knee angle (A1–A3) |
| Power position (transition) | Bar at the upper thigh or hip; trunk near vertical (A9); knees under the bar | Knee, hip angle (A8) |
| Catch | Bar over the mid-foot (B10); arms locked; lifter's catch depth (squat or power) | Trunk, hip, knee angle (A14, A15) |

3. The delta = measured angle at the phase mark minus the model angle.

- Constraints are a coach's description of a good position, not a proven optimum. The model says "this position fits your proportions", not "this is ideal".
- Several solutions may fit (e.g. hip height at setup). Report the range, not a single angle.
- The hips and knees are hidden at the transition (`../results/13-phase-check.md`), so the power position waits on D1, as A10 and A11 do.

**Test (on gate-1 data):** do deltas from the proportion model separate made and missed lifts better than deltas from the best own reps (layer 3)? If not, drop 1b. Until it passes, 1b is reported, not used for cause claims.

## 2. Efficiency metrics: "wasteful", not "different"

The answer to the biased-reference problem: judge what is measurably wasteful, which has a better and a worse direction without any template.

| Metric | Definition | Better | From |
|---|---|---|---|
| Excess height | B8 drop ÷ peak height | Lower | `markers.py` (B6, B8) |
| Relative peak height | B6 ÷ lifter height | Lower at the same load | `markers.py` + lifter height |
| Horizontal waste | X2 + Xloop | Lower | `markers.py` (B3, B4) |
| Speed per load | C1 at known %1RM | Higher | `markers.py` + load |
| Turnover time | D4 | Shorter | after #31 |

- Score = rank sum across the metrics within one lifter, at one load band. No weights until there is data to fit them.
- **Open:** whether a better score means a higher 1RM. That needs an intervention over weeks (change technique, see whether the max moves), not one video. Not testable before gate 1.

## 3. Changes to the prototype

| Change | Where | When | Blocks gate 1? |
|---|---|---|---|
| Add **lifter height** per lifter (`pct_1rm` is already in the recording-protocol log) | recording protocol § Log, `clip-log.md` | **now** (cheap) | No; layer 2 only |
| Efficiency metrics | `snatch/markers.py` (new fields on `BarMarkers`) | now; they are ratios of existing markers | No |
| Layer 1 band checks with noise margin | new `snatch/bands.py`: `check_bands(markers, noise) -> list[BandHit]` | with #27 | Yes |
| Layer 3 reference selection | new `snatch/reference.py`: filter by load, rank, take top third, return per-marker median + SD | with #27 | Yes |
| Layer 1b proportion model | new `snatch/proportions.py`: `segment_lengths(pose, frames) -> Segments`, `solve_position(segments, constraints) -> AngleRange` | with #27 (setup, catch); power position after D1 | No; reported only, compared with layer 3 in the gate-1 evaluation |
| Dynamic optimal-control model (Korayem style) | — | only after gate 1 passes, and only if 1b beats layer 3 | No |
| Layer 2 elite table | `snatch/elite.py`: one constant table with source per row | after gate 1 | No |
| Measurement noise per marker | from `snatch/spread.py` and the static test (D1) | before band thresholds | Yes |

- The cause engine (#27) already plans the "hybrid" reference (`12` § 1, Reference). Layers 1 and 3 are that hybrid made specific; no new product decision.
- The current clips (5–10 kg) can't feed layer 3: there is no heavy load. Layer 3 code can be written and unit-tested now; real reference values come from the gate-1 recording set.

## 4. Order: measurement first, but not "perfect"

**Measurement first.** Every layer depends on knowing the measurement error:
- layer 1 needs it for the noise margin;
- layer 2 needs **absolute** accuracy in cm, which nothing has checked yet (only repeatability: hub jitter 0.7–1.6 px in `../results/14-ladder-and-plate.md`, and frame-rate agreement in `../results/30-fps-estimate.md`);
- layer 3 needs repeatability: an error smaller than the rep-to-rep spread.

**"Perfect" is the wrong target.** Done = error ≤ 0.5 × rep-to-rep SD on the markers of the gate-1 cause list (the rule already used in #30). Measuring more markers, or measuring them better than that, doesn't change the gate.

Open measurement gaps that block gate 1, in order:

1. **D1 (#23) / D2 (#24):** hip, knee and wrist hidden by the plate; the static metric test is also the first check of absolute accuracy. It checks horizontal distance only (50 cm roll); B6 and B8 are vertical and need a vertical check too.
2. **#31:** the catch mark and D4 fail at every frame rate (definition, not frame rate).
3. **#26:** phase detection for the squat snatch (gate 1 is squat snatch only; all reps measured so far are power snatches).
4. Exact frame rate from real recordings (#15, approximated by #30).

**Then layers 1 and 3 with the cause engine (#27), with 1b built alongside and reported only. Layer 2 and the efficiency score after gate 1.** Building layers before these gaps close would set thresholds on numbers whose error is unknown.
