# Code review skill

Source: "How the Claude Code team does code review" (claude.dev blog, 2026-10-15). Agreed 2026-10-21.

Problem: the agent that plans a change also reviews its diff (CLAUDE.md, Workflow), and that review leaves nothing on the PR. GitHub only gets the output evidence from /verify. No second reviewer, no CI, no branch protection (free private repo). #75 merged 3 min after it opened.

## Scope
- New project skill `.claude/skills/review/`, separate from /verify. Review reads the diff and runs nothing; /verify proves outputs (clips, sheets, proofs, image review in `review.md` stay there).
- Order per commit: code → review → fixes → verify → publish. Review goes first so its fixes don't make the clips rerun.
- Review posts findings, never an approval. The human still merges.
- Out of scope: the validation milestone's blind markers (`validation-milestone.md`), CI, a PR template (CLAUDE.md already sets the PR body), parallel hunters + voting, a reviewer eval set (see Later).

## Reviewer
- Input: `git diff main...HEAD` plus the plan item it claims to do (the PR's intent), the spec (`docs/pipeline-v2.html` + the stage md) and CLAUDE.md.
- Questions: does the change do what the item says, does it fit the spec and the stage contract, what does it break. On a bug fix: is it the root cause, not a patch over the symptom.
- Runs as a fresh-context Opus subagent (it didn't plan or write the code).
- Verifier pass: a second fresh subagent re-checks each finding against the code and drops any without file:line evidence (a guess from a name doesn't count), plus style- or cleanup-only findings.
- Fixes go to Sonnet subagents as usual (CLAUDE.md, Workflow).

## What "wrong" means here (failure list)
- A stage silently outputs wrong angles / phases / judgements (no exit, plausible numbers).
- The stage cache serves a stale result (key misses an input or the code it depends on).
- A check passes trivially (threshold never reachable, empty input passes, wrong field compared).
- A test breaks the CLAUDE.md test rule (no R1–R5 reason, or one the clips already cover).
- Spec and code disagree (exit codes, stage order, output fields).
- Skip: `.scratch/`, `docs/results/`.

## Output
- Summary starts with a count ("2 Important, 1 Nit, 0 Pre-existing") and says plainly when there's nothing to fix.
- Tags: **Important** (blocks), **Nit** (max 3, never blocks), **Pre-existing** (bug the PR didn't add; doesn't block, goes in the plan if it matters).
- A finding names its bug class, so the fix covers every instance, not just the one cited.
- One PR comment per reviewed HEAD, header `## /review: <sha> — N findings`, so the Stop hook can find it.

## Answers and rounds
- Every finding gets an answer in that comment: fixed (commit) / wrong / intentional / didn't matter, with a reason. Keep the counts per category; that's the noise rate to look at later.
- At most 3 review rounds per PR. After that only the new diff gets reviewed, and findings already posted aren't repeated. Still not clean after 3 → stop and ask whether the approach is right.
- A finding that comes back across PRs becomes a rule (CLAUDE.md, a `check_pipeline.py` check, a pyright setting) instead of being flagged again.

## Depth by risk
- Only `.scratch/` or `docs/` touched: no review (checks only).
- Stage code: normal review.
- `check_pipeline.py`, `stage_cache.py`, the other verify scripts, `.claude/hooks/`, the S8 judge: deep review plus a "human should read" line at the top of the comment (a bug there makes all evidence lie).

## Stop hook (`require-evidence.sh`)
- Also requires a `/review` comment for HEAD (or a commit with the same code, as for evidence) with every Important finding answered.
- Also requires the pytest + pyright results to be recorded (exit 0 and 0 errors).
- Keep the stop-on-retry fallback (the session must never get stuck).

## CLAUDE.md
- Workflow: name review, then verify, in that order.
- PR body: "what the checks would miss" on every PR, not only milestones.

## Done
- The skill run on its own PR and on one past stage PR (#74), findings posted to each.
- The hook blocks a stop without the review comment and lets it through with one.

## Later (not this item)
- Parallel hunters + voting, if one reviewer turns out noisy (many "wrong" / "didn't matter" answers) or misses bugs.
- Eval set: PRs that caused regressions (R5 tests cite them), rerun whenever the skill or the model changes; keep a change only if the score goes up.
- Track rounds-to-pass per PR.
