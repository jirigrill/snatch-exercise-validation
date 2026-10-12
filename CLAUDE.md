# snatch-exercise-validation

Pipeline v2 spec: `docs/pipeline-v2.html`. Work queue: `.scratch/plan/README.md` (next unchecked item). Code: `prototype/` (run with `uv` from there).

## Workflow
- One checklist item = one session = one PR off main. No subagents, worktrees or pstack skills.
- Stop and ask on spec ambiguity instead of guessing.
- Finish: commit, push, open a PR (not draft) with the check results and the evidence path, then stop. Never merge.

## Checks before commit
1. `uv run pytest -q` passes; `uv run pyright` error count ≤ 56.
2. `/verify` skill: `run_clip.sh` on T1. Look at the output images.
3. Milestone items only: T1–T7 vs main, every diff explained. T7 = XFAIL exit 4; T5 exit 6.

## Tests
- Clip runs are the main test. Do not write a unit test per stage.
- Add a unit test only for: exit codes and edge cases no test clip covers, the S7 judge rule table, or a bug a clip found (regression).
- When code moves or is deleted, move or delete its tests too.
