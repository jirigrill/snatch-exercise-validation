# Status: where we are on the way to the verdict

As of 2026-10-09. Issue states are checked against GitHub by `python3 -I tools/check_status.py`. Run it before trusting this page.

## What decides the verdict

The final verdict (#10, written into `../VERDICT.md`) waits on two tests. Both rules were fixed before any result existed.

| Test | Question | Pass rule |
|---|---|---|
| **#11 repeatability prototype** | Does RTMPose-x give joint angles that repeat across reps, on one lifter's iPhone footage? | Locked rule in [#11](https://github.com/jirigrill/snatch-exercise-validation/issues/11#issuecomment-5929883679): per joint, SD bands 3° / 5°; model noise floor ≤ 2° on the standing hold; transition found in ≥ 8 of 9 reps; lowest frame rate whose SD stays within 1° of 240 fps. |
| **Gate 1** (#28, rule in [`research/12-feasibility-grill.md`](research/12-feasibility-grill.md) §5 D3) | Can the app name the mechanical cause of a miss as well as two coaches can? | 2 lifters × ≥ 8 misses, 2 coaches labelling blind. Go needs all four: coverage ≥ 13/16, app–coach agreement ≥ coach–coach agreement, ≥ 80% on misses where both coaches agree, false alarms ≤ 20% of clean made lifts. Otherwise the project ends. |

The prior leans NO-GO (research #1–#8). A gate 1 failure ends the project.

## Where we are

The pipeline works end to end and all spike session results are in. Test 1 is waiting for the full run on all clips (#15). Gate 1 is waiting for the camera view and cause list to be fixed (#25); its two blockers D1 (#23) and D2 (#24) are closed. D1 said side-on stays. D2 said provisional go, with thin evidence.

**Next on the critical path.**
1. #25 fix the view (side-on) and the cause list in `recording-protocol.md`. The issue label still says `blocked`, but #23 and #24 are closed. Check the label.
2. #15 run RTMPose-x on all clips and frame rates against the locked rule.
3. #26 phase detection for squat snatch. The spike session has squat clips now.
4. Record the gate set (#20), build the cause engine (#27), score gate 1 (#28).

## Test 1: repeatability (#11)

| Issue | State | What | Result |
|---|---|---|---|
| #12 | closed | Walking skeleton on one clip | [results/12](results/12-walking-skeleton.md) |
| #13 | closed | Phase-marking check, phase definition v2 frozen | [results/13](results/13-phase-check.md) |
| #14 | closed | Frame-rate ladder and plate tracking | [results/14](results/14-ladder-and-plate.md) |
| #30 | closed | Quick frame-rate estimate (approximation, not the verdict) | [results/30](results/30-fps-estimate.md) |
| #15 | open | RTMPose-x on all clips and rates against the locked rule | not started |
| #16 | open | Add other models (SAM 3D Body, ViTPose, HMR2.0, Apple Vision) | not started |
| #17 | open | Compare models and resolve #11 | not started |
| #11 | open | The test itself | resolved by #17 |

## Gate 1: cause diagnosis (#28)

| Issue | State | What | Result |
|---|---|---|---|
| #22 | closed | Record the spike session (2026-10-07) | [clip-log](clip-log.md) |
| #23 | closed | D1 camera view | no-go for oblique, side-on stays: [results/33](results/33-d1-views.md) |
| #24 | closed | D2 early arm bend | provisional go: [results/34](results/34-d2-arm-bend.md) |
| #25 | open | Fix view and cause list in the protocol | next |
| #26 | open | Phase detection for squat snatch | not started |
| #27 | open | Cause engine | not started |
| #20 | open | Record the made vs missed set (gate 1 data) | not started, protocol in [recording-protocol](recording-protocol.md) |
| #28 | open | Score gate 1 | not started |

Spike session side results: body height 174.5 ± 3 cm in shoes ([results/35](results/35-body-height.md)), knee and wrist fill-in behind the plate ([results/36](results/36-skeleton-fill.md)).

## Side spikes (not on the critical path)

| Issue | State | What |
|---|---|---|
| #31 | open | Phase definition v3 (bar-speed phases), frozen before testing |
| #33 | open | Faster person detector than YOLOX-x |
| #34 | open | Map barpath's 15 faults to our cause list |
| #35 | open | PELT changepoint cross-check for catch and turnover |
| #36 | open | DTW whole-curve distance for reference layer 3 |
| #37 | open | 3D lift of pose output for hidden arm bend |
| #38 | open | Plate detector as fallback for off-axis tracking |
| #19 | open | Related open-source projects |

## Final

| Issue | State | What |
|---|---|---|
| #9 | open | Validation roadmap |
| #10 | open | Final verdict, blocked on #11 and #28 |

Research #1–#8 (market, fit, competitors, graveyard, feasibility, economics, platform, LLM substitution) are closed. Their files are in [`research/`](research/). Their combined lean is NO-GO.

## Known gaps

- `docs/reps.csv` (the hand-checked rep list) is cited by `recording-protocol.md`, `clip-log.md`, `find_reps.py` and `extract_pose.py --reps`, but it is not in the repo and was never committed. Rep ranges exist only as proposals in `prototype/out/reps_proposed.csv`.
