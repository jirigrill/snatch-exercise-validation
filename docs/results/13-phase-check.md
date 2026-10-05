# 13 — Phase-marking check

Ticket: [#13](https://github.com/jirigrill/snatch-exercise-validation/issues/13) (parent [#11](https://github.com/jirigrill/snatch-exercise-validation/issues/11)). Reviewed 2026-10-02.

**Bottom line.** The developer accepted all 24 phase marks (6 reps × 4 events, clips 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg, 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg), after an outside review prepared with `13-reviewer-brief.md`. **Phase definition v2 is final and frozen, unchanged:** see [`14-ladder-and-plate.md` §4](14-ladder-and-plate.md#4-phase-definition-v2-frozen-2026-10-02-before-15) and `prototype/src/snatch/phases.py`. Later tickets must not change it.

## Verdict

| Rep | setup | transition | catch | lockout |
|---|---|---|---|---|
| 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg r1 | accept | accept | accept | accept |
| 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg r1 | accept | accept (maybe late, see below) | accept | accept |
| 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg r1 | accept | accept | accept | accept |
| 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg r2 | accept | accept | accept | accept |
| 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg r1 | accept | accept (maybe late, see below) | accept | accept |
| 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg r2 | accept | accept | accept | accept |

Per-frame verdicts, notes and visibility ticks: `prototype/out/review13/checklist.md`.

## Findings

- **Setup is on time.** At the marked frame the sleeve is still on the floor. It is slightly up at +12 f and clearly up at +24 f (hub +14…+24 px, ~2–3 cm). The hub rises > 3 px within −1…+8 f of the mark, so the mark is at most ~0.03 s early. The first pull (0.53–0.61 s, against 0.42 s for elite lifters in Baumann 1988 / Harbili 2012) is long because these lifters break the bar off the floor slowly, not because of the mark.
- **Transition** is at the end of the knee re-bend: bar at mid/upper thigh, knees under the bar. −0.1 s shows the end of the first pull, +0.1 s the full extension.
- **Catch** is at the bottom of the receiving squat. The lowest hip point is within −19…+31 f of the bar's lowest point after the turnover. All receptions are high (hips above the knees).
- **Lockout:** upright with arms locked. The frames ±0.1 s look the same.

## Known limitation (accepted, not investigated)

On **20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg r1 and 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg r1** the transition may be ~10–20 f (0.04–0.08 s) late. The torso already looks near vertical, peak bar speed follows only 25 / 67 ms later, and the knee dips are shallow (−6°, −4°), so the minimum is flat. Not resolved with a finer frame strip: this is a prototype. If the transition-frame angles in #15 show a large spread, check here first.

## Visibility (input for #15)

Same pattern in all 6 reps (near side, middle-row frame):

| Event | Not visible | Borderline |
|---|---|---|
| setup | wrist, knee, ankle (behind plate / arm) | knee |
| transition | wrist, hip, knee (behind plate) | |
| catch | wrist (inside plate outline) | |
| lockout | wrist (at plate rim) | wrist |

The wrist is never reliably visible. This supports v2's switch from wrist height to the hub. The model scores for the same frames are in `prototype/out/review13/model_visibility.json`, kept out of the checklist on purpose.

## Files

| Path | What |
|---|---|
| `docs/results/13-reviewer-brief.md` | Brief for the outside reviewer |
| `prototype/out/review13/<clip>_rep<k>.jpg` | Contact sheets (event ±0.1 s) |
| `prototype/out/review13/checklist.md` | Verdicts, visibility ticks, reviewer summary |
| `prototype/out/review13/literature_check.md` | Timing vs literature |
| `prototype/scripts/review_phases.py`, `check_phases_literature.py` | Generate the above |
