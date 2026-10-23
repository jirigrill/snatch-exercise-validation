# PR D: S7 stage, S8 judge, S9 contract, report

No reuse from open PRs. Thresholds come from spec decisions 1–3 (placeholders until checked against labels.csv).

## labels.csv (first commit)
- `prototype/labels.csv`: `clip, attempt, result, intended_type, reason, fault, note` (one row per true rep, side views only; done, see README). `reason` = the S8 reason expected for a failed lift; `fault` = the technique fault from the filename, for S9 (a fault alone leaves the lift completed); `note` says where the label comes from (`from filename; unchecked` = not checked against the video).
- Replaces filename labels; no filename parsing for labels.

## S7 angles + phases (decided 2026-10-21)
Written from scratch (v1's `angles.py` + `phases.py` in git history, 6469c5b, reference only). Loops over attempts.json, not over overhead runs. Reads `pose.npz` (S6), `plate.npz` (hub), `frame_times.npy`, `facing.json`. All timing through frame times, never × fps.

**Angles.** Smooth keypoints (fill gaps, Savitzky-Golay 0.1 s, order 2). Near-side hip, knee, elbow per frame. `angles.csv`: a filled column per joint (S6 mask) + `wrist_hidden` (wrist inside the plate outline + 10 %, S6's test). Elbow computed on every frame; S8 uses it only where `wrist_hidden` is false. No wrist rebuild (later item).

**Phases** (literature: Enoka 1979, Baumann 1988, Gourgoulis 2000, Harbili 2012; matches thetraininggeek "5 phases" with catch split out). These names everywhere: code, phases.json, sheets, overlay, S8 rules. Same rules for every snatch type.

| Phase | start → end | Border rule |
|---|---|---|
| starting_position | attempt start → liftoff | liftoff: v2 setup rule (last hub-below-hip frame before bar_overhead, back to the start of the rise > 50 px/s) |
| first_pull | liftoff → first knee max | first knee max: highest knee angle between liftoff and the deepest re-bend (**new**) |
| transition | first knee max → deepest re-bend | deepest re-bend: v2.1 transition rule (prominence ≥ 3° on the whole liftoff → full-extension segment, after the hub passes the knees) |
| second_pull | deepest re-bend → full extension | full extension: v2 peak knee extension (highest knee before the hub passes the nose) |
| turnover | full extension → bar peak | bar peak: first hub high point after full extension; no dip (muscle) → highest hub before standing (**new**) |
| catch | bar peak → bar lowest | bar lowest: lowest hub between bar peak and the legs straight again (first frame after the knee's low with knee within 5° of its max while overhead); = bar peak if no dip (**new**; the bound is not `standing`, which depends on it, nor the overhead end, which catches the bar being lowered) |
| recovery | bar lowest → standing | standing: v2 lockout rule (first frame after bar lowest with knee within 5° of its max while overhead). Arms locked = S8 |
| hold | standing → bar_overhead end | |

- Marker `bar_overhead` (start, end): hub above the nose ≥ 0.25 s, longest run in the attempt. Not a phase.
- A border S7 can't find → null (no bar_overhead = failed pull: partial record). Every border frame carries `filled`.
- Replaces the #13 freeze: write `docs/results/37-s7-phases.md` (what's kept from v2, what's new, decided 2026-10-21); a pointer line in `13-phase-check.md`.

**Out:** angles.csv, angles.png, phases.json (one record per attempt), phase_sheet.jpg, grabs/, overlay `7_phases.mp4`.

**Correctness: blind marking + HITL** (moves the marking tool from validation-milestone V1 forward; the milestone reuses these marks for S7).
- Clips: T1, T2 (squat), T3 + T7 (failed: borders that exist), T6 (60 fps; also vs the #13 marks on 20261001_3), T8 (2 attempts).
- Two markers (Opus, Sonnet), each alone, no pipeline output: plain border definitions, every-4th-frame strips across the attempt, then every-frame strips around their pick.
- To the human (show-me page, frames side by side, candidates labelled): markers disagree beyond tolerance, or markers agree and S7 is off beyond tolerance. Human verdict = true frame.
- Tolerance (s): liftoff, bar peak, bar lowest ±0.03; first knee max, deepest re-bend, full extension ±0.05; standing ±0.10.
- PR reports per border: S7 − true (s), pass/fail vs tolerance.
- The confirmed frames are saved as the reference; regression test (R5) checks phases.json against them within tolerance.

## S8 judge (new: `snatch/judge.py`; gaps decided 2026-10-23)
Scope: every attempt (completed or failed); result + type only. Technique is S9 (a fault that still gets the bar up = completed).
- performed_type (S7 names):
  - muscle: knee drops ≤ 10° below its `full_extension` value over `bar_peak` → `standing` (no rebend)
  - power: rebend, hip above knee at the `bar_lowest` frame
  - squat: hip at or below knee at the `bar_lowest` frame
  - unknown: split / unclear (`unsupported_type`), hip/knee filled at `bar_lowest` (`low_confidence`), or no `bar_peak` / no `bar_overhead` (failed pull: nothing caught)
- intended_type: `--intended` > labels.csv > inferred (= performed); record `intended_source`.
- lift_result = completed / failed / unknown + reason. Checks, in order (first fail = `reason`):

  | # | reason | result | fails when |
  |---|---|---|---|
  | 1 | `no_overhead` | failed | no S7 `bar_overhead` |
  | 2 | `elbow_unlocked` | failed | in the hold: elbow < 165° (only frames with the wrist seen), or hub–shoulder horizontal offset > 15 % of arm length, or hub–shoulder distance < 90 % of arm length |
  | 3 | `no_standup` | failed | no S7 `standing` (hip above knee, knee ≥ 160°) |
  | 4 | `hold_short` | failed | `standing` → `bar_overhead` end < 1 s (frame times) |
  | 5 | `dropped` | failed | hub max − min height over `standing` → `bar_overhead` end ≥ 10 cm (per-frame px/m from plate.npz) |
  | 6 | `type_mismatch` | failed | performed ≠ intended; skipped when intended_source = inferred or performed unknown |
  | 7 | `low_confidence` | unknown | no check failed, but one is unsure: its frames rely on a filled/hidden hip or knee, or the plate is lost in the hold |
  - Each check is pass / fail / unsure. A clear fail on reliable frames wins over any unsure (e.g. elbow bent on seen frames + knee filled → `failed: elbow_unlocked`). completed = every check passes.
  - Arm length: skeleton px × scale.json factor; without S5 scale, the median shoulder–wrist distance over the hold on frames with the wrist seen.
- Out: `judgement.json` per attempt {performed_type, intended_type, intended_source, lift_result, reason, evidence_frames, checks: {name: {value, threshold, unit, pass|fail|unsure, frames: [start, end]}}}; evidence_frames = the deciding check's frames. Overlay `8_judgement.mp4`. `judgement_sheet.jpg`: a row per attempt, frames at `bar_lowest`, `standing`, mid-hold, `bar_overhead` end, each with the verdict + check values; the worst frame per check is marked.
- Proof (verify): T1–T8 cached into one root, look at every judgement sheet, `sheets.md`.

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
- Agreement script: run judge on T1–T8 vs labels.csv; besides the %, a confusion matrix of lift_result and of performed type, and the cause of each disagreement. No agreement target (labels.csv holds the intended lift, not what was performed; thresholds are not fitted): every miss is named as an upstream stage error (S4–S7, plan item), a wrong label (fix labels.csv) or the lifter performing other than intended (expected, reported).

## Done when
All clips in labels.csv run end-to-end through `pipeline.py`, agreement is reported, and run_all.sh is gone.
