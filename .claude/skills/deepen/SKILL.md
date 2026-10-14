---
name: deepen
description: Rewrite a task prompt into a deeper (not bigger) one before doing it - what a top professional would add, the rawest material, the methods and tools, and an outside check that shows the result is right. Use when the user types /deepen <prompt>, or asks to make a prompt deeper or more ambitious. Produces the rewrite only; does not do the task.
---

# Deepen a prompt

Input: the prompt after `/deepen` (or the one the user points at). Output: the four answers, then the rewritten prompt in one code block. Do not start the task; the user runs the rewrite.

## Ground it first (a few minutes, read-only)
Look at what the prompt touches before answering, so the answers name real files, not generic advice:
- the spec `docs/pipeline-v2.html` and the plan `.scratch/plan/README.md` (+ its stage files) for what is asked and what is already settled;
- the raw material in this repo: the test clips `vids/test/` (T1–T7, `.claude/skills/verify/features/test-clips.md`), the session logs `~/.claude/projects/-Users-jiri-grill-Developer-snatch-exercise-validation*/*.jsonl`, the PRs and their `/verify evidence` comments (`gh pr list --state all`), `labels.csv` once it exists;
- the outside judges that already exist: `run_clip.sh` + `check_pipeline.py` (verify skill), the worst-frame sheets, pytest, pyright, the Stop hook.

## Answer, one short block each
1. **What a top professional would do here that the prompt does not ask for** (e.g. a baseline before a change, a failure taxonomy, a measured target, a split into reviewable steps).
2. **The rawest material they would start from** instead of what is already digested (clips and per-frame arrays over summaries, logs over memory, the PR history over recollection).
3. **The specific methods and tools** (by name: coverage, an import graph, jq over the logs, a confusion matrix against labels.csv, a before/after diff of the outputs on T1–T7, ...).
4. **What, other than the model or the user, shows the result is right**: a check that can fail, run by a tool (a clip run, an assertion in `check_pipeline.py`, a test that fails when the behaviour breaks, a metric against labels).

## Rewrite
Then rewrite the prompt to ask for exactly that: deeper, not longer. Keep the user's goals and constraints, name sources, method, output and proof per part, keep it within CLAUDE.md (one item = one PR, stop and ask on ambiguity, the checks), and say where the user must decide (e.g. "stop and ask before deleting"). Put any assumption you made (a time window, a threshold) under the code block in one line.
