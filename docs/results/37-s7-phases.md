# 37 — S7 phases (decided 2026-10-21)

Replaces the freeze in [13-phase-check.md](13-phase-check.md) (v2 phase definition, [14-ladder-and-plate.md §4](14-ladder-and-plate.md#4-phase-definition-v2-frozen-2026-10-02-before-15)). Code: `prototype/src/snatch/phases.py` (pure rules), `prototype/src/snatch/stages/phases.py` (stage). Plan: `.scratch/plan/D-judge.md`.

## Kept from v2 (#13, accepted on 6 side-on reps)
- The bar is the near plate's **hub**, not the wrist (the hands sit inside the plate outline).
- Overhead = hub above the nose for >= 0.25 s. Now a **marker** (`bar_overhead`), the longest run in the attempt, not a rep counter: S7 loops over `attempts.json`.
- **liftoff** (v2 "setup"): last frame before the overhead run with the hub below the hip, then back to the start of the continuous rise (hub faster than 50 px/s).
- **deepest_rebend** (v2.1 "transition"): knee minimum with prominence >= 3 deg measured on the whole liftoff to full-extension segment; only minima after the hub passes the knee.
- **full_extension** (v2 peak knee extension): highest knee angle before the hub passes the nose.
- **standing** (v2 "lockout"): first frame after the catch with the knee within 5 deg of its maximum while overhead.
- Thresholds unchanged (0.25 s, 50 px/s, 3 deg, 5 deg, 0.1 s smoothing); now named constants in `snatch/phases.py` and in `phases.json` `params`.

## New
- **Names, everywhere** (code, json, sheets, overlay, S8 rules): phases `starting_position, first_pull, transition, second_pull, turnover, catch, recovery, hold`; borders `liftoff, first_knee_max, deepest_rebend, full_extension, bar_peak, bar_lowest, standing`.
- **first_knee_max**: highest knee angle between liftoff and deepest_rebend (null without a re-bend).
- **bar_peak**: first peak of hub height after full_extension with prominence >= 2 cm; no dip (muscle snatch) = the highest hub in the range.
- **bar_lowest**: the catch bottom. `knee_low` = lowest knee angle in [bar_peak, bar_overhead.end); `upper` = first frame >= knee_low with the knee within 5 deg of its maximum over [knee_low, bar_overhead.end); bar_lowest = lowest hub in [bar_peak, upper] (= bar_peak when there is no dip); null without bar_overhead. Decided 2026-10-21: the earlier rule (lowest hub up to bar_overhead.end) also caught the bar being lowered at the end of the hold (T1: f1095 instead of the catch bottom ~f590), and standing followed it.
- **Null borders**: a border S7 cannot find is null; a phase with a null border has a null start or end. No bar_overhead (failed pull) = bar_lowest and standing null, a partial record.
- Every border carries `frame`, `t`, `filled` (S6 mask at the near hip, knee or ankle) and `hidden`.
- All timing through the frame times `t` (seconds), never frames x fps.
- Same rules for every snatch type; S8 classifies.

## Outputs
`angles.csv` (hip, knee, elbow, S6 filled mask per joint, `wrist_hidden`, hub_y), `angles.png`, `phases.json`, `grabs/a<k>_<border>.jpg`, `phase_sheet.jpg`, `overlays/7_phases.mp4`.

## Checked against true frames (2026-10-21)
Clips T1, T2, T3, T6, T7, T8 (7 attempts, 49 borders). Two blind markers (Opus, Sonnet agents) marked every border from raw frame strips (`mark_strips.py`), no pipeline output. Where they disagreed beyond tolerance, or agreed and S7 was off, the developer picked the frame on a review page (`s7_marks_review.py`): 31 borders; the other 18 = the markers' mean, not seen by the developer. Reference frames: `prototype/tests/data/s7_reference.json`; `check_pipeline.py` checks every clip run against it (a border in `passing` that stops agreeing = FAIL). Tolerance (s): liftoff, bar_peak, bar_lowest 0.03; first_knee_max, deepest_rebend, full_extension 0.05; standing 0.10.

**The reference is not ground truth** and not precise enough to judge timing at these tolerances:
- Anchoring: the page outlined every candidate's frame as a letter, S7's among them (which letter was S7 was hidden, its frame was not). 26 of the developer's 28 frame picks are exactly a candidate's frame, 9 exactly S7's (liftoff T1, T2, T6, T7; standing T1, T2, T6, T8 a2; bar_lowest T2).
- Plateaus: bar_peak, bar_lowest and full_extension span 20-30 frames (bar level, knee near straight), wider than a 0.03 s tolerance (7 frames at 240 fps).
- Definitions: standing on T1 is f722-732 for both markers, f853 for the developer and S7 (0.5 s): a reading of "legs straight".
- Repeatability: the same frames marked twice (T1 = T8 a1) differ by up to 0.18 s for a marker; the developer marked them once.
- The developer is not a coach; the re-bend borders (knee behind the plate) are the hardest.

So the table below is agreement with that reference, not accuracy: a timing fail does not prove S7 is off, a timing pass (liftoff, standing: anchored) does not prove it right. **What holds regardless:** S7 gives no first_knee_max / deepest_rebend where every judge saw a re-bend (the 3 deg rule does not fire on these clips), and borders that do not exist on the standup T7. For S8 these gaps do not change a result (T7 has no overhead, failed either way; S8 reads bar_overhead, bar_peak and the angles around bar_lowest / full_extension, plateaus where a 0.05 s shift barely changes the value); they matter for S9's technique faults. A reference precise enough for timing is a validation-milestone task (unanchored marking, ranges for plateau borders, a repeat marking, a coach on the re-bend).

**Agreement with the reference: 28 of 49** (markers: Opus 27, Sonnet 21; details in the PR's S7 proof):

| border | pass | how the fails fail |
|---|---|---|
| liftoff | 5/7 | T3, T8 a2 0.04 s early |
| first_knee_max | 1/7 | null where a true one exists (the rule needs a re-bend; T1 has a knee max without one) |
| deepest_rebend | 4/7 | null on T3, T6, T8 a2: dips under 3 deg after the hub passes the knee |
| full_extension | 2/7 | T1, T2, T6 0.07-0.08 s early; T7 (standup) found, true none |
| bar_peak | 6/7 | T7 found, true none |
| bar_lowest | 3/7 | early on T1, T6, T8 a2 (0.05-0.13 s) |
| standing | 7/7 | |

Not tuned in this PR (the rules were decided before the marking). Candidate rule changes for a later item: first_knee_max without a re-bend; full_extension later (the knee keeps extending after the hub passes the nose?); bar_lowest bound; no pull borders past liftoff for a no-overhead attempt that never extends (T7).

Marker consistency: T1 and T8 a1 are the same frames, marked twice: median difference Opus 0.038 s, Sonnet 0.017 s (S7 0). The markers' own files were deleted once by `sweep_evidence.sh` (a dir under `.scratch/verify/` without a run log) and restored from their reports; they now live in `.scratch/s7-marks/` (gitignored, local).
