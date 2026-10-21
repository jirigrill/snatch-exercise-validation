# Validation milestone: validate every stage on T1–T8

Goal: find out how correct the outputs of every stage (S-1, S0, S1–S8, side, C3, exits and stops), on T1–T8, measured to the pixel and checked by a human. No pipeline code changes: the output is a bug report with a suggested fix per bug. Settled in a grilling session, 2026-10-16.

Order: item 0 (v1 removal) → V1 → V2 → V3, one PR each (V3 may be plan edits only).

**Runs once, after Milestone D (merged with the old Milestones B and C, 2026-10-21).** Item 0 is done (#68). Scope: all of T1–T8; if D missed the goal (S8 below 100 % agreement with labels.csv), start with the clips and stages D's per-disagreement notes name. Answers: would making the weak stages precise reach the goal? The stages table below lists the front stages; S5–S8 are checked the same way against the references. Frame counts are the full-scope upper bound. Open S6 items: T3 fill unmeasured, T5 airborne shank/thigh +4–6 %.

## Item 0: remove v1 (own PR, before V1)
- Delete: `scripts/analyze.py`, `compare_phases.py`, `extract_person.py`, `extract_pose.py`, `find_reps.py`, `overlay_video.py`, `track_plate.py`, `run_all.sh`; `reps.find_lifts`, `find_pose_lifts`, `find_pose_holds`; `spread.py`, `phases.py`, `angles.py`; all of `scripts/studies/` and `src/snatch/studies/` (conclusions live in the plan and PRs; git keeps them); their tests (`test_phases.py`, `test_spread.py`, `test_angles.py`, the v1 parts of `test_reps.py`).
- `HALPE26` moves from `angles.py` to `pose.py` (next to `SIDE_OF`); update its importers (calibrate, pose, overlay, skeleton).
- The T6 item (v1 2 reps vs v2 1) is dropped: V2's blind marking settles T6's true count.
- Check: pytest, pyright, `/verify` on T1 with no output change (stage keys may change; content must not).

## Runs
- One `VERIFY_NO_CACHE=1` run of T1–T8 into one evidence root (fresh; audits the stage cache). An audit FAIL is a finding, not a stop.
- Every later run in V1–V3 uses the cache. All runs go through `run_clip.sh`.
- Expected: T1–T3, T6 1 attempt; T4 stops `2 side`; T5 stops `6 S2` (+ calibration); T7 1 attempt (standup, failed); T8 2 attempts.

## What is validated
| Stage | Checked against the references |
|---|---|
| S-1 | frame times, fps vs ffprobe |
| S0, side | exits/stops as expected (T4, T5), facing vs filename |
| S1 | box contains the whole lifter |
| S2 | plate ellipse on the rim, hub px, px_per_m vs the plate diameter, track gaps |
| S3 | attempt count, start/end frames, key frames (liftoff, peak, back on floor), `not_a_pull` |
| S4 | near-side shoulder, elbow, wrist, hip, knee, ankle, heel, toe (px); facing |
| C3 (T5) | skeleton lengths vs lengths measured on frames with the leg visible |

## Review A: blind marking
- Two markers, Opus and Sonnet, each on its own; neither sees pipeline output (no overlays, no numbers).
- Marking tool (verify skill, built in V1): zoom in steps (full frame → 4× crop with labelled grid → 16× crop around the point); the agent answers in grid coordinates at each step.
- Frames, fixed before marking starts:
  - every 4th frame from liftoff to catch;
  - every 12th frame for the rest of each attempt window;
  - every 48th frame outside the attempts;
  - every S3 key frame and every worst frame of every stage;
  - frames Review B flags (the only later addition).
  - T5: `calibration_overlay` worst frames, 20 frames from the bent-leg frames (where C3 rebuilds the knee), every 48th frame.
- About 100–130 frames per clip, ~900 total.

## Review B: by eye
- A third agent (Opus); sees neither the marks nor pipeline numbers, only drawings.
- Contact sheets of every 4th frame with the overlay (16 frames per image, ~2,100 frames total), plus every existing sheet and worst-frame image.
- Per frame: correct / wrong + what. Flagged frames are added to Review A.

## When a difference is a bug
- Points: pipeline farther from the markers' mean than k × the markers' spread on that point, and > 3 px. k set from the V1 pilot.
- Frames (attempt start/end, key frames): off by more than ±2 frames.
- A frame where the two markers disagree beyond their usual spread is unclear: it goes to the human, not into the bug count.
- A finding raised by both reviews is marked as such.

## Human check (HITL)
- A `/show-me:show-me` page per clip: each finding as a crop with the pipeline point and markers A and B in different colours, the error in px, Review B's verdict; plus a random 10 % of agreements as a check on the agents.
- Human verdicts in `.scratch/plan/validation-report.md`: `confirmed / rejected / unsure` + note per finding.
- Only `confirmed` becomes a plan item in `README.md`, linking its finding and the suggested fix.

## V1: marking tool + pilot (PR)
- Build the marking tool in the verify skill.
- Pilot on T1 (or the first in-scope clip): both markers mark the same frame set twice; measure spread per point (px), cost per frame (time, tokens).
- Gate: spread > 10 px on any point (≈ 2.4 cm at 240 fps) → stop and ask (better tool, or a human marks that point).
- PR gives the measured precision, k, and the cost estimate for V2. The user confirms the cost before V2.

## V2: full validation (PR)
- Fresh run, Reviews A and B on the in-scope clips (T1–T8 at most), the comparison, `validation-report.md` with findings and suggested fixes, the show-me pages.
- PR also carries CLAUDE.md check 3: what would make this result wrong (forensic pass), and the 3 most urgent open decisions with the case for and against.

## V3: human check
- The human records verdicts in the report; confirmed bugs become plan items.
