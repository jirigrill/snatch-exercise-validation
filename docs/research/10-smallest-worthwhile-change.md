# 10 — Smallest worthwhile change in snatch joint angles
Status: draft · Date: 2026-10-01

Tags: **VERIFIED** (read in primary source this session), **SECONDARY** (seen only in a search-engine summary or abstract, not re-read in full text), **INFERRED** (my arithmetic/reasoning from tagged facts), **ASSUMPTION**, **NO EVIDENCE FOUND**.

## In plain English (read this first)

**The question.** The app would tell a lifter "this rep is X degrees more closed than your reference reps". What size of X is worth saying, and how quiet must the measurement be so the app is not reporting noise?

**Words used below**

| Term | Plain meaning |
|---|---|
| SD (standard deviation) | How much a set of numbers spreads around its average. Small SD = reps look alike. |
| Typical error / noise | The SD you get when the *same* thing is measured again and again. It is the wobble you cannot avoid. |
| Between-lifter SD | Spread across *different* people. Says nothing about how much one person varies. |
| Within-lifter SD | Spread across one person's reps. This is the number the app needs. |
| RMSD / RMSE | Average size of the error against a reference system. Measures *accuracy*, not repeatability. |
| MDC (minimal detectable change) | The smallest change you can trust is real, not noise. About 2.77 × the typical error when comparing two single reps. |
| SWC (smallest worthwhile change) | The smallest change that matters in practice (a convention: 0.2 × the between-person SD). |
| Bias | An error that is the same every time. It cancels when you compare your own reps, so it does not hurt this app. |

**What we found (the short version)**
1. **Nobody has ever measured how much one lifter's snatch joint angles vary from rep to rep.** Not in papers (checked in two passes), not in coaching books, not in any app. Your own clips will be the first rough measurement.
2. **Closest stand-ins (walking, jumping, squatting) say the natural wobble is small:** knee about 1.5–3°, hip about 2–4°, trunk about 2.5–3.5°. Nothing exists for the elbow. This is an assumption for the snatch, not a measurement.
3. **Differences that matter depend on the comparison.**
   - The same lifter, successful vs failed lift at the same weight: only about **3–7°**, and often not statistically significant.
   - Elite vs less-skilled lifters: **8–17°**. That is a different question from "this rep vs my other reps".
4. **Coaching gives no number for X.**
   - Western coaches (Catalyst, CrossFit, Pendlay, British Weightlifting) teach with cues ("keep the same back angle"), not degrees.
   - Soviet-school texts do give angles, but as wide ranges that describe how good lifters look (start knee 45–90°, end of first pull 145–155°). They are not tolerances for repeating a rep.
   - The only coach-style rep-vs-rep comparison found is a single lifter's knee re-bend: 16–17° in made lifts, 20° in a miss. That is n = 1 and below phone error.
5. **How big must a change be before the app can trust it?** Roughly 2.77 × the total noise (your natural wobble plus the app's measurement error):

| App measurement noise | Total rep-to-rep noise | Smallest change the app can honestly report |
|---|---|---|
| 0° (perfect) | 2.5° | about 7° |
| 2° | 3.2° | about 9° |
| 3° | 3.9° | about 11° |
| 5° (a realistic single phone at the hip) | 5.6° | about 15° |

6. **Phone and camera errors are mostly constant bias.** The big accuracy errors in the literature (8–22° at hip and knee) exaggerate the problem here, because a constant error cancels when you compare your own reps. What matters is repeatability, which is what test #11 measures.

**What this means**
- **10° is a noise limit, not a "size that matters".** It is reportable only if the app's own measurement noise stays at about 2° or less. That is exactly what #11 checks.
- **The 3–7° differences linked to success cannot be seen in a single rep comparison, even with a perfect sensor.** Seeing them needs the average of several reps (roughly 4–9).
- **"Compared with your best rep" is a weak design.** The best rep is partly luck, so later reps look worse for chance reasons alone. Compare with the average of several reference reps instead.
- **The pass/fail rule for #11 does not change:** noise 3° or less across reps = pass, 3–5° = marginal, over 5° = fail, with the standing hold in 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg as the model-only noise floor (about 2° or less).
- **Biggest caveat:** every "natural wobble" figure is borrowed from other movements. A heavy fast lift may wobble more. Only your own reps can settle it.

**Where the detail is**
- This file: the first pass, with corrections applied below.
- `10a-pass2-literature.md`: source-by-source re-check, new within-lifter numbers, reliability standards.
- `10b-pass2-coaching.md`: Soviet, Hungarian and Western coaching sources and apps.

**Pass-2 corrections to the first pass**
- The elite vs sub-elite study is Liu et al. 2018 (not "Zhang"). Its hip differences were tested and were not significant.
- Mastalerz 2019 does have degree values (read off a chart): successful lifts end the second pull with the knee about 4.6° and hip about 3.3° more extended.
- Harbili & Alptekin 2014 does report angles: the same lifters' two heaviest lifts differ by 0.4–3.7° (not significant).
- Soviet-school texts do give numeric angles (the first pass found none).
- The phase RMSDs from Thiele 2024 pool all lower-limb joint movements, not only sagittal ones.

---

## Headline

The literature does **not** support a specific "smallest worthwhile change" in degrees for snatch hip/knee/elbow/trunk angles. No snatch study found reports (a) within-lifter rep-to-rep SD of joint angles, (b) test-retest SEM/MDC of snatch joint angles, or (c) a Hopkins SWC computed on snatch joint angles. The only quantitative anchors are indirect:

- Between-group differences (elite vs sub-elite) of **~8–17 deg** at knee/hip ([PMC6076374](https://pmc.ncbi.nlm.nih.gov/articles/PMC6076374/), **VERIFIED**).
- Between-lifter SDs of **~8–18 deg** (IMU, n=7) ([PAAH 306](https://paahjournal.com/articles/10.5334/paah.306), **VERIFIED**), implying a Hopkins 0.2xSD of **~1.5–3.5 deg** — below any consumer-camera noise floor.
- 2D video squat angle MDC of **~5.5–7.9 deg** (**SECONDARY**), and markerless-3D snatch RMSD vs Vicon of **8.3 deg (knee) to 22.5 deg (hip)** ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/), **VERIFIED**).

Working recommendation (all **INFERRED**): report only differences >= ~10 deg at knee/hip/trunk and >= ~10 deg at elbow; this implies a repeatability SD <= ~3 deg. Current pose-model accuracy (Thiele) does not meet that for the hip.

## Part A — Literature

### A1. Numeric values found

| # | Source | Joint | Phase | Value | Population | Represents | Tag |
|---|---|---|---|---|---|---|---|
| 1 | [Khuyagbaatar et al., PAAH 306](https://paahjournal.com/articles/10.5334/paah.306) | Knee | Start / 1st pull / Transition / 2nd pull / Turnover / Catch | 62.4±10.1 / 119.8±9.6 / 123.9±9.5 / 154.3±9.0 / 71.2±11.8 / 58.4±13.3 deg | 7 female Mongolian lifters, IMU, snatch | mean±SD **between lifters** | VERIFIED |
| 2 | same | Hip | same phases | 24.3±17.3 / 48.7±20.5 / 101.9±28.1 / 172.6±7.9 / 60.6±18.1 / 51.3±17.9 deg | same | mean±SD between lifters (hip convention differs from ordinary flexion; start value 24 deg is not anatomical flexion) | VERIFIED |
| 3 | same | Trunk | same phases | 117.0±28.2 / 139.0±17.5 / 153.9±19.7 / 157.5±9.7 / 147.9±10.4 / 146.5±10.2 deg | same | mean±SD between lifters (IMU trunk convention; 180 = upright assumed) | VERIFIED |
| 4 | same | Elbow | same phases | 184.0±5.5 / 183.0±4.9 / 187.7±7.4 / 183.1±10.3 / 176.0±8.5 / 179.8±7.5 deg | same | mean±SD between lifters | VERIFIED |
| 5 | same | Snatch vs clean | Start | Knee 62.4 vs 77.5 deg (p<0.01); trunk 117.0 vs 136.8 deg (p<0.05) | same | between-exercise difference (15 and 20 deg were "significant") | VERIFIED |
| 6 | [Zhang/Chinese study, PMC6076374](https://pmc.ncbi.nlm.nih.gov/articles/PMC6076374/) | Knee | End of M1 / M2 / M3 / M4 | Top-elite 127.2±9.1 / 115.1±5.4 / 154.8±8.9 / 70.7±6.7 vs sub-elite 109.7±10.6 / 101.5±10.2 / 138.1±12.0 / 70.9±6.1 deg | 6 top-elite vs 6 sub-elite 69 kg men, 3D, heaviest successful lift | **difference 17.5 / 13.7 / 16.7 / -0.2 deg** (p<0.05 at M1,M2,M3) | VERIFIED |
| 7 | same | Hip | M1 / M2 / M3 / M4 | Top-elite 89.6±11.9 / 117.9±7.4 / 147.1±8.2 / 105.5±8.6 vs sub-elite 81.2±11.5 / 104.0±18.9 / 146.0±10.7 / 112.2±17.8 deg | same | difference +8.5 / +13.9 / +1.0 / -6.7 deg (not tested) | VERIFIED |
| 8 | [Biomech. successful vs unsuccessful, elite females, PMC6724589](https://pmc.ncbi.nlm.nih.gov/articles/PMC6724589/) | Knee, hip | Start, suspension (T), preparation for aerial phase (P) | Angles **higher in successful** lifts; only P position significantly different (p<=0.05). **No degree values extracted** | 14 elite women, 14 matched success/fail pairs, 2 cams 50 Hz | direction only | VERIFIED (direction); NO EVIDENCE FOUND (magnitude, from the text I could read) |
| 9 | Greek elite snatch study ([PDF](https://paulogentil.com/pdf/TREINO%20DE%20FORC%CC%A7A/Treinamento%20com%20pesos/G1.pdf)) | Knee | 1st pull to transition | Decrease of 22.2±4.45 deg | elite Greek lifters | mean±SD of knee flexion in the knee-bend (an SD across lifters) | SECONDARY (PDF unreadable; from search summary) |
| 10 | [Thiele 2024, PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/) | Hip flexion | Entire snatch | RMSD **22.5±7.0 deg** | 21 lifters, 131 trials, 12-camera markerless (Theia3D) vs Vicon | measurement error vs criterion | VERIFIED |
| 11 | same | Knee flexion | Entire snatch | RMSD 8.3±1.9 deg | same | measurement error | VERIFIED |
| 12 | same | Ankle dorsiflexion | Entire snatch | RMSD 10.0±5.2 deg | same | measurement error | VERIFIED |
| 13 | same | All sagittal | By phase | RMSD 13.0 (1st pull), 12.3 (transition), 10.1 (2nd pull), 11.0 (turnover), 11.6 (recovery) deg (all DoF pooled) | same | measurement error | VERIFIED |
| 14 | same | Knee | Transition | knee flexion in transition missed in ~9.7% (14/145) trials | same | detection failure | VERIFIED |
| 15 | same | Hip joint centre | — | 6.0±1.3 cm RMS; shoulder 6.3±1.6, knee 4.7±1.5 cm | same | position error | VERIFIED |
| 16 | Kinovea squat reliability ([MDPI Sensors 26(12):3749](https://www.mdpi.com/1424-8220/26/12/3749)) | Knee, pelvic tilt (squat) | — | MDC 5.48–7.87 deg; intra-rater SEM up to 5.14 deg; test-retest SEM up to 14.29 deg | healthy active women, squat, 2D | MDC/SEM of the measurement (not snatch) | SECONDARY (page blocked; search summary) |
| 17 | Kinovea overhead-squat ([Life 15:80](https://doi.org/10.3390/life15010080)) | Hip, knee | Overhead squat | test-retest ICC 0.99 | healthy adults | ICC only (high ICC is not low SEM) | SECONDARY |
| 18 | [Barbell variability, PMC10534034](https://pmc.ncbi.nlm.nih.gov/articles/PMC10534034/) | Barbell only | Whole lift | SEM 0.004–0.023 m (trajectory); ICC 0.46–0.99; variability increases from first pull to catch; lower at maximal than submaximal loads | 7 German national-team men, 85% vs 97% 1RM, 50 fps | within-lifter SEM/SRD; **joint angles not measured** | VERIFIED |
| 19 | [Nagao & Kubo 2019, PMC6628121](https://pmc.ncbi.nlm.nih.gov/articles/PMC6628121/) | Barbell only | 2nd pull to catch | backward displacement 0.11±0.05 m (success) vs 0.10±0.06 m (fail); drop 0.17 vs 0.18 m | 61 male lifters, 2017 Worlds | barbell differences; no joint angles | VERIFIED (abstract) |
| 20 | [Colombian 2D study, redalyc](https://www.redalyc.org/journal/5516/551662868010/) | Hip, knee, ankle, shoulder | 5 phases | Directional description only; **no numeric angles** | 17 lifters, 3 cam 60 fps, 2D | — | VERIFIED (that no numbers given) |
| 21 | [JSSM 13:417, adolescent males](https://www.jssm.org/jssm-13-417.xml%3EFulltext) | Hip, knee | 1st pull | Angular **velocity** only; heaviest lift had greater hip extension velocity; no angle values | 9 elite adolescent males, APAS 50 Hz | — | VERIFIED (that no angles given) |

### A2. Answers to the five sub-questions

1. **Key-phase kinematics with means/SDs.** Only #1–4, #6–7 give usable per-phase mean±SD. All SDs are **between lifters** on single (or best) lifts. Heavy vs light load: only velocity differences found (#21), no angle magnitudes. Elite vs novice: knee 14–17 deg and hip 8–14 deg at end of first pull / transition / second pull (#6–7); no difference at the catch (-0.2 deg knee).
2. **Within-lifter rep-to-rep variability of snatch joint angles.** **NO EVIDENCE FOUND.** Closest: barbell-trajectory SEM of 0.4–2.3 cm (#18) and the qualitative statement that variability grows from first pull to catch. A squat-kinematics paper on inter-/intra-individual variability exists ([PubMed 31442623](https://pubmed.ncbi.nlm.nih.gov/31442623/)) but I could not read it. Reference: squat is a poor proxy for the snatch (**ASSUMPTION**).
3. **Test-retest reliability (ICC/SEM/MDC) of joint angles in weightlifting, 2D vs 3D.** **NO EVIDENCE FOUND** for the snatch specifically. Generic 2D Kinovea squat MDC 5.5–7.9 deg (#16, **SECONDARY**). 3D markerless vs marker-based snatch: RMSD 8–22 deg (#10–13), and the authors concluded the systems are not comparable (#"lack of comparability", **VERIFIED**). IMU vs optical: "<=5.8%" error (PAAH 306, **VERIFIED**; percent, not degrees).
4. **Hopkins SWC (0.2 x between-subject SD) applied to snatch joint angles.** **NO EVIDENCE FOUND.** I found SEM/SRD applied to barbell kinematics (#18) and SWC applied to other variables, not to joint angles.
5. **Angle-to-outcome relationships.** Direction only: successful lifts had larger knee and hip angles (more extended) at the end of the second pull ("preparation for aerial phase") in elite women (#8); National-level lifters had greater knee and hip extension at second pull than college-level (SECONDARY, [PAAH search summary](https://www.mdpi.com/2673-4591/10/1/22)); greater load associated with steadier trunk through the first pull (SECONDARY, [ISBS paper](https://commons.nmu.edu/cgi/viewcontent.cgi?article=2811&context=isbs), not readable). Failures in elite men are explained by barbell position, not joint angle (#19). No threshold angle "below which the lift fails" found.

## Part B — Coaching schools

I could read only the Catalyst pages directly; other rows come from search summaries and should be treated as **SECONDARY / NO EVIDENCE FOUND**, not as proof of absence in books I could not access.

| School | Numeric angle targets/tolerances? | Evidence |
|---|---|---|
| Catalyst Athletics / Greg Everett | **No.** "Shins inclined forward", "shoulders slightly (SLIGHTLY) in front of bar", "same back angle from start to above the knees". Zero degree values in start-position and phases articles. | VERIFIED ([start position](https://www.catalystathletics.com/article/49/The-Olympic-Lift-Starting-Position-Snatch-Clean/), [phases](https://www.catalystathletics.com/article/2189/Dial-in-the-Phases-of-the-Snatch-Clean/)) |
| Rippetoe / Starting Strength | **No numbers found.** Qualitative: snatch back angle stays more constant/horizontal than in deadlift. | SECONDARY ([article](https://startingstrength.com/article/back-angle-and-spinal-position)) |
| Pendlay | NO EVIDENCE FOUND | — |
| CrossFit L1 / Journal | NO EVIDENCE FOUND (PDF unreadable; a "90 deg knee" at power-snatch reception appeared in a search summary, unverified) | SECONDARY |
| Pierce / Burgener / USAW SPC | NO EVIDENCE FOUND in pages searched | — |
| Soviet (Medvedev, Vorobyev, Roman) | Numeric models exist in Russian texts per the literature, but I could not access them; no numbers retrieved | NO EVIDENCE FOUND |
| Bulgarian (Abadjiev) | Training-load philosophy; **no technique angle numbers** in results | SECONDARY |
| Chinese | Qualitative ("clear knees back", quad-dominant pull); no numbers found | SECONDARY |
| Kono, Takano | No numbers found in results (Takano articles are qualitative coaching-process pieces) | SECONDARY |
| Polish/Smalcerz, Georgian/Talakhadze, Ilyin analyses | Not located | NO EVIDENCE FOUND |

**Pattern:** Coaching practice is cue-based ("same back angle", "knees over bar", "hips and shoulders rise together"). I found no school that states a tolerance in degrees. Only common numeric content is toe-out of 10–15 deg (stance, not a joint angle; SECONDARY).

## Synthesis

### (a) Natural within-lifter rep-to-rep SD per joint
Not measured in the literature for snatch angles. Bounds only (all **INFERRED**/**ASSUMPTION**):
- Lower bound: measurement noise of good 3D systems, ~2–5 deg.
- Upper bound: between-lifter SDs of 8–18 deg (#1–4, #6–7) which include anatomy and style; within-lifter SD is certainly smaller.
- Barbell data show variability rising from pull to catch and falling at maximal loads (#18), so expect larger rep-to-rep SD at the catch/bottom and with lighter loads (**INFERRED** from barbell analog).
- My planning guess: 2–4 deg at knee/hip in pulling phases, 3–6 deg at catch, elbow 3–5 deg (**ASSUMPTION**, no source).

### (b) Differences with success/failure or technique level
| Joint | Difference | Context |
|---|---|---|
| Knee | 14–17 deg | top-elite vs sub-elite, end of 1st pull, transition, 2nd pull (#6) |
| Hip | 8–14 deg | same, M1–M2 (#7); ~1 deg at M3 |
| Knee/hip | direction only | success vs fail at end of 2nd pull, elite women (#8) |
| Trunk | none quantified | — |
| Elbow | none quantified; elbow flexion in 1st pull is a coaching fault but no threshold | — |

### (c) Defensible smallest worthwhile change
| Joint | Hopkins 0.2 x between-SD (**INFERRED**, from #1–4, #6–7) | Evidence-based "meaningful" magnitude | Verdict |
|---|---|---|---|
| Knee | ~1.9–2.4 deg (SD 9.5–12) | 14–17 deg (skill level) | Statistical SWC is below noise; practical "report" threshold ~10 deg |
| Hip | ~1.6–3.6 deg (SD 8–18; 0.2x23 up to ~5.6 at transition) | 8–14 deg | ~10 deg |
| Trunk | ~2–5.6 deg (SD 10–28, IMU convention) | none | No supported number; ~10 deg is a placeholder (**ASSUMPTION**) |
| Elbow | ~1–2 deg (SD 5–10) | none | No supported number; ~10 deg placeholder (**ASSUMPTION**) |

Honest read: the 0.2xSD convention yields 1.5–3.5 deg, but those are not detectable with a phone; effect sizes known to matter are around 8–17 deg. A 10 deg "worth reporting" is a defensible middle but is **not** a number any source states.

### (3) Recommended repeatability SD threshold (effect/3) — INFERRED
Assuming reported effect X = 10 deg at all joints, SD_repeat <= X/3 ~ **3.3 deg**. If one insists on the SWC-scale effect of ~3 deg, the SD would have to be ~1 deg, which is below any published video system (**INFERRED**).

| Joint | Effect worth reporting | Max repeatability SD (effect/3) |
|---|---|---|
| Knee | 10 deg (range 8–15) | ~3 deg |
| Hip | 10 deg | ~3 deg |
| Trunk | 10 deg (placeholder) | ~3 deg |
| Elbow | 10 deg (placeholder) | ~3 deg |

Compare with Thiele 2024: knee RMSD 8.3, hip 22.5, ankle 10.0 (#10–12). Even a 12-camera system fails this threshold at the hip, and one phone will do no better. 2D Kinovea squat MDC 5.5–7.9 deg implies SEM ~2–2.8 deg (MDC = 1.96 x SQRT2 x SEM; **INFERRED**), which is just inside the threshold under manual, ideal conditions only.

## Caveats and gaps
- **Biggest gap:** zero data on within-lifter rep-to-rep SD of snatch joint angles, and zero on test-retest MDC for snatch angles. This is the number the app most needs. It would need to be measured in-house (repeat reps of the same load, 3D reference).
- All between-lifter SDs come from tiny samples (n=6–14), single best lifts, inconsistent angle conventions (hip 24 deg at start in #2 is not anatomical flexion; trunk convention unclear).
- Elite-vs-subelite differences reflect anatomy and style, not within-lifter "this rep vs best rep" comparison; transfer is **ASSUMPTION**.
- Several full texts were blocked (JSCR 2012 Greek study, ISBS knee-trunk paper, MDPI pages, PubMed). Values tagged SECONDARY need re-verification before citing.
- Coaching coverage is thin; Soviet and Bulgarian primary technique manuals, Pierce/USAW curricula, Georgian/Polish/Ilyin analyses were not accessed.
- Success-vs-failure in elite men is explained by barbell position, so angle deltas may not predict outcome even when large.
