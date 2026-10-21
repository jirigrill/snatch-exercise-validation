# PR D: S7 stage, S8 judge, S9 contract, report

No reuse from open PRs. Thresholds come from spec decisions 1–3 (placeholders until checked against labels.csv).

## labels.csv (first commit)
- `prototype/labels.csv`: `clip, attempt, result, intended_type, reason, fault, note` (one row per true rep, side views only; done, see README). `reason` = the S8 reason expected for a failed lift; `fault` = the technique fault from the filename, for S9 (a fault alone leaves the lift completed); `note` says where the label comes from (`from filename; unchecked` = not checked against the video).
- Replaces filename labels; no filename parsing for labels.

## S7 angles + events
- Written from scratch (v1's `angles.py` + `phases.py` were deleted with v1, see validation-milestone.md item 0; git history has them): a stage that loops over attempts.json, not over overhead runs.
- Reads `pose.npz` (S6) + `frame_times.npy`. Every event carries `filled` from the S6 mask.
- No overhead run → partial record, missing events = null.
- Out: angles.csv (+ filled columns), angles.png, phases.json, phase_sheet.jpg, grabs/; overlay `6_phases.mp4` (**new**).
- Regression test: pin phases.json for the 6 eye-accepted reps + a failed-pull fixture.

## S8 judge (new: `snatch/judge.py`)
- performed_type after the bar peak:
  - muscle: knee drops ≤ 10° below full extension (no rebend)
  - power: rebend, hip above knee at the catch
  - squat: hip at or below knee at the catch
  - unknown: split / unclear (`unsupported_type`), or hip/knee filled at the catch (`low_confidence`)
- intended_type: `--intended` > labels.csv > inferred (= performed); record `intended_source`.
- lift_result = completed / failed / unknown + reason:
  - completed in one overhead run: arms locked (hub over the shoulder, hub–shoulder ≥ 90 % of arm length; elbow ≥ 165° only on frames where the wrist is seen), stand-up (hip above knee, knee ≥ 160°), hold ≥ 1 s (frame times), bar drop < 10 cm, type matches intended
  - reasons: `no_overhead`, `elbow_unlocked`, `no_standup`, `hold_short`, `dropped`, `type_mismatch`, `low_confidence`
  - `type_mismatch` is skipped when intended_source = inferred or performed is unknown
- Out: judgement.json; overlay `7_judgement.mp4`.

## S9 findings (contract only)
`snatch/findings.py` writes `findings.json` with an empty `findings[]` + the bar-path metrics that are cheap now (horizontal travel, peak height). Never changes lift_result.

## Report
- In pipeline.py: `report.json` per attempt (phases, key angles, judgement, findings, clip warnings).
- Final label: completed / failed / unknown. Without S9 rules, completed_clean / completed_with_errors are not shown.
- `overlay.mp4` combines all layers.

## Cleanup (spec decision 7, same PR)
Delete `scripts/run_all.sh`. Update the verify skill, `prototype/README.md` and `docs/results/33-d1-views.md`.

## Tests (only if a clip cannot cover it)
- judge: a table test with one synthetic angle trace per reason + per type.
- Agreement script: run judge on all clips vs labels.csv; besides the %, a confusion matrix of lift_result and of performed type, and the reason for each disagreement. The S8 target is 100 %; report the actual number in the PR.

## Done when
All clips in labels.csv run end-to-end through `pipeline.py`, agreement is reported, and run_all.sh is gone.
