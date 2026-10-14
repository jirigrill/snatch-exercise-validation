# snatch-exercise-validation

Pipeline v2 spec: `docs/pipeline-v2.html`. Work queue: `.scratch/plan/README.md` (next unchecked item). Code: `prototype/` (run with `uv` from there).

## Workflow
- One checklist item = one session = one PR off main. No subagents, worktrees or pstack skills.
- Stop and ask on spec ambiguity instead of guessing.
- Finish: commit, push, open a PR (not draft) with the check results, publish the evidence to it, then stop. Never merge.

## Checks after each commit to the branch/PR
1. `uv run pytest -q` passes; `uv run pyright` error count ≤ 20.
2. Run the `/verify` skill: `run_clip.sh` on T1 (pipeline v2). Look at every frame sheet (`overlays/*.jpg`) and write one line per sheet on what it shows (e.g. "1_person_sheet: box on the lifter in all 8 frames"); for a `*_worst.jpg`, name each of its frames and what is right or wrong there. Push, then `publish_evidence.sh <evidence root> "<those lines>"` (PR comment + branch `evidence/pr-<n>`, deleted when the PR closes; the local root goes at the next session start, `sweep_evidence.sh`).
3. Milestone items only: T1–T7 vs main, every diff explained. T7 = 0 reps (standup); T5 exit 6 (once S3 exists; add it to `expected_stop` in run_clip.sh).

A FAIL (or a sheet that looks wrong) means fix and rerun, or stop and report it in the PR. Never finish with a failing check.
A Stop hook (`.claude/hooks/require-evidence.sh`) blocks finishing on a PR branch until HEAD is pushed and the PR has ✅ evidence for it (or for an earlier commit with the same `prototype/` and verify scripts).

## Tests
- Clip runs are the main test. Do not write a unit test per stage.
- Add a unit test only for: exit codes and edge cases no test clip covers, the S7 judge rule table, or a bug a clip found (regression).
- When code moves or is deleted, move or delete its tests too.
