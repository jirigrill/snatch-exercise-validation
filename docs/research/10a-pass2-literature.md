# 10 — Pass 2: literature verification and gap-closing (smallest worthwhile change)
Date: 2026-10-01 · Scope: second pass on `docs/research/10-smallest-worthwhile-change.md`. File 10 itself was not edited.

**Tags:** **VERIFIED** = I read it this session in the primary full text, or in the official abstract where I say so (table, figure or quote given). **SECONDARY** = only a third-party or summary source. **INFERRED** = my own arithmetic. **NO EVIDENCE FOUND**.

**How I read the sources.** pmc.ncbi.nlm.nih.gov showed a captcha, so I read PMC articles as Europe PMC full-text XML (`https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML`). I pulled the numbers out of the raw XML, HTML or PDF tables myself, not out of a model's summary. JSSM tables came from `jssm.org/tablejssm-…/table00N.xml`. Mastalerz 2019 Fig. 4 is a bar chart, so I measured it in pixels: the y-axis is 1.835 px per degree, so each read-off value is good to about ±1°.

---

## (a) Checking table A1 from the first pass

| A1 row | Source | Verdict | What changed / detail | Tag |
|---|---|---|---|---|
| 1–4 | Khuyagbaatar 2024, PAAH 306 ([article](https://paahjournal.com/articles/10.5334/paah.306), [PDF](https://paahjournal.com/articles/306/files/65aa78324e3c4.pdf)) | **Confirmed** | Every value in Table 1 matches. Additions: (i) each lifter did 3 snatches at **70 % 1RM**, and "each participant's data was averaged". So each SD is the spread **between lifters of their 3-rep means**; no within-lifter SD is reported. (ii) There is also a shoulder column. Snatch shoulder flexion: start 22.1±8.0, 1st pull 26.4±11.4, transition 8.8±13.5, 2nd pull 1.2±15.5, turnover 159.9±6.9, catch 160.8±6.1, end 158.4±6.9°. (iii) The "≤5.8 %" figure comes from the authors' earlier work (Choi et al. 2021); this study did not measure it. | VERIFIED (PDF p.3–5, Table 1) |
| 5 | same | **Confirmed** | Snatch vs clean at the start: knee 62.4 vs 77.5 (p<0.01); trunk 117.0 vs 136.8 (p<0.05). | VERIFIED |
| 6 | "Zhang/Chinese study", PMC6076374 | **Values confirmed, authors corrected** | The paper is **Liu G, Fekete G, Yang H, Ma J, Sun D, Mei Q, Gu Y. Heliyon 2018**. Setup: 2 Sony cameras at 50 Hz, SIMI 3D, recorded at the China National Championship and China Olympic Trial, heaviest successful lift only. Knee values match. Rows the first pass left out (Table 4): **start** knee 64.92±13.28 vs 58.99±13.65, hip 45.84±8.10 vs 49.70±8.61; **M5** knee 42.78±6.03 vs 47.94±7.02, hip 54.35±10.35 vs 61.01±13.79; **M6** (squat) knee 37.67±5.31 vs 40.36±5.85, hip 48.32±7.81 vs 47.73±9.44. None of these differ significantly. | VERIFIED ([Europe PMC XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6076374/fullTextXML), Table 4) |
| 7 | same | **Corrected** | The first pass said hip differences were "not tested". They were tested and are **NS** in Table 4. | VERIFIED |
| 8 | Mastalerz, Szyszka, Grantham, Sadowski 2019, J Hum Kinet 68:69 ([PMC6724589](https://pmc.ncbi.nlm.nih.gov/articles/PMC6724589/), [PDF](https://johk.pl/wp-content/uploads/2023/03/10078-68-2019-v68-2019-06.pdf)) | **Corrected: degree values exist (Fig. 4)** | Digitised success vs fail means. **Knee:** S 57.2 vs 56.1; T 109.5 vs 106.8; **P 156.9 vs 152.3 (Δ +4.6°)**. **Hip:** S 32.7 vs 31.6; T 63.8 vs 63.2; **P 173.3 vs 170.0 (Δ +3.3°)**. Only the P differences are significant (p≤0.05). Error bars are 5–11°; the caption does not say whether they are SD or SE. Design: 14 elite women from the 2013 Worlds (places 1–8), 14 success/fail pairs **at the same load per lifter**, 2 cameras at 50 Hz, APAS. | VERIFIED (figure, digitised ±1°) |
| 9 | Greek elite study, SECONDARY in the first pass | **Now VERIFIED** | This is **Gourgoulis, Aggelousis, Mavromatis, Garas 2000, J Sports Sci 18:643** ([PDF](https://paulogentil.com/pdf/TREINO%20DE%20FORC%CC%A7A/Treinamento%20com%20pesos/G1.pdf)). Table 2: knee decrease during transition **22.2±4.45°** (SD between lifters). Full table is in (b). | VERIFIED (Table 2) |
| 10–12 | Thiele 2024, Int J Exerc Sci ([PMC11728585](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/)) | **Confirmed** | Hip 22.5±7.0, knee 8.3±1.9, ankle 10.0±5.2°. Additions: (i) markerless estimates showed an "offset towards knee extension … a similar but larger offset … for the hip and ankle", so much of the RMSD is **systematic bias**. (ii) The authors say the differences are "likely due to differing models and assumptions, rather than measurement accuracy". (iii) Lifters were sub-elite (relative 1RM 0.93 F / 1.15 M; 24–47 months' experience). (iv) Elbow could not be compared because the marker-based elbow peaked at about 160° with straight arms. | VERIFIED (Table 2, Results/Discussion) |
| 13 | same | **Wording corrected** | The phase RMSDs pool **all lower-limb DoFs** (sagittal plus frontal), not "all sagittal": 1st pull 13.0±6.4, transition 12.3±5.8, 2nd pull 10.1±4.8, turnover 11.0±5.7, recovery 11.6±5.9°. Per-DoF phase values are in (b). | VERIFIED |
| 14, 15 | same | **Confirmed** | 9.7 % (N=14 of 145) of trials were discarded. Joint-centre error: hip 6.0±1.3, shoulder 6.3±1.6, knee 4.7±1.5 cm. | VERIFIED |
| 16 | Kinovea squat, Sensors 26:3749 ([PMC13306374](https://pmc.ncbi.nlm.nih.gov/articles/PMC13306374/)) | **Corrected, now VERIFIED** | The "MDC 5.48–7.87°" range was a subset. **Test–retest** (two performances 20 min apart): SEM 1.98–14.29° and MDC 5.48–39.61° across all variables. For the sagittal joints see (b). Population: 20 healthy active women, light back squat, 30 fps webcams, the deepest of 3 reps. | VERIFIED (Tables 2–3) |
| 17 | "Kinovea overhead squat, Life 15:80" | **Corrected** | The paper is **Soylu et al. 2025**, testing a TecnoBody D-Wall (Kinect) against Kinovea ([PMC11766738](https://pmc.ncbi.nlm.nih.gov/articles/PMC11766738/)). The ICC 0.99 is agreement among the 3 reps within one session (Table 1). **Table 3 test–retest:** Kinovea ICC 0.88–0.93, **SEM 5.9–6.9°**; D-Wall SEM 8.3–10.5° (hip/knee ROM, 29 adults). The abstract's "test-retest ICC 0.99" conflicts with Table 3. | VERIFIED (Tables 1, 3) |
| 18 | Sandau, Langen, Nitzsche 2023, Front Sports Act Living ([PMC10534034](https://pmc.ncbi.nlm.nih.gov/articles/PMC10534034/)) | **Confirmed** | Snatch barbell horizontal SEM 0.004–0.023 m and vertical 0.007–0.022 m. Two consecutive reps per load (85 % / 97 % of planned 1RM), 7 German national-team men, 50 fps. No joint angles. | VERIFIED (Table 1) |
| 19 | Nagao et al. 2019, Sports ([PMC6628121](https://pmc.ncbi.nlm.nih.gov/articles/PMC6628121/)) | **Confirmed (full text)** | DxL 0.11±0.05 vs 0.10±0.06 m; drop Dy3 0.17±0.04 vs 0.18±0.04 m. Barbell only. | VERIFIED (Table 3) |
| 20 | Colombian 2D study ([redalyc](https://www.redalyc.org/journal/5516/551662868010/)) | **Partly confirmed** | The text has no angle values. Table 1 is an image (inter-subject medians), which I did not extract. | VERIFIED (text only) |
| 21 | Harbili & Alptekin 2014, JSSM 13:417 ([article](https://www.jssm.org/jssm-13-417.xml%3EFulltext), [Table 5](https://www.jssm.org/tablejssm-13-417.xml/table005.xml)) | **Corrected: angles ARE reported** | Table 5 gives maximum extension angles for the **two heaviest successful lifts of the same lifters**. This is a within-lifter comparison; numbers are in (b). | VERIFIED (Table 5) |
| A1 text: Kristiansen 2019 squat ([PubMed 31442623](https://pubmed.ncbi.nlm.nih.gov/31442623/)) | | **Still could not open** | The abstract ([AAU portal](https://vbn.aau.dk/en/publications/inter-and-intra-individual-variability-in-the-kinematics-of-the-b/)) reports significant intra-individual differences in **angular velocity**, not angles. No numbers in the abstract. | VERIFIED (abstract) / full text not opened |

---

## (b) All new numbers

### B1. Within-lifter snatch comparisons (the key gap)

| Source | Joint | Phase | Value | Population | Represents | Tag |
|---|---|---|---|---|---|---|
| [Harbili & Alptekin 2014, Table 5](https://www.jssm.org/tablejssm-13-417.xml/table005.xml) | Ankle / knee / hip | Max extension, 1st pull | Heavier vs heaviest lift: 126.2±3.2 vs 128.0±3.5; **144.7±7.0 vs 148.1±6.4**; **93.2±8.3 vs 96.9±8.5** | 9 elite adolescent men (national team, 18.9 y); 2 heaviest successful competition snatches (122.2 vs 126.8 kg) | Within-lifter difference between two near-max reps: Δ +1.8 / +3.4 / +3.7°, **all NS** (0° = full flexion) | VERIFIED |
| same | Ankle / knee / hip | Max extension, 2nd pull | 133.8±5.6 vs 136.4±4.2; **165.2±4.3 vs 165.6±5.9**; 199.2±4.5 vs 200.4±3.2 | same | Within-lifter Δ +2.6 / +0.4 / +1.2°, NS | VERIFIED |
| same (my arithmetic) | Knee, hip | 1st pull | If the NS result is equivalent to a paired t-test with n=9 (t<2.306), then Δ 3.4–3.7° being NS implies SD of within-lifter differences ≳4.4–4.8°, i.e. typical error per lift ≳3.1–3.4° | — | Rough lower bound on rep-to-rep noise plus load effect. The authors used ANOVA, not a paired t, so treat this loosely. | INFERRED |
| [Mastalerz 2019 Fig. 4](https://johk.pl/wp-content/uploads/2023/03/10078-68-2019-v68-2019-06.pdf) | Knee | S / T / P | Success vs fail **57.2/56.1; 109.5/106.8; 156.9/152.3** | 14 elite women, 2013 Worlds, **same load** success/fail pairs | Δ +1.1 / +2.7 / **+4.6°** (P significant) | VERIFIED (digitised) |
| same | Hip | S / T / P | **32.7/31.6; 63.8/63.2; 173.3/170.0** | same | Δ +1.1 / +0.6 / **+3.3°** (P significant) | VERIFIED (digitised) |
| same | Knee, hip | all positions | Error bars about 5–11° | same | Spread between lifters (SD/SE not stated) | VERIFIED (digitised) |
| same (my reading) | — | — | The statistics are reported as F(1,26), an independent-groups df. A 4.6° gap with about 8–10° spread would not normally reach p<0.05 unpaired, so the significance claim is fragile. | — | Caveat | INFERRED |
| [Liu G et al. 2022, Appl Bionics Biomech, Table 4](https://pmc.ncbi.nlm.nih.gov/articles/PMC9113912/) | Knee | End M1 / M2 / M3 / M4 / M5 | Success vs fail **121.85±11.42 / 124.24±9.93; 111.9±6.47 / 118.89±9.22; 153.13±9.22 / 151.84±7.88**; 68.47±8.38 / 68.72±9.37; 44.71±6.2 / 45.29±10.34 | 10 elite men, 73 kg, heaviest successful vs heaviest failed attempt (2019 Worlds, 2019 Asian Champs, 2020 China Olympic Trial); 2-camera 3D SIMI; **paired t-test**; failed loads were 2–9 kg lighter (Table 1) | Within-lifter success−fail Δ −2.4 / **−7.0** / +1.3 / −0.3 / −0.6°, **all NS**. Authors: knee at M2 is "6.99° smaller" in successful lifts. | VERIFIED |
| same | Hip | End M1–M5 | 85.02±5.63 / 88.87±14.27; 111.18±7.75 / 112.22±7.39; **144.68±19.58 / 152.64±6.54**; 99.08±20.43 / 101.67±18.78; 52.38±11.62 / 58.72±16.45 | same | Δ −3.9 / −1.0 / **−8.0** / −2.6 / −6.3°, all NS | VERIFIED |
| same (my arithmetic) | Knee re-bend (M1−M2) | Transition | Success 9.95° vs fail 5.35° | same | Δ ≈ 4.6° more re-bend in successful lifts. Authors: "Insufficient knee flexion in the knee flexion phase (M2) … may be an indirect factor leading to the failed snatch." | INFERRED (quote VERIFIED) |
| same (my arithmetic) | Knee M2, hip M3 | — | A paired t NS at n=10 (t<2.262) for Δ 7.0° and 8.0° implies SD of paired differences >9.8° and >11.2°, i.e. typical error >~7–8° | — | Upper-range noise for competition 2-camera video: measurement error + load + real technique change, which cannot be separated | INFERRED |
| [Gourgoulis et al. 2009, JSCR 23:486](https://pubmed.ncbi.nlm.nih.gov/19197201/) | Lower-limb joints | 1st/2nd pull | "no significant differences … in the angular displacement and velocity data of the lower-limb joints" | 7 international men, success vs fail **at the same load**, 2 cameras at 60 Hz | Direction only; no magnitudes in the abstract; full text not opened | VERIFIED (abstract) |
| [Ho et al. 2011, JSCR 25:2773](https://pubmed.ncbi.nlm.nih.gov/21873899/) | Pelvis, hip, ankle | Start position | Success more likely with **anterior pelvic tilt >17.6°** and **hip angle <89.6°**. Unsuccessful attempts had greater right ankle dorsiflexion (p=0.0228). | **One** novice (1RM 80 kg), **133 attempts** at 75–100 % 1RM, Vicon MX 500 Hz | Within-lifter thresholds from a partition model; the within-lifter SDs are in the full text, which I could not open (LWW 402, ACU 403) | VERIFIED (abstract) |
| [Ang & Kong 2023, Sensors, Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC9919757/) | Barbell | 1st pull / 2nd pull / descent | Within-lifter SD over 3 reps of horizontal displacement: 0.19–2.77 cm; peak-velocity SD 0.02–0.11 m/s | 6 Singapore national-team lifters, 3 snatches at one load, Kinovea | Within-lifter SD (barbell only) | VERIFIED |
| [Sorensen et al. 2022, JSCR (accepted MS)](https://eprints.chi.ac.uk/id/eprint/6114/1/AS_Study%201%20JSCR_revision%201.pdf) | — | — | Reliability of 70 clean variables (ICC/CV), but **no joint angles**: barbell and force only | 8 competitive lifters, 90 % 1RM, 3 sessions | — | VERIFIED (text searched) |

### B2. Classic snatch kinematics with per-phase angles (all SDs are between lifters)

| Source | Joint | Phase | Value | Population | Tag |
|---|---|---|---|---|---|
| [Gourgoulis 2000, Table 2](https://paulogentil.com/pdf/TREINO%20DE%20FORC%CC%A7A/Treinamento%20com%20pesos/G1.pdf) | Knee | End of 1st pull | 143±5.19° | 12 elite Greek men, competition, 2 S-VHS cameras at 60 Hz, DLT, heaviest lift | VERIFIED |
| same | Knee | Decrease during transition (re-bend) | 22.2±4.45° | same | VERIFIED |
| same | Knee / ankle / hip | Max extension, end of 2nd pull | 156±6.65 / 117±8.80 / 177±5.53° | same | VERIFIED |
| [Harbili 2012, JSSM 11:162, Table 3](https://www.jssm.org/tablejssm-11-162.xml/table003.xml) | Knee | Start | Men 70.9±16.0 vs women 68.6±8.4° | 9 men + 9 women, 69 kg, 2010 Worlds Group A, 2 cameras at 50 fields/s, APAS 3D, heaviest lift | VERIFIED |
| same | Ankle / knee / hip | Max, 1st pull | 128.5±6.6 vs 119.6±4.3*; **146.8±14.1 vs 134.7±3.6***; 103.4±6.7 vs 96.6±7.7° | same | VERIFIED |
| same | Knee | End of transition | 134.7±7.9 vs 127.3±6.4°*; text: knee flexed "approximately 12° in men and 7° in women" | same | VERIFIED |
| same | Ankle / knee / hip | Max, 2nd pull | 144.3±4.3 vs 142.6±8.4; **169.7±3.5 vs 165.3±5.1***; 191.8±5.9 vs 193.0±9.7° | same | VERIFIED |
| [Liu 2018, Table 4](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6076374/fullTextXML) (my arithmetic) | Knee re-bend (M1−M2) | Transition | Top-elite 12.1° vs sub-elite 8.3° | 6 + 6 men, 69 kg | INFERRED |
| Elite-sample Hopkins SWC (my arithmetic) | Knee, hip | Pull maxima | 0.2 × between-lifter SD (3.2–8.5°) = **0.6–1.7°** (Gourgoulis 2000; Harbili 2012; Harbili & Alptekin 2014) | elite | INFERRED |
| [Baumann et al. 1988, IJSB 4:68](https://journals.humankinetics.com/view/journals/jab/4/1/article-p68.xml) | — | — | No angle values in the abstract; full text not opened | 1985 Worlds | VERIFIED (abstract) |
| [Hadi, Akkuş, Harbili 2012](https://pubmed.ncbi.nlm.nih.gov/22614145/) | — | 60/80/100 % 1RM | No angle values in the abstract (only barbell and CG differences); full text blocked (LWW 403) | 7 elite Turkish men | VERIFIED (abstract) |
| [Akkuş 2012](https://pubmed.ncbi.nlm.nih.gov/22450233/) | — | — | No angle values in the abstract | 7 gold medallists, 2010 women's Worlds | VERIFIED (abstract) |
| [Campos 2006](https://pubmed.ncbi.nlm.nih.gov/17194258/) | — | — | "No significant differences were found in the analyzed angular parameters" between light and heavy categories; no numbers | 33 junior men | VERIFIED (abstract) |
| [Gourgoulis 2004](https://pubmed.ncbi.nlm.nih.gov/15470309/) | Knee | — | Adolescents vs adults: no difference in most variables; adolescents extended their knees more slowly | 14 adolescents + 9 adults | VERIFIED (abstract) |
| [Korkmaz & Harbili 2016](https://pubmed.ncbi.nlm.nih.gov/26357926/) | — | — | No numbers in the abstract | 10 elite junior women | VERIFIED (abstract) |
| [Kim et al. 2019](https://pubmed.ncbi.nlm.nih.gov/31221023/) | Lower-limb coupling | Transition to take-off | Coordination pattern changes with load (30/65/90 %); no degree values in the abstract | 20 elite men, 8 cameras at 200 Hz | VERIFIED (abstract) |
| [Arauz et al. 2024](https://pubmed.ncbi.nlm.nih.gov/39182264/) | Knee | End of 2nd pull, max bar height | Elite lifters had "significantly more flexed knees" than varsity (p<0.05); no degrees in the abstract | 11 elite + 12 varsity | VERIFIED (abstract) |
| Bartonietz 1996 (SCJ 18:24), Isaka 1996 (JAB 12:508) | — | — | Not found in Europe PMC or open sources; not opened | — | NO EVIDENCE FOUND (not accessed) |

### B3. Snatch measurement error per phase and DoF ([Thiele 2024, Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC11728585/); 12-camera Theia3D vs Vicon; 21 lifters; 131 trials)

| DoF | Whole snatch | 1st pull | Transition | 2nd pull | Turnover | Recovery | Tag |
|---|---|---|---|---|---|---|---|
| Hip flexion | 22.5±7.0 | 27.9±8.8 | 29.9±9.4 | 18.7±8.3 | 19.2±7.4 | 22.0±7.5 | VERIFIED |
| Knee flexion | 8.3±1.9 | 6.4±3.2 | 7.2±3.3 | 7.2±3.2 | 6.0±2.5 | 5.5±2.7 | VERIFIED |
| Ankle dorsiflexion | 10.0±5.2 | 6.5±4.7 | 7.2±3.9 | 8.3±4.0 | 9.5±6.3 | 8.3±5.9 | VERIFIED |
| Hip abduction / knee abduction / ankle inversion (whole) | 6.6±2.9 / 18.2±9.0 / 9.0±5.7 | | | | | | VERIFIED |

All values are RMSD vs the reference, in degrees. They include systematic offset, so they **are not** a measure of rep-to-rep repeatability.

### B4. Within-person trial-to-trial and test–retest variability in proxy tasks

| Source | Joint | Task | Value | Population | Represents | Tag |
|---|---|---|---|---|---|---|
| [Schwartz, Trost, Wervey 2004](http://trama.deib.polimi.it/allegati/Schwartz_2004.pdf) ([PubMed](https://pubmed.ncbi.nlm.nih.gov/15336291/)) | Knee flex/ext | Gait | **σ_trial 1.6°**; σ_therapist 3.4° | 2 able-bodied adults × 12 sessions (4 therapists × 3) × 5 trials, Vicon 512 | Within-person stride-to-stride SD (intrinsic) vs between-session/therapist SD | VERIFIED (p.199–200) |
| same | Hip flex/ext | Gait | σ_ther 3.5°, σ_ther/σ_trial = 3.0, so **σ_trial ≈ 1.2°** | same | as above | VERIFIED / INFERRED (σ_trial) |
| same | Pelvic tilt | Gait | σ_ther 2.8°, ratio 4.0 | same | — | VERIFIED |
| [Malfait et al. 2014, MSSE](https://pubmed.ncbi.nlm.nih.gov/24107791/) | Hip, knee (all planes) | Drop vertical jump, peak angles | **σ_trial 1.1–3.5°**; σ_session 2.7–6.4°; σ_ther-trial ≤2.0° for most | marker-based (LJMU model), 2 therapists, 6 sessions | Within-person trial-to-trial SD of a ballistic lower-limb task | VERIFIED (abstract) |
| [Kanko et al. 2021, J Biomech](https://pubmed.ncbi.nlm.nih.gov/33873117/) | All lower-limb angles | Gait | Inter-trial **2.5°**, inter-session 2.8° (mean of all angles); ratio 1.1. The [preprint](https://www.biorxiv.org/content/biorxiv/early/2020/12/10/2020.06.23.155358.full.pdf) says 2.2° / 2.5° | 8 adults, 8-camera Theia3D, 3 sessions × 5 trials | Markerless repeatability, measurement plus stride variation | VERIFIED (abstract; preprint p.8) |
| [Augustine et al. 2025, PeerJ](https://pmc.ncbi.nlm.nih.gov/articles/PMC11700486/) | All lower-limb angles | Gait | Inter-trial **<2°**, inter-session <3°, session plus clothing change <3.5° | Theia3D, 8 cameras | Markerless repeatability | VERIFIED (abstract) |
| [Vicente-Loren et al. 2026, Sensors, Table 3](https://pmc.ncbi.nlm.nih.gov/articles/PMC13306374/) | Knee / hip (rel. ASIS) / trunk tilt / ankle | Loaded back squat, bottom (P2) | Test–retest SEM **1.98 / 5.15 / 3.35 / 3.13°**; MDC 5.48 / 14.28 / 9.28 / 8.67° | 20 active women, 2D Kinovea manual, 30 fps, deepest of 3 reps, 2 performances 20 min apart | Rep-to-rep plus digitising error | VERIFIED |
| same, Table 3 | Knee / hip / trunk | Standing start (P1) | SEM 2.64 / 2.37 / 2.35°; MDC 7.31 / 6.56 / 6.51° | same | same | VERIFIED |
| same, Table 2 | Knee / hip / trunk | P2, same video re-digitised a week later | SEM 1.90 / 3.65 / 1.46° | same | Digitising error only | VERIFIED |
| same (my arithmetic) | Knee / hip / trunk | P2 | Movement-only part = √(test-retest² − digitising²) ≈ **0.6 / 3.6 / 3.0°** | same | Rough biological rep-to-rep SD; fragile (subtracting two estimates) | INFERRED |
| [Hallman et al. 2026, Gait Posture](https://pubmed.ncbi.nlm.nih.gov/42364529/) | Peak knee flexion/adduction | Squat | **MDC 3.7–10.2°** (gait 1.6–9.9°); squat intersession ICC 0.05–0.96 | 21 female educators, markerless, before/after shift | MDC of a markerless system | VERIFIED (abstract) |
| [Yoma et al. 2025, IJSPT](https://pmc.ncbi.nlm.nih.gov/articles/PMC12317789/) | Trunk, hip, knee, ankle | Single-leg squat | Between-day SEM **3.1±1.3°** (markerless), 4.1±2.2° (marker-based); **hip flexion SEM/RMSD 5–8°** | 19 recreational athletes (Theia3D); 10 for marker-based | Between-day error | VERIFIED (abstract) |
| [Soylu et al. 2025, Life, Table 3](https://pmc.ncbi.nlm.nih.gov/articles/PMC11766738/) | Hip, knee ROM | Overhead squat | Test–retest SEM: Kinovea 5.93–6.89°; Kinect D-Wall 8.25–10.51° | 29 healthy adults | Test–retest | VERIFIED |
| [Lima et al. 2024, J Sports Sci](https://pubmed.ncbi.nlm.nih.gov/39444219/) | Trunk, lower limb | Squat (OpenCap) | RMSE vs markers mean **7.0° (2.9–13.6)**; peak-angle inter-session ICC 0.60–0.92; MDC is in the full text, which I could not open (403) | 19 adults | Validity / reliability | VERIFIED (abstract) |

### B5. Phone, single-camera and markerless accuracy

| Source | Value | Setup | Represents | Tag |
|---|---|---|---|---|
| [Uhlrich et al. 2023, OpenCap, Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC10586693/) | Joint-angle MAE **4.5°** (range 1.7–10.3°) over 18 rotational DoFs; **squat 4.1° (1.8–7.2)**; walk 4.1, sit-to-stand 4.7, drop jump 5.1 | 2 iPhones, HRNet, 10 healthy adults | Error vs marker-based | VERIFIED |
| [Pratapneni et al. 2026, IEEE Access](https://pmc.ncbi.nlm.nih.gov/articles/PMC13229575/) | Sagittal hip/knee/trunk RMSE **2.10–10.98°**; "Errors were predominantly attributable to systematic bias, not random error"; ROM ICC >0.93 | **Single smartphone** (30 Hz, MeTRAbs) vs Theia3D, 51 participants, gait / sit-to-stand / trunk flexion | Monocular accuracy | VERIFIED (abstract) |
| [Iizuka et al. 2026, Front Sports Act Living](https://pmc.ncbi.nlm.nih.gov/articles/PMC13347614/) | Raw bias hip −11.2°, knee −10.6°; RMSE hip 11.6±4.2 → **4.0±2.3°**, knee 10.9±3.3 → **3.9±1.5°** after geometric correction | Fixed monocular webcam, 30 men, bodyweight squat | Monocular accuracy (bias is correctable) | VERIFIED (abstract) |
| [Zhang et al. 2027, Appl Ergon](https://pubmed.ncbi.nlm.nih.gov/42575021/) | Sagittal RMSE **9.9–31.2°**; errors +15–30 % for asymmetric lifts | MediaPipe (monocular) and OpenCap vs Vicon, 20 adults, occupational lifting | Accuracy in lifting | VERIFIED (abstract) |
| [Wade et al. 2023, PLoS One](https://pmc.ncbi.nlm.nih.gov/articles/PMC10635560/) | Occluded-side hip/knee: SD of bias and LoA **double** those of the camera side; camera-side sagittal hip/knee near marker-based error | Single 2D camera, gait, 15 adults | Occlusion penalty | VERIFIED (abstract) |
| [Stefanova et al. 2026, PLOS Digit Health](https://pmc.ncbi.nlm.nih.gov/articles/PMC13446582/) | Mean per-joint angular error **7.7±0.91°** | Single camera vs Xsens IMU, 7 older adults | Accuracy | VERIFIED (abstract) |
| [Baldinger et al. 2025, Sensors](https://pmc.ncbi.nlm.nih.gov/articles/PMC11819822/) | "Significant biases when comparing the joint angles inferred from the different viewing angles" | OpenPose, 4 viewing angles | Viewing angle changes bias | VERIFIED (abstract) |
| No study found | Repeatability of a phone or single camera across reps of a **fast barbell lift** | — | — | NO EVIDENCE FOUND |

### B6. Reliability definitions and thresholds (external anchors)

| Source | Exact statement | Tag |
|---|---|---|
| [Hopkins 2000, Sports Med 30:1](https://pubmed.ncbi.nlm.nih.gov/10907753/) | "the typical (standard) error of measurement: the standard deviation of an individual's repeated measurements". Limits of agreement are "the 95% likely range of change of an individual's measurements between 2 trials". "Reasonable precision for estimates of reliability requires approximately 50 study participants and at least 3 trials." | VERIFIED (abstract; full text closed) |
| [Hopkins, sportsci: reliability calculations](https://www.sportsci.org/resource/stats/relycalc.html) | "divide the standard deviation of the difference score by root2" to get the typical error | VERIFIED |
| [Hopkins, sportsci: precision](https://www.sportsci.org/resource/stats/precision.html) | "the limits of agreement are ±2.77 times the typical error … the standard deviation of the difference score (which is root2 times the typical error) multiplied by 1.96" | VERIFIED |
| [Hopkins 2004, Sportscience 8:1](https://www.sportsci.org/jour/04/wghtests.htm) | Team sports: "an appropriate default for the smallest change in test performance is one-fifth of the between-athlete standard deviation (a standardized or Cohen effect size of 0.20)". Individual sports: "0.3 of the typical variation in an athlete's performance from competition to competition". "The noise in most performance tests is greater than the smallest worthwhile difference." 2018 update: "thresholds for assessing magnitude of the typical error are now half those for a change in the mean". | VERIFIED |
| [Hopkins 2015, sportsci ValidRely](https://www.sportsci.org/2015/ValidRely.htm) | "If the subjects repeated the movement for each trial (the usual scenario), then the typical error represents a combination of variability contributed by the subjects and the rater. You can't partition the error into the two sources" | VERIFIED |
| [Vicente-Loren 2026 methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13306374/) | SEM = SD·√(1−ICC); MDC = SEM·1.96·√2 | VERIFIED |
| [McGinley et al. 2009, Gait Posture 29:360](https://pubmed.ncbi.nlm.nih.gov/19013070/) | Abstract: "Most studies providing estimates of data error reported values (S.D. or S.E.) of less than 5 degrees, with the exception of hip and knee rotation." Highest reliability in sagittal hip and knee. | VERIFIED (abstract) |
| McGinley 2009 as quoted in [Augustine 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11700486/) | "gait kinematic variation <2° might be 'acceptable', variation between 2–5° might be 'reasonable' and >5° degrees may 'raise concern'". The full text was not retrievable: the Salford repository copy is gone and the Wayback Machine has no copy. | SECONDARY |
| CMAS UK & Ireland (Stewart 2023) as quoted in Augustine 2025 | "guideline thresholds of 5° for intra-tester repeatability" | SECONDARY |
| [Hallman 2026](https://pubmed.ncbi.nlm.nih.gov/42364529/) | Uses a "5° MDC threshold" for interpreting squat knee angles | VERIFIED (abstract) |

### B7. Technique faults with degree values

| Fault | Source | Number | Tag |
|---|---|---|---|
| Too little knee re-bend (double knee bend) | [Liu 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9113912/) | Success 10.0° vs fail 5.4° re-bend; knee at M2 7.0° less flexed in fails (NS); authors call it an "indirect factor" | VERIFIED values; INFERRED re-bend |
| same | [Harbili 2012](https://www.jssm.org/hf.php?id=jssm-11-162.xml) | Men about 12°, women about 7°. Key point: women "should be able to execute a deeper and faster knee flexion in the transition phase" | VERIFIED |
| same | [Gourgoulis 2000](https://paulogentil.com/pdf/TREINO%20DE%20FORC%CC%A7A/Treinamento%20com%20pesos/G1.pdf) | Elite: 22.2±4.45° re-bend. Note that the definitions of knee extension differ from Liu and Harbili. | VERIFIED |
| Start posture | [Ho 2011](https://pubmed.ncbi.nlm.nih.gov/21873899/) | Anterior pelvic tilt >17.6°, hip <89.6°; more ankle dorsiflexion at the start in fails (one lifter) | VERIFIED (abstract) |
| Incomplete extension at end of 2nd pull | [Mastalerz 2019](https://johk.pl/wp-content/uploads/2023/03/10078-68-2019-v68-2019-06.pdf) | Knee −4.6°, hip −3.3° in fails at the same load | VERIFIED (digitised) |
| Hips rising first / back-angle change in 1st pull | [Kipp et al. 2012](https://pubmed.ncbi.nlm.nih.gov/21986692/) (clean 85 %); [Nagatani et al. 2026](https://pubmed.ncbi.nlm.nih.gov/41562453/) (power clean) | "greater lift mass was associated with steady trunk position during the first pull"; more upright torso at the power position correlated with performance (r=0.39). **No degrees.** | VERIFIED (abstracts); degrees NO EVIDENCE FOUND |
| Early arm bend | — | No degree threshold. Only descriptive between-lifter elbow values: snatch 183.0±4.9 (1st pull), 183.1±10.3° (2nd pull) ([PAAH](https://paahjournal.com/articles/306/files/65aa78324e3c4.pdf)). Internal focus raised elbow velocity ([Schutts 2017](https://pubmed.ncbi.nlm.nih.gov/28030531/)). | NO EVIDENCE FOUND (threshold) |
| Excessive backward lean at turnover / early drop under | [Nagao et al. 2023](https://pubmed.ncbi.nlm.nih.gov/32772836/); [Schutts 2017](https://pubmed.ncbi.nlm.nih.gov/28030531/) | Fails (frontward drops, same weights, 22 world-class men) had greater backward COM displacement, read as "excessive backward leaning". Internal focus gave larger barbell–cervical–hip angles at max bar height ("squatted under the barbell too soon"). **No degrees in the abstracts.** | VERIFIED (abstracts) |
| Rearward vs forward displacement in drop-under | [Whitehead et al. 2014](https://pubmed.ncbi.nlm.nih.gov/23942165/) | Hip-angle effect sizes 0.17–0.50 between groups; no degrees in the abstract | VERIFIED (abstract) |
| Learning the hang power clean | [Haug et al. 2015](https://pubmed.ncbi.nlm.nih.gov/25559908/) | With learning, "greater double knee bend during the transition phase". The within-athlete mean±SD is in the full text, which I could not open. | VERIFIED (abstract) |

---

## (c) Best-supported answers

### c1. Natural within-lifter rep-to-rep SD per joint (best estimates; all INFERRED from proxies, since there is still no direct snatch measurement)

| Joint / phase | Best estimate | What it rests on |
|---|---|---|
| Knee, pull positions (end of 1st pull, transition, end of 2nd pull) | **~1.5–3°** | Stride-to-stride gait σ 1.6° (Schwartz); drop-jump σ_trial 1.1–3.5° (Malfait); squat test–retest SEM 2.0–2.6° including digitising (Vicente-Loren); two near-max snatches differ by only 0.4–3.4°, NS (Harbili & Alptekin) |
| Hip, pull positions | **~2–4°** | Gait σ ≈1.2°; squat movement-only part ≈3.6° at the bottom; 1.2–3.7° NS between two near-max snatches; hip error is consistently larger than knee in every system (Thiele; Yoma 5–8°) |
| Trunk | **~2.5–3.5°** | Squat trunk-tilt SEM 2.35–3.35°, movement-only part ≈3.0° (Vicente-Loren). No snatch data. |
| Elbow | **No evidence** | No rep-to-rep or test–retest elbow data for lifting found |
| Catch / turnover | **Likely larger than in the pull** | Barbell SEM rises from 1st pull to catch: x 0.4 → 2.3 cm (Sandau) |
| Competition 2-camera video, success vs fail | The SD of paired differences is ≳10° (Liu 2022). This mixes measurement error, load and real technique change. | Upper envelope for poor capture conditions |

### c2. Differences that matter, per joint

| Joint | Within lifter: same or near load (success vs fail, heavier vs heaviest) | Between groups (skill, sex) |
|---|---|---|
| Knee, end of 2nd pull | **+4.6°** in successful lifts (Mastalerz, sig.); +1.3° NS (Liu 2022); +0.4° NS (H&A 2014) | Top-elite vs sub-elite +16.7° (Liu 2018); men vs women +4.4°* (Harbili 2012) |
| Knee re-bend depth (transition) | ≈ **+4.6°** more re-bend in successful lifts (10.0 vs 5.4°, NS; Liu 2022) | Top-elite 12.1 vs sub-elite 8.3°; men ≈12 vs women ≈7° |
| Knee, end of 1st pull | −2.4° NS (Liu 2022); +3.4° NS (H&A) | +17.5° (Liu 2018); +12.1°* (Harbili 2012) |
| Hip, end of 2nd pull | **+3.3°** (Mastalerz, sig.); −8.0° NS (Liu 2022, opposite sign); +1.2° NS (H&A) | +1.0° NS (Liu 2018); −1.2° NS (Harbili 2012) |
| Hip / pelvis, start | Hip <89.6°, pelvic tilt >17.6° (one novice; Ho 2011) | −3.9° NS (Liu 2018) |
| Trunk | Direction only (steadier, more upright, no excessive backward lean) | — |
| Elbow | NO EVIDENCE FOUND | — |

**Reading (INFERRED):** within one lifter, the differences linked to success are about **3–7°**. The 8–17° differences cited in the first pass are **between skill levels**, which is a different question from "this rep vs my best rep".

### c3. External reliability standard to borrow, and what it implies (INFERRED)

1. **Framework: Hopkins (VERIFIED).** Use typical error, i.e. the SD of one lifter's repeated reps (from two trials, SD of the difference ÷ √2). Comparing two single reps, a 95 % detectable change is **±2.77 × TE**, equivalent to MDC95 = 1.96·√2·SEM. Your "noise SD ≈ X/3" rule is slightly stricter than this, so it is defensible. The 0.2 × between-lifter SD rule gives only **0.6–1.7°** in elite samples, so it is useless at phone noise levels. Hopkins himself notes that noise is usually larger than the SWC.
2. **Quality gate: McGinley bands (SECONDARY wording; abstract VERIFIED for "<5°") and the CMAS 5° repeatability limit.** Apply them to the system's own rep-to-rep SD on a consistent lifter: <2° good, 2–5° usable with care, >5° do not report.
3. **Derived thresholds (INFERRED).** Assume natural SD σ_bio ≈ 2.5° at knee/hip in the pull. The smallest single-rep vs single-rep change X you can report at 95 % is 2.77·√(σ_bio² + σ_meas²):

| σ_meas (phone pipeline) | Total rep-to-rep SD | Smallest reportable X |
|---|---|---|
| 0° (perfect sensor) | 2.5° | **6.9°** |
| 2° | 3.2° | 8.9° |
| 3° | 3.9° | 10.8° |
| 5° (realistic single phone at the hip) | 5.6° | 15.5° |

   - Reporting **X = 10°** under the X/3 rule needs an **observed** rep-to-rep SD ≤3.3°, which leaves **σ_meas ≲2.2°**. This can be tested directly by filming repeated reps at one load.
   - The 3–7° within-lifter success/fail differences are **below what a single-rep comparison can resolve**, even with a perfect sensor. Seeing them needs averaging over n reps (σ/√n), e.g. about 4–9 reps.
   - Comparing against the "best rep" adds selection bias (regression to the mean). Compare against the mean of several reference reps instead.
   - Phone and markerless error is largely **systematic bias** (Thiele, Pratapneni, Iizuka). Bias cancels in within-lifter comparisons if camera placement is fixed, so accuracy RMSD (8–22°) overstates the noise that matters here. Repeatability, not accuracy, is the number to measure.

### What changed vs the first pass
- **Corrections:** Liu et al. authorship; hip differences were tested (NS); Mastalerz and Harbili & Alptekin both contain degree values; the Kinovea and Life 15:80 numbers; Thiele's phase pooling covers all lower-limb DoFs.
- **New:** the first within-lifter snatch data, Δ 0.4–4.6° at same or near load. Outcome-linked differences are about 3–7°, not 8–17°.
- **Change of reasoning:** 10° can still be justified, but as a **noise limit** (biological variation plus measurement), not as "the size that matters". Under the X/3 rule it requires measurement SD ≲2–2.5°.
- **Elite SWC:** elite between-lifter SDs are only 3.5–7°, so the Hopkins 0.2·SD SWC is ≈1°.

---

## (d) Remaining gaps
1. **There is still no published within-lifter rep-to-rep SD, ICC, SEM or MDC for snatch joint angles.** The closest primary sources are paywalled:
   - Ho 2011 (133 attempts by one lifter, Vicon): LWW 402, ACU 403.
   - Haug 2015 (within-athlete mean±SD, hang power clean).
   - Kristiansen 2019 (squat, intra-individual angular velocity).
   - Gourgoulis 2009 (success/fail magnitudes).
   - Hadi 2012 (angles at 60/80/100 %; LWW 403).
   - The ISBS knee–trunk coordination paper (commons.nmu.edu 403).
   - The MDPI ECSA national vs college IMU paper (403).
2. **No elbow or trunk rep-to-rep data** for any lifting task.
3. **Phone repeatability for fast lifts is unknown.** All phone and monocular numbers are accuracy (vs a reference) in gait, squats or occupational lifting. None is rep-to-rep repeatability in a snatch or clean.
4. The **McGinley 2009 full text** (exact threshold wording) and **Lima 2024 squat MDCs** could not be opened.
5. **The success/fail evidence is small and inconsistent.** It rests on n = 7–14 lifters, 50–60 Hz competition video, and opposite-sign hip results (Mastalerz vs Liu 2022). Mastalerz's significance claim is statistically fragile.
6. **The proxy biological SDs (gait, drop jump, squat) are an ASSUMPTION for the snatch.** It is plausible that a maximal ballistic lift varies more than walking. The only way to close this is in-house data: about 10 lifters × ≥5 reps at one load, phone plus a reference system, reporting TE per joint per phase.
7. **Bartonietz 1996 and Isaka 1996** were not located in open sources. **Baumann 1988** abstract has no angle values.
