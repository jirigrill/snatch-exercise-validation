# snatch-exercise-validation

Pipeline v2 spec: `docs/pipeline-v2.html`. Work queue: `.scratch/plan/README.md` (next unchecked item). Code: `prototype/` (run with `uv` from there). GitHub: `jirigrill/snatch-exercise-validation`.

## Workflow
- One checklist item = one session = one PR off main. No pstack skills unless the user's prompt allows them.
- Main agent (Opus) plans, reviews and verifies; it doesn't write the code. Coding goes to subagents with `model: "sonnet"`, `effort: "medium"`, each given a self-contained brief (goal, files it owns, constraints, how to verify). Independent units run as parallel subagents launched in one message, with disjoint files; units that share files run sequentially or with `isolation: "worktree"`. The main agent collects the results, reviews the combined diff against the plan, and sends fixes back to new Sonnet subagents until clean. Trivial edits (a few lines, one file) skip delegation.
- Runs and waits: every pipeline run, the main agent's and every subagent's, goes through `run_clip.sh` (verify skill), never a hand-run `pipeline.py`, so it gets the caches and the checks; each brief says which clips to run through it. Reuse a result only when its key says that what it depends on is unchanged; anything a change touches reruns, and no check is skipped to save time. Work another unit has to wait for stays in that unit's agent instead of a parallel one that polls for it. Wait on a background job's own completion notice, not a process poll.
- Stop and ask on spec ambiguity instead of guessing.
- First pass: make it work on the test clips. No optimisation or generalisation the current item doesn't need; write later improvements into the plan instead.
- PR body: explain in plain English what the change does and how to read everything it produces (each output file, image, colour, field and number), so someone who didn't follow the session can review it without asking. When text alone isn't enough (a new stage, a changed data flow, a new kind of output), add a `/show-me:show-me` page as a screenshot (verify skill, Evidence).
- Finish: commit, push, open a PR (not draft) with the check results, publish the evidence to it, then stop. Never merge unless asked.

## Checks after each commit to the branch/PR
1. `uv run pytest -q` passes; `uv run pyright` 0 errors.
2. `/verify` on T1; when a stage's outputs change or a stage is new, on T1–T8 into one root (cached) and a proof per such stage (the skill says how: run, review every sheet incl. each worst frame, publish the evidence to the PR).
3. Milestone items only: what is checked and how comes from the milestone's spec in `.scratch/plan/` (`validation-milestone.md`: blind marking + eye review of the outputs, bug report, human check). Always one T1–T8 run with `VERIFY_NO_CACHE=1` (fresh; audits the stage cache), every later run cached; then in the PR: what would make this result wrong (one pass, as a forensic reviewer would), and the 3 most urgent open decisions with the case for and against each. T7 = 1 attempt, failed (standup: no_overhead once S8 exists); T8 = 2 attempts; T5 exit 6 (once S2 exists; add it to `expected_stop` in run_clip.sh).

A FAIL (or a sheet that looks wrong) means fix and rerun, or stop and report it in the PR. Never finish with a failing check; the Stop hook (`.claude/hooks/require-evidence.sh`) enforces the evidence.

## Tests
Clip runs are the main test. A unit test exists only for one of these reasons, named first in its docstring:
- R1 an exit code or stop (spec "Stop exit codes")
- R2 the stage-runner contract (hash, skip, stale, atomic outputs)
- R3 an edge case no test clip covers (say which)
- R4 the S8 judge rule table (one case per reason and type)
- R5 a regression a clip found (cite the PR)

Not: the normal path a clip already shows, helper math, inputs the recording protocol rules out, one test per function or stage. Fold variants of one behaviour into one (parametrized) test. When code moves or is deleted, move or delete its tests and apply this rule to them in that PR.
