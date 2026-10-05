# 12 — Can the app say *why* a snatch failed? Feasibility grill
Status: decisions agreed in a grilling session, nothing built · Date: 2026-10-05 · Builds on: `05-technical-feasibility.md`, `11-technique-markers.md`, `../recording-protocol.md`

## Bottom line

- **Not ruled out, not proven.** Nothing in the current prototype answers the core question yet: 13 light power snatches, one lifter, no misses, no coach labels.
- One cheap, binary experiment decides it: **gate 1** (D3 below). If it fails, the project ends.
- 80% coverage at 80% coach agreement from one phone is **ambitious**. The main threats, in order:
  1. frontal-plane misses, which are always "I don't know";
  2. the only known made/missed discriminators (A10, A11) are hidden by the plate in the side view;
  3. coaches disagreeing with each other;
  4. the causal heuristic may not hold.

## 1. Product decisions

| Topic | Decision |
|---|---|
| Cause | **Mechanical cause** (technique), shown as a symptom → mechanism chain. Root causes (mobility, strength, fear, cue) appear only as hypotheses |
| User | A lifter training without a coach, or between sessions with a coach |
| Input | **One phone, one fixed view**: side-on, or oblique if D1 wins. No second camera, no hardware |
| Exercise | Full snatch from the floor |
| Unit | Patterns across reps carry the strong claim; single reps are weaker |
| Reference | Hybrid: universal physical bands from day one, refined by the lifter's own made reps |
| Causes | **A closed list**; only validated causes ship |
| Co-occurring faults | **The earliest deviation in time = the primary cause**; later deviations are reported as consequences |
| Made lifts | Misses get a cause; made lifts get only "deviations from your best reps", with no cause claim. Gate 1 checks false alarms on clean made lifts. Full diagnosis of made lifts needs its own validation later |
| Uncertainty | The app may answer "fault detected, cause outside what we can diagnose" |
| Promise | "The most likely cause + what to try", not "we'll tell you why" |
| Fallback without causes | **Not acceptable**: no cause, no product |
| No-go | **End the project**; no rescue through extra hardware or a second camera |
| Generalization | Gate 1 uses 1–2 lifters only; the risk that it doesn't carry over to customers is **accepted** and is confirmed only in production |

### Why there is no universal perfect lift

- Femur, torso and arm lengths set the trunk, hip and knee angles in the pull.
- Technique schools disagree (for example on knee re-bend depth). Coaches don't agree on what counts as correct (Furaev), and made-vs-missed differences "were not consistent" (Garhammer).
- Elite lifters succeed with all 4 trajectory types (Shah).
- Coordination is individual even among elite lifters (Ahn & Kipp).

What is universal are **physical bands**:
- the bar stays close (Xnet, X2, Xloop);
- the bar is over the base at the catch (B10);
- full extension comes before the turnover;
- the catch happens below the bar's peak.

## 2. Hard limits (cannot be overcome with one phone)

1. **Frontal plane:** one side lower, bar tilt, knee valgus, uneven grip (E5). Those misses always get "I don't know" and count against coverage.
2. **Root causes** are not in the video.
3. **Cause vs consequence isn't provable.** Faults in the pull co-occur mechanically (05). The earliest-deviation heuristic can only be confirmed by agreement with coaches. There is no published precedent for causal attribution from video.
4. **Disagreement among coaches** caps the measurable accuracy.
5. **No universal template:** beginners without made reps only get the faults that break the physical bands.

## 3. Possibly solvable limits

| Problem | Why it matters | Possible fix |
|---|---|---|
| Hip and knee hidden at the transition | A10, A11 are the only known made/missed discriminators | Oblique view (D1) |
| Wrist hidden throughout the pull | Early arm bend, the most common cue, can't be measured | 2D shoulder-to-hub distance (D2) or oblique view (D1) |
| Detector ~50 min/clip on CPU; body7 licence unverified | Engineering and legal work, not a feasibility question | — |

**Shoulder-to-hub distance (unverified idea).**
- With straight arms the 2D shoulder-to-hub distance equals the projected arm length, and it shouldn't change when the arm swings about the shoulder. The hand lies on the camera axis behind the plate, so it projects near the hub.
- If the distance shrinks before full hip extension, the arms are bending.
- Risks: perspective (the plate is nearer the camera than the shoulder), shoulder keypoint noise, a shrug moving the shoulder keypoint.

**Oblique view.**
- The plate moves sideways off the hand and hip.
- `plate.py` already fits an ellipse. Its axis ratio ≈ cos(viewing angle), so the image can be rectified back to the sagittal plane.
- Rectification is exact only in the plate plane; the body is 20–40 cm deeper.
- Against it so far: off-axis clips 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg and 20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg broke hub tracking on the floor, and Shah fails at ≥ 20°.

## 4. Closed cause list (candidates; final list fixed after D1/D2)

| Cause | Signature | Status |
|---|---|---|
| Shoulders behind the bar at liftoff | A4 | now |
| Hips rise faster than shoulders (1st pull) | A5, A1 | now |
| Bar not brought close in the 1st pull | B2 | now |
| Bar swings away in the 2nd pull | B3, B1, B5 | now |
| Incomplete extension | A10, A11 | more work (D1) |
| Early arm bend | A13 / shoulder-to-hub | more work (D2) |
| Slow or late turnover | D4, B8, C3 | now |
| Catch too high or soft | A14, B8 | now |
| Jump forward/back | E4 | more work |
| Unstable overhead | E3, E2 | now (bar only) |

### Coverage of miss types (estimate before data)

| Miss type | Candidate causes | Measurable now? |
|---|---|---|
| Bar in front | B3, A4, A5; arm bend, short extension | Mostly; the rest waits on D1/D2 |
| Bar behind | Over-pull / backward lean, Xnet toward the lifter (B5), bar outside the base (B10) | Mostly |
| Press-out | Late turnover (D4), catch too high (A14, B8) | Yes; arm lockout (A16) needs more work |
| No turnover | Late or slow turnover | Partly; fear is a root cause |
| Frontal (one side, tilt) | — | **Never** |

## 5. Decision list

| # | Step | Go if | No-go → |
|---|---|---|---|
| **D1** | View spike: one phone, interleaved sets side / 30° / 45°, plus a static metric test (`../recording-protocol.md` § Spike session) | An oblique view shows the transition hip/knee or the wrist **and** the rectified bar path is within ~1 cm on the static test | Side-on stays |
| **D2** | Arm-bend spike (same session as D1) | Shoulder-to-hub distance separates bent and straight arms beyond rep-to-rep spread | Early arm bend leaves the list |
| — | Fix the view and the final cause list in the recording protocol, **before** gate 1 | — | — |
| **D3** | **Gate 1:** 2 lifters × ≥ 8 misses, 2 coaches labelling blind | **≥ 13/16** misses get a cause **and** app–coach agreement ≥ coach–coach agreement **and** ≥ 80% on misses where both coaches agree **and** false alarms on ≤ 20% of made lifts both coaches call clean | **≤ 12/16 → end the project** (the grey zone 11–12 counts as no-go) |
| D4 | Generalization | — (risk accepted) | — |

**Gate 1 is a filter against a clear failure, not proof of success.**
- With 16 misses, an observed 13/16 (81%) is consistent with a true rate of about 57–93%.
- Raising the count to ~30 misses would narrow that to about ±14%. It was rejected: too many heavy misses to collect.

### How agreement is measured

- Each coach labels every lift **blind**: without seeing app output, marker values or the other coach's labels.
- Labels come from the closed cause list, plus `outside_list` and `cant_tell`.
- Coach–coach agreement is the ceiling. Misses where the coaches disagree are reported separately as "ambiguous"; that count is itself a finding.
- **Coverage:** the share of misses where the app names a cause from the list (not "I don't know").
- **False alarm:** the engine outputs a cause on a made lift both coaches label `clean`.
- **Agreement:** the share of misses where the app's primary cause, or the cause it ranks second, matches the coach's cause.
