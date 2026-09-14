# 05 — Technical feasibility: can pose estimation detect snatch faults reliably?
Ticket: [#5](https://github.com/jirigrill/snatch-exercise-validation/issues/5) · Status: resolved · Date: 2026-09-14

## Headline

No. The single most relevant peer-reviewed study — a 2024 validation of a state-of-the-art deep-learning markerless system against Vicon **on the snatch specifically, with 21 competitive weightlifters** — found hip flexion RMSD of **22.5°** and joint-centre errors of **4.7–6.3 cm**, and concluded the systems were "not interchangeable" and that reliable technique conclusions were "impossible." Critically, that study used **12 synchronised cameras at 100 Hz** in a lab; the product proposes one phone. Meanwhile the signal to be measured — snatch horizontal bar displacement — is only **4–6 cm**, i.e. *smaller than the measurement error of the best available system*. Bar-path tracking is genuinely solved and survives; joint-level fault diagnosis is not currently credible to an expert user, and causal attribution has **no published precedent at all**.

## Key finding in one line

Measurement error (4.7–6.3 cm, 22.5° at the hip) **exceeds the magnitude of the fault being diagnosed** (4–6 cm of horizontal drift). That is not a tuning problem; it is an inverted signal-to-noise ratio.

## Fault-by-fault tractability

| Fault to detect | What it requires | Tractable today? | Evidence |
|---|---|---|---|
| **Bar path / horizontal displacement** | Track a high-contrast circular plate end in 2D from a fixed lateral view. Classical CV (Hough circles, colour blob, or a small detector) + homography scaling. | **YES — effectively solved** | Iron Path, WL Analysis, Kinovea all ship this. Sports-science papers routinely derive bar kinematics from a single 60 Hz consumer camera in Kinovea ([PMC7829930](https://pmc.ncbi.nlm.nih.gov/articles/PMC7829930/), **VERIFIED**). Note the Theia3D snatch study explicitly could NOT get bar kinematics from pose keypoints — wrist trajectory is not the bar ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/), **VERIFIED**) — so bar path must be tracked as an *object*, not inferred from a skeleton. |
| **Early arm pull (timing)** | Detect elbow-flexion onset to within a few tens of ms, and distinguish it from passive elbow bend under load. Requires reliable elbow angle. | **NO** | The snatch validation study could not even *compare* elbow and shoulder angles to the criterion — differing rotation sequences, and the marker-based elbow saturated near 160° ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/), **VERIFIED**). Upper-limb joint-centre error was 5.7 ± 1.5 cm, worse than lower limb. Elbow angle is precisely the signal needed and precisely the one not validated. |
| **Pulling too early / too late (timing to ms)** | Event detection at ≤~20 ms resolution across the 2nd pull. | **NO at 30 fps; marginal at 240 fps** | 30 fps = 33 ms/frame, so a 6-frame turnover (see arithmetic below). The same study *failed to detect knee flexion in the transition phase in ~10% of trials* that Vicon captured — i.e. it missed the double-knee-bend event entirely one time in ten ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/), **VERIFIED**). A 10% event-miss rate is fatal for timing claims. |
| **Catch depth & position** | Hip/knee flexion angle at an extreme, out-of-distribution posture (deep overhead squat, fully abducted shoulders). | **NO — worst case** | Hip-flexion RMSD in the turnover phase = 19.2 ± 7.4°; whole-lift hip flexion 22.5 ± 7.0° ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/), **VERIFIED**). Authors state errors *grew with larger angles and velocities* — the catch is both. Clinical acceptability threshold is ≤5°; "almost all estimated lower limb joint angles exceeded this value" (range 4.7–29.9°). |
| **Jump forward / back** | Foot-position displacement in the sagittal plane, in cm, plus a stable floor reference. | **PARTIALLY** | This is a large-amplitude, low-frequency, high-contrast signal (feet leave and re-contact the floor). Closest to bar-path in difficulty. But ankle/foot are the *most* error-prone joints in dynamic tasks — greatest errors in "distal, dynamic joints (e.g., ankles)" ([IEEE Access 2026, PMID 42238785](https://pubmed.ncbi.nlm.nih.gov/42238785/), **VERIFIED**). **INFERRED**: detecting *that* the athlete jumped forward is feasible; quantifying it to the cm is not. |
| **Lockout stability** | Sub-degree tracking of small oscillations of the elbow/shoulder under load, post-catch. | **NO** | Requires exactly the upper-limb angles that could not be validated (above). Oscillation amplitude is far below the 5.7 cm upper-limb positional error. **INFERRED** from the same source. |
| **Torso angle at first pull** | Trunk segment inclination in the sagittal plane during the slowest phase of the lift. | **BEST CANDIDATE — cautiously yes** | The first pull is the slowest phase, and sagittal-plane trunk/hip flexion is the best-validated quantity across the literature (OpenCap sagittal knee/hip CMC > 0.94, grand mean MAE 3.85°, [PMID 38905926](https://pubmed.ncbi.nlm.nih.gov/38905926/), **VERIFIED**). **Caveat**: the snatch study reported *no* trunk values at all, and first-pull hip-flexion RMSD was its **worst** phase result at 27.9 ± 8.8° — plausibly because the torso is occluded by the loaded bar and plates. **NO EVIDENCE FOUND** that trunk angle is measurable during a loaded first pull. |
| **Bar contact height** | Vertical bar position at hip/thigh contact, ±~2 cm, plus detection of the contact event. | **PARTIALLY** | The *bar* half is tractable (object tracking). The *hip landmark* half is not: hip joint-centre error was 6.0 ± 1.3 cm ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/), **VERIFIED**), and reference bar heights are reported to 1 cm precision (end of 2nd pull 0.99 ± 0.02 m, [PMC3990899](https://pmc.ncbi.nlm.nih.gov/articles/PMC3990899/), **VERIFIED**). Error is 6× the precision required. |
| **Causal attribution between faults** ("your early arm pull caused the loop") | A labelled dataset of expert-annotated snatch faults *with causal links*, plus a model that distinguishes cause from correlate. | **NO — no published precedent** | **NO EVIDENCE FOUND.** See the attribution section below. Not "hard"; absent from the literature. |

## The temporal-resolution math

### Inputs from the literature (all VERIFIED)

| Quantity | Value | Source |
|---|---|---|
| Peak barbell vertical velocity, 2nd pull (elite juniors, ~122 kg) | **1.82 ± 0.12 m/s** | [PMC3990899](https://pmc.ncbi.nlm.nih.gov/articles/PMC3990899/) |
| Peak barbell velocity, snatch at 100% 1RM (transducer, 100 Hz) | **2.00 ± 0.17 m/s** | [PMC11843885](https://pmc.ncbi.nlm.nih.gov/articles/PMC11843885/) |
| Peak barbell velocity, snatch (competition video) | up to **4.17 m/s** | [PMC7829930](https://pmc.ncbi.nlm.nih.gov/articles/PMC7829930/) |
| Barbell **horizontal** displacement (the fault signal) | toward lifter **6 ± 3 cm**; away **4 ± 3 cm** | [PMC3990899](https://pmc.ncbi.nlm.nih.gov/articles/PMC3990899/) |
| Bar height at end of 2nd pull | 0.99 ± **0.02** m | [PMC3990899](https://pmc.ncbi.nlm.nih.gov/articles/PMC3990899/) |
| Phase durations (knee-extension / flexion / force / inertial ascent / squat support) | 0.454 / 0.290 / 0.416 / 0.552 / 0.532 s | [PMC9113912](https://pmc.ncbi.nlm.nih.gov/articles/PMC9113912/) |
| Third pull (turnover) as % of lift cycle | **7%** elite, 3% amateur | [PMC10559295](https://pmc.ncbi.nlm.nih.gov/articles/PMC10559295/) |
| Peak hip/knee/ankle extension angular velocity, 2nd pull (Vicon) | **458–473 °/s** | [PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/) |

**Turnover duration, derived (INFERRED):** summing the five reported phases gives 0.454 + 0.290 + 0.416 + 0.552 + 0.532 = **2.24 s** total. The third pull at 7% of cycle → 0.07 × 2.24 ≈ **0.157 s**. This independently corroborates the widely quoted ~0.2 s turnover. Two sources, two methods, same order of magnitude.

### The arithmetic

Bar travel between consecutive frames, at v = 1.8 m/s:

```
30 fps  → 1/30  = 33.3 ms/frame → 1.8 × 0.0333 = 6.0 cm of bar travel per frame
60 fps  → 1/60  = 16.7 ms/frame → 1.8 × 0.0167 = 3.0 cm per frame
120 fps → 1/120 =  8.3 ms/frame → 1.8 × 0.0083 = 1.5 cm per frame
240 fps → 1/240 =  4.2 ms/frame → 1.8 × 0.0042 = 0.8 cm per frame
```

**Read that against the 4–6 cm horizontal displacement being measured.** At 30 fps, the bar moves 6.0 cm between frames — the *entire* fault amplitude occurs inside one frame interval. 30 fps is unusable in principle, not merely imprecise. 60 fps is marginal. **120–240 fps is a hard requirement**, which is a real product constraint (see caveats).

Frames available to characterise the ~0.16–0.2 s turnover:

```
30 fps  → 0.20 × 30  =  6 frames
60 fps  → 0.20 × 60  = 12 frames
120 fps → 0.20 × 120 = 24 frames
240 fps → 0.20 × 240 = 48 frames
```

Six frames cannot support a claim about *when* within the turnover something happened. Joint rotation between frames, at 470 °/s:

```
30 fps  → 470/30  = 15.7° of hip rotation between frames
60 fps  → 470/60  =  7.8° between frames
120 fps → 470/120 =  3.9° between frames
```

**INFERRED, and this is the key compounding insight:** at 30 fps the *inter-frame* hip rotation (15.7°) is smaller than the *measured hip-flexion error* (22.5°) of the best validated system. Even infinite frame rate does not rescue the joint angles — the per-frame estimate is the binding constraint. Frame rate and keypoint accuracy are two independent failure modes, and **both** fail.

### Motion blur

Blur is the length of bar travel during the exposure:

```
1/60 s  shutter → 1.8 / 60   = 30.0 mm of smear
1/600 s shutter → 1.8 / 600  =  3.0 mm
1/1000 s shutter → 1.8 / 1000 =  1.8 mm
```

**VERIFIED, and telling:** the snatch validation study locked shutter at **1/600 s** ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/)) — a deliberate lab choice. A phone on auto-exposure in a dim garage will *not* select 1/600 s; it will open the shutter to gather light, producing ~30 mm of smear on the bar and worse on the fast-moving wrists. **INFERRED**: this makes the app's accuracy a function of the user's gym lighting, which is uncontrollable and will vary shot to shot. A garage lifter is close to the worst case: low light forces long exposure exactly when short exposure is required.

## Pose models: published accuracy

Benchmark scores are on **COCO/MPII — photos of everyday poses**. They are a ceiling under ideal conditions, not a predictor of snatch performance.

| Model | Type | Published accuracy | Notes for this use case |
|---|---|---|---|
| **MediaPipe BlazePose** | 2D (+ weak 2.5D) | Vendor reports PCK@0.2 ~95–97% on its own yoga/fitness eval set; no COCO AP published | **SECONDARY** (vendor, not peer-reviewed). 33 keypoints, optimised for on-device speed. No snatch validation — **NO EVIDENCE FOUND**. |
| **MoveNet** | 2D | Vendor-reported only; no peer-reviewed COCO AP | **SECONDARY**. Accuracy explicitly traded for latency. |
| **OpenPose** | 2D multi-person | ~61–65 AP COCO test-dev | **SECONDARY**. Common 2D front-end in biomech studies. |
| **YOLOv8-pose** | 2D | ~68–71 COCO AP (size-dependent) | **SECONDARY** (vendor). |
| **ViTPose** | 2D | up to **81.1 AP** COCO test-dev (ViTPose-G) | **SECONDARY** (arXiv 2204.12484). Top config not phone-deployable. |
| **RTMPose** | 2D | ~75.8 AP COCO (RTMPose-L), real-time/mobile target | **SECONDARY** (arXiv 2303.07399). |
| **Sapiens (Meta)** | 2D + depth/normals | SoTA on several body benchmarks; 0.3–2B params | **SECONDARY** (arXiv 2408.12569). Too large for on-device; no barbell validation. |
| **Apple Vision body pose** | 2D 19 joints; 3D via `VNHumanBodyPose3D` | **Apple publishes no accuracy figures** | **NO EVIDENCE FOUND** for any quantitative accuracy or barbell validation. |
| **Theia3D** (the one actually tested on snatch) | 3D, multi-camera, commercial DL | **Hip flexion RMSD 22.5°; joint centres 4.7–6.3 cm** on the snatch | **VERIFIED** — [PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/). Most capable system here on the actual movement, and it failed. |

**The critical reading:** the only entry with a snatch-specific number is a *multi-camera lab system*, and it is the one that failed. Every phone-deployable model above has **zero** published validation on Olympic weightlifting. **NO EVIDENCE FOUND** for peer-reviewed validation of MediaPipe, MoveNet, or Apple Vision against mocap on the snatch or clean & jerk.

## Validation against marker-based mocap: the actual numbers

| Study | Task | Error | Tag |
|---|---|---|---|
| Thiele et al. 2024, *Int J Exerc Sci* 17(1):1629–1647, [PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/) — **decisive** | **Snatch**, 21 competitive weightlifters, 131 trials, 65/75/80% 1RM. Theia3D 12 cams @100 Hz vs Vicon 10 cams @200 Hz | Hip flexion RMSD **22.5 ± 7.0°** (1st pull 27.9°, transition 29.9°); knee abduction **18.2 ± 9.0°**; knee flexion 8.3°; ankle 9–10°. Joint centres: hip 6.0, shoulder 6.3, wrist 5.7, knee 4.7, ankle 3.5 cm. **~10% of trials: transition knee flexion not detected at all.** Underestimated peak extension velocity (290–397 °/s vs 458–473 °/s); "not able to estimate the true extension velocity for the hip or the knee." | **VERIFIED** |
| OpenCap validation, [PMID 38905926](https://pubmed.ncbi.nlm.nih.gov/38905926/) | Jump-landing, hops; 437 trials; 2 smartphones | Grand mean **MAE 3.85°, RMSE 4.34°**. Sagittal knee/hip CMC > 0.94; **frontal CMC 0.47–0.78; transverse 0.51–0.60** | **VERIFIED** |
| [PMID 42238785](https://pubmed.ncbi.nlm.nih.gov/42238785/), IEEE Access 2026 | Gait, sit-to-stand, trunk flexion; 51 participants, 669 trials; **single smartphone @30 Hz** | Trajectory RMSE **5.95 cm**; joint angle RMSE **2.10–10.98°**; worst in "distal, dynamic joints" | **VERIFIED** |
| Kanko et al. 2022, [PMID 36252308](https://pubmed.ncbi.nlm.nih.gov/36252308/) | Running, walking, CMJ; 15 participants; **multi-view 200 Hz** | Hip **0.1–10.5°**, knee/ankle 0.7–3.9° — best result found, but requires multi-camera 200 Hz, not a phone | **VERIFIED** |
| Systematic review, [PMID 40526450](https://pubmed.ncbi.nlm.nih.gov/40526450/), *J Sports Sci* 2025, **53 studies** | Walking, squat, jump, run, cut | Validity differences **0.2° to 28.6°**; correlations "negligible (including negative values) to very strong." Hip flexion SEM **4.0–11.1°**. Verdict: MMC "not largely comparable to marker-based systems" | **VERIFIED** |
| Single-leg squat validity, [PMID 36198251](https://pubmed.ncbi.nlm.nih.gov/36198251/) | Single-leg squat, adolescents, 2D pose vs 3D | Sagittal r = 0.68–0.94. **Frontal-plane knee angle r = 0.20**; traditional 2D r = 0.05 | **VERIFIED** |

**Benchmark for interpretation (VERIFIED):** the clinical-gait acceptability threshold cited by the snatch authors (McGinley et al.) is **≤5°**. On the snatch, "almost all estimated lower limb joint angles exceeded this value," range 4.7–29.9°.

## Occlusion and out-of-distribution poses

- **VERIFIED**: the snatch study's joint-centre errors were *larger than the same system's published errors on gait and boxing*; authors attribute this to "occlusion caused by the weights and the barbell," while honestly flagging the attribution as speculative since Theia3D's training data is undisclosed. Occlusion degradation on loaded barbell movements is **observed**; its mechanism **inferred**.
- **VERIFIED**: errors "grew with larger angles and velocities." The catch is the largest-angle and the turnover the highest-velocity part of the lift — the model degrades precisely where the coaching value is.
- **INFERRED (well-supported)**: COCO/MPII contain almost no deep overhead squats with a loaded bar and fully abducted, externally rotated shoulders. The catch is out-of-distribution by construction. The 22.5° hip error and the inability to compare shoulder/elbow angles at all are consistent with this.
- **ASSUMPTION**, flagged: that a snatch-specific fine-tune closes the gap. Plausible, but the transition-phase *detection failure* (10% of trials) suggests part of the loss is information genuinely absent from the pixels (knee occluded behind the plate), which fine-tuning cannot recover.

### Quantified degradation (each factor measured independently)

These figures come from general-purpose CV benchmarks, so they are **SECONDARY** for this application, but they establish that each degradation factor is real and large. All apply to the snatch.

| Factor | Measured penalty | Source | Applies here? |
|---|---|---|---|
| **Occlusion, 2D keypoints** | HRNet-W48: **76.3 AP (COCO) → 37.8 AP (OCHuman)**, a 50% relative collapse. With ground-truth boxes supplied: 78.1 → 65.0 AP (**−13.1 pp**) | [arXiv:2101.11223](https://arxiv.org/abs/2101.11223) | Yes — plates over hips, arms over torso. *But* ~⅔ of the OCHuman drop is detection/association failure from crowding; a single-athlete video has none, so the **~13 pp figure is the honest one** here. |
| **Occlusion, 3D mesh methods** | SPIN PA-MPJPE **59.2 → 68.3 mm** (3DPW → 3DOH), only +9 mm | [arXiv:2104.08527](https://arxiv.org/abs/2104.08527) | Yes — and notably mild. Body-prior/mesh methods absorb occlusion far better than bare keypoints. |
| **Rare / out-of-distribution poses** | MPJPE **46.8 → 89.1 mm on the rarest 10% of poses (+90%)** | [arXiv:2007.09389](https://arxiv.org/abs/2007.09389) | Yes — the snatch catch is a rare pose by any dataset measure. |
| **COCO long-tail bias** | AP 74.4 vs balanced AP 65.4 (**−9.0 pp**) | [arXiv:2208.07755](https://arxiv.org/abs/2208.07755) | Confirms the upright-everyday-pose bias of the training data. |
| **Extreme camera angle** | ViTPose-s: **35.1 AP bottom-view vs ~70 AP COCO** | [arXiv:2307.06737](https://arxiv.org/abs/2307.06737) | Yes if the user's camera is low or off-axis — angle alone can halve AP. |
| **Motion blur, 2D** | DEKR **62.5 → 28.6 mAP (−33.9 pp, −54%)** | [arXiv:2507.22438](https://arxiv.org/abs/2507.22438) | Yes — the second pull is the fastest phase. |
| **Motion blur, 3D** | VideoPose3D **+22.4 mm MPJPE** (33.4 → 55.8, HumanEva-I-C) | [arXiv:2312.06797](https://arxiv.org/abs/2312.06797) | Same source ranks corruptions: blur 78.1 mm vs **cropping/occlusion 118.1 mm — occlusion is the worse of the two.** |
| **Occlusion, biomechanics-side** | Pose2Sim: mean joint errors 3.0–4.1° overall, but **CMC falls to 0.75 for a partially occluded ankle** (cycling) and 0.65 for hip (running, with a 15° systematic offset) | [PMID 35408326](https://pubmed.ncbi.nlm.nih.gov/35408326/) | Yes — shows occlusion produces *systematic offsets*, not just noise. Systematic error does not average out over reps. |

**INFERRED, and this is the key point: these factors stack.** The snatch triggers occlusion, rare pose, motion blur, and (often) a suboptimal camera angle simultaneously. The Thiele snatch study is the compound result measured directly with *good* hardware — 22.5° hip RMSD and 10% trial loss. A single-phone pipeline should be expected to do worse, not better. The general-CV numbers above and the snatch-specific numbers are mutually corroborating, from independent literatures.

**Remaining gaps — NO EVIDENCE FOUND**: quantified rolling-shutter error in human pose estimation; any study isolating shutter speed as an independent variable; per-joint mm error as a function of occluder size; keypoint AP degradation for gymnastics/yoga (only activity-*classification* accuracy exists).

## Camera-angle fragility, 3D lifting, and LiDAR

- **VERIFIED**: a single 2D view cannot measure frontal-plane knee angle — r = **0.20** against 3D mocap on a *slow, unloaded* single-leg squat ([PMID 36198251](https://pubmed.ncbi.nlm.nih.gov/36198251/)). Knee valgus in the catch and torso rotation are **not measurable** from one prescribed angle. Any app claim about knee cave from a single lateral view is unsupported.
- **VERIFIED**: even multi-camera 3D shows frontal CMC 0.47–0.78, transverse 0.51–0.60 ([PMID 38905926](https://pubmed.ncbi.nlm.nih.gov/38905926/)). The snatch study *declined to report transverse-plane results at all* due to unreliability — torso rotation is unreported even in the lab.
- **INFERRED**: monocular 3D lifting adds error on top of 2D keypoint error. A prescribed angle constrains but does not solve this, and transfers burden to the user: any deviation silently degrades output without the app knowing.
- **iPhone LiDAR does not help.** **VERIFIED**: iPhone 13 Pro depth sensor has a "reported maximum range of **5 m**"; in a controlled survey study it showed MAE **3.83–5.08 cm**, RMSE 4.58–5.39 cm, with sharp features smoothed ([PMC13517338](https://pmc.ncbi.nlm.nih.gov/articles/PMC13517338/)). Filming a full snatch needs ~3–4 m standoff — near the range limit — and the ~4–5 cm error is the same magnitude as the pose error it would need to correct. That source reports **no** data on moving subjects or bright conditions; **NO EVIDENCE FOUND** for LiDAR tracking a 2 m/s barbell. It is a sparse, upsampled, low-frame-rate depth map built for static AR scene meshing.

## The attribution problem — the crux

Even granting perfect keypoints, the product's core promise (a *named* fault plus its *cause*) requires supervision that does not exist.

**Dataset search results:**

- **NO EVIDENCE FOUND**: any public dataset of expert-annotated *snatch* faults. No snatch fault-label dataset was located on arXiv, PubMed, PMC, or paperswithcode.
- **VERIFIED — the strongest negative result in this report.** A 2025 systematic review of exercise classification in resistance training ([PMC12513948](https://pmc.ncbi.nlm.nih.gov/articles/PMC12513948/)) screened 2,062 records and included **44 studies / 49 models**. Findings:
  - **The snatch does not appear anywhere.** Only one study included any Olympic lift ("clean and jerk," alongside box jump, kettlebell swing, burpee). "No snatch appears in the extracted exercise lists."
  - Technique-*error* classification was rare and trivial: one study classified correct vs incorrect **sit-ups and curl-ups** (96%); five others "analysed users' exercise form." Everything else classified *which exercise* was being done — a fundamentally easier task.
  - Vision was almost absent: only **one** 2D RGB camera study among 49 models; IMUs dominated (24/49).
  - **All 49 models carried high risk of bias**; 36 had unclear applicability. Samples were 1–159 participants, only seven exceeded 30, and 24 models had EPV < 10 (overfitting risk). 48/49 lacked proper discrimination and calibration assessment.
  - Headline accuracies (95–99.996%) are inflated: over half the problems used fewer than 10 exercises, and the authors state accuracy is "likely inflated relative to real gyms" and that cross-technology comparison "is not possible."
- **Named-fault datasets for *any* barbell lift: only two, neither usable.** **Fitness-AQA** (squat / row / overhead press, with naturally-occurring fault labels) is licensed **non-commercial**; a 7-label squat set (Chern) was **never released**. **VERIFIED**. Neither covers the snatch.
- **The one AQA work touching weightlifting** is an undergraduate final-year project: **1,570 frames, phase labels only** (not fault labels), unreleased. **VERIFIED**. That is the entire state of the art for weightlifting AQA.
- **NO EVIDENCE FOUND** for any published work performing **causal attribution** between weightlifting faults — nothing establishes "early arm pull caused the loop" rather than merely co-occurring with it. This is not a hard problem with a partial solution; it is absent from the literature. A survey of the "explainable AQA" literature found every near-miss falls into one of four non-causal categories (**VERIFIED**):
  1. **Score + attention/saliency map** — shows where the model looked, not why the lift failed.
  2. **Rubric/rule-based per-element deductions** — e.g. NS-AQA (diving).
  3. **Deviation-from-reference sentences from a grammar** — this is what **AIFit** actually does. Its "human-interpretable feedback" is *descriptive/comparative*: how you differ from a reference, not what caused what.
  4. **LLM-templated text with generic consequences** — e.g. CoT-AFA ([arXiv:2512.15153](https://arxiv.org/abs/2512.15153)) emitting boilerplate like "will cause strain," not a video-grounded causal link.
- The two most causal-sounding papers both fail on inspection: **FineCausal** ([arXiv:2503.23911](https://arxiv.org/abs/2503.23911)) and **CaFlow** ([arXiv:2511.21653](https://arxiv.org/abs/2511.21653)), where "causal" denotes representation de-confounding, not causal claims about technique. **VERIFIED**. None uses counterfactual reasoning to validate a fault→consequence link.
- Reference infrastructure: 2025 AQA survey with dataset tables ([arXiv:2502.02817](https://arxiv.org/html/2502.02817)), [Awesome-AQA](https://github.com/ZhouKanglei/Awesome-AQA). **Caveat**: paperswithcode leaderboards are now defunct (redirect to HuggingFace); AQA-7 per-action sample counts could not be retrieved (host timed out) and are **left unstated rather than estimated**.
- **INFERRED**: causal attribution is also *scientifically* fraught, not just technically. Faults in a ballistic chain co-occur by mechanical necessity, so observational kinematics generally cannot separate cause from consequence. A bar loop and an early arm pull are mutually entailed; asserting a direction of causation from a single video is unsupported inference, however it is generated.
- **VERIFIED, sobering**: even *with* 3D mocap + EMG on 23 lifters, a 2024 study distinguishing **elite from varsity** snatch technique found several asymmetries but concluded they "may not be critical factors in achieving a successful snatch lift," since all lifters completed the lift ([PMID 39182264](https://pubmed.ncbi.nlm.nih.gov/39182264/)). If full lab instrumentation cannot confidently say which kinematic deviations *matter*, an app cannot either. **This undercuts the ground truth itself**: the mapping from kinematics to "fault" is contested in the sports-science literature, not merely unlabelled.

**Generalisation caveat (INFERRED, high confidence):** every dataset located samples either elite athletes in competition or small lab cohorts. The persona — a hobbyist in a garage, mixed loads, variable lighting, uncalibrated camera — is precisely the out-of-distribution case. Models trained on elite lifts will systematically mis-score novices, whose movement variance is larger and whose faults are the actual target.

### The sting in the tail: bar path is tractable but may not be *diagnostic*

This is the most uncomfortable finding in the report, because it constrains even the part that survives.

- **VERIFIED**: in a study of successful vs unsuccessful snatches, peak barbell velocity was **1.698 ± 0.142 m/s (success) vs 1.614 ± 0.163 m/s (failure) — not statistically different**, and *no* phase duration differed significantly either ([PMC9113912](https://pmc.ncbi.nlm.nih.gov/articles/PMC9113912/)).
- **SECONDARY** (via research agent, not independently retrieved): Nagao 2026 tested 13 national-level lifters with a make *and* a miss at identical load, and again found **no significant bar-velocity difference**. The discriminating variables were trunk ROM, hip extension velocity, and dip knee flexion velocity — i.e. **body kinematics, not bar kinematics**.
- **The implication (INFERRED)**: the quantity the app can measure well (bar trajectory and velocity) may not separate a good lift from a failed one, while the quantities that *do* separate them (trunk ROM, hip extension velocity) are exactly those measured at 22.5° hip error and with velocities underestimated by ~40% (290–397 °/s vs 458–473 °/s actual).
- Two independent studies pointing the same way makes this more than an outlier, though I have directly verified only one. **This inverts the naive product intuition**: bar path is not merely "the easy part we start with" — it may be the part that is easy *because* it carries less of the diagnostic signal.

## PROVEN vs SPECULATIVE

### PROVEN (peer-reviewed, with numbers)

1. Barbell path tracking from a single fixed lateral consumer camera is established practice in sports science and shipping commercial products. **VERIFIED**.
2. Peak snatch bar velocity is ~1.7–2.0 m/s (up to 4.17 m/s in competition), and horizontal displacement — the primary fault signal — is only **4–6 cm**. **VERIFIED**.
3. A SoTA multi-camera markerless system on the snatch produces hip-flexion RMSD of **22.5°** and joint-centre errors of **4.7–6.3 cm**, exceeds the ≤5° clinical threshold on nearly every joint, misses the transition event in ~10% of trials, cannot recover true joint extension velocities, and cannot derive bar kinematics from keypoints. Its authors conclude the systems are **not interchangeable** and real-time athlete feedback is "so far impossible." **VERIFIED**.
4. Sagittal-plane joint angles in *slow* tasks are the best-validated output (MAE ~3.85°); frontal-plane and transverse-plane measurements are unreliable, and single-view frontal knee angle is effectively uncorrelated with truth (**r = 0.20**). **VERIFIED**.
5. Markerless accuracy degrades with increasing joint angle and velocity — i.e. worst exactly at the second pull, turnover, and catch. **VERIFIED**.
6. No public dataset of expert-annotated snatch faults exists; the snatch is absent from a 44-study review of resistance-training exercise classification. The only barbell fault-labelled dataset (Fitness-AQA) is non-commercial and excludes the snatch. **VERIFIED / NO EVIDENCE FOUND**.
7. iPhone LiDAR has ~5 m maximum range and ~4–5 cm error on static targets. **VERIFIED**.
8. **Bar velocity does not significantly distinguish successful from failed snatches** ([PMC9113912](https://pmc.ncbi.nlm.nih.gov/articles/PMC9113912/)); phase durations don't either. **VERIFIED**. The discriminating signal appears to live in body kinematics, which is the unmeasurable part.

### SPECULATIVE (explicitly not established)

1. That a snatch-specific fine-tune, or a purpose-built dataset, would bring joint-angle error below the ~5° needed. Plausible but **unproven**; some error is irreducible occlusion. **ASSUMPTION**.
2. That "AI will improve and fix this." Explicitly marked **SPECULATIVE**. The snatch study's own authors hedge that markerless "holds promise to become a suitable alternative" — an aspiration, not a finding, and not a basis for a product roadmap.
3. That 240 fps phone slow-mo plus a fast shutter yields sufficient temporal resolution. The arithmetic supports the *frame rate* being adequate at 240 fps, but **NO EVIDENCE FOUND** that any pose model retains accuracy on 240 fps barbell footage. Frame rate was never the only binding constraint.
4. That a named coaching fault can be inferred from imperfect kinematics at expert-acceptable precision. **NO EVIDENCE FOUND**.
5. That causal attribution between faults is achievable from monocular video. **NO EVIDENCE FOUND**, and mechanically dubious.
6. That multimodal video LLMs solve this. Briefly (ticket #8 covers it): Gemini/GPT/Claude video understanding is trained for semantic description, not sub-centimetre spatial measurement, and typically samples video at ~1 fps — orders of magnitude below the 120–240 fps this movement requires. **INFERRED**: they can generate *plausible-sounding* coaching text, which for an expert persona is the worst failure mode — confident, fluent, and wrong. **NO EVIDENCE FOUND** for any published benchmark of video LLMs on weightlifting technique assessment.

## The expert-user trust problem

This is where the accuracy gap becomes commercially fatal rather than merely disappointing.

- **INFERRED, high confidence**: the persona can already read a bar path. The app's most reliable output is therefore the one that adds least value; its highest-value outputs (fault naming, causal coaching) are its least reliable.
- The error asymmetry is brutal. A hip angle wrong by 22.5° is not a subtle miss — it is visibly wrong to anyone who coaches the lift. A single false positive ("you pulled early" when they did not) is *immediately* falsifiable by the user against their own video, and unlike a beginner, they have the expertise to detect it and the community to broadcast it.
- **INFERRED**: trust here is asymmetric and effectively non-recoverable. Ten correct diagnoses do not offset one obviously wrong one, because the wrong one proves the system does not understand the movement. Beginner form apps survive on plausibility; this persona tests correctness.
- Quantified: at ~10% event-detection failure ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/)) — measured in a **lab with 12 cameras** — roughly one lift in ten would produce a visibly wrong analysis. **INFERRED**: single-phone, in-gym failure rates would be higher. No expert-user product survives a 1-in-10 obvious-error rate.

## Verdict impact

**SUPPORTS NO-GO for the product as specified.** This blocker fires.

It does **not** kill the concept wholesale. Precisely:

**What survives (build this):**
- **Bar path tracking and visualisation.** Proven, cheap, robust. Horizontal displacement, trajectory shape, vertical velocity profile, max height, drop-under distance — all from object tracking, not pose estimation. Requires a scale reference and a fixed lateral camera. **Important limit**: this is descriptive, not diagnostic — bar velocity does not separate makes from misses (see the sting-in-the-tail section). Sell it as a *mirror*, never as a *diagnosis*.
- **Sagittal-plane trunk/hip angle at the first pull**, presented as approximate with a stated error band — the slowest phase and best-validated plane. Marginal, and must not be quantified to the degree.
- **Rep logging, load tracking, side-by-side comparison, self-comparison over time.** Relative change is far more defensible than absolute measurement, since systematic bias partially cancels.

**What dies:**
- Joint-level fault diagnosis at the catch, turnover, or second pull — error is 4× the acceptable threshold at exactly these phases.
- Any timing claim to millisecond precision, including early arm pull.
- Anything in the frontal or transverse plane: knee valgus, torso rotation. Not measurable from one view; unreliable even in the lab.
- **AI narrative coaching that names faults and asserts causes.** No dataset, no validated model, no published precedent (only descriptive, rubric-based, or de-confounding near-misses), and the highest-visibility failure mode for this exact persona.
- AI corrective programming *predicated on* fault diagnosis. Programming from bar path plus load history alone may be defensible; programming from imputed faults is not.

**The strategic bind:** the differentiator (AI fault diagnosis + causal coaching) is the infeasible part; the feasible part (bar path) is already commoditised by Iron Path and others — *and* is the part with the weakest link to lift success. Feasibility does not merely constrain the product; it removes the moat. Recommend re-scoping to a bar-path-plus-tracking tool with honest uncertainty, or targeting a persona that tolerates approximation, which the stated persona explicitly does not.

**One caveat on my own confidence:** the decisive study is a single paper (n=21, one commercial system, *Int J Exercise Science*, a lower-tier journal). Its finding is strongly corroborated in *direction* by the broader markerless literature and by first-principles arithmetic, and its lab conditions were strictly *better* than the product's, so it likely represents a best case. But a single-study foundation for a NO-GO warrants noting. **The arithmetic in the temporal section, however, is independent of that paper and sufficient on its own** to rule out 30 fps capture and to show that measurement error exceeds the 4–6 cm signal.

## If the concept is pursued anyway: least-bad technical choices

Not a rescue plan — the verdict stands — but these follow from the evidence and would reduce (not eliminate) the error.

1. **Use a mesh-recovery model with body priors, not bare 2D keypoints.** Occlusion costs a mesh method ~+9 mm; it costs bare keypoints up to −38 AP. This is the single largest available win. **SECONDARY**.
2. **Capture at ≥120 fps (ideally 240) with a forced fast shutter**, and refuse to analyse footage that fails a brightness/blur pre-check. Never report derived velocity or power below 120 fps.
3. **Track the bar as an object (KLT/detector), never infer it from the wrist keypoint** — Thiele showed the estimated wrist sits consistently *below* the actual bar. **VERIFIED**.
4. **Restrict all angular claims to the sagittal plane**, with a geometric perspective correction. Treat every frontal/transverse output as unusable and do not display it.
5. **Show uncertainty, and prefer within-user deltas to absolute numbers.** Systematic bias partially cancels across a user's own reps; it does not cancel against a population reference.
6. **Gate output on a self-check**: if the transition event is not detected, say so rather than emitting a confident analysis. A visible "couldn't read this rep" preserves far more expert trust than a fabricated diagnosis.


