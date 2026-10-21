# Code review skill

Source: "How the Claude Code team does code review" (claude.dev blog, 2026-10-15). Agreed 2026-10-21.

Problem: the agent that plans a change also reviews its diff (CLAUDE.md, Workflow), and that review leaves nothing on the PR. GitHub only gets the output evidence from /verify. No second reviewer, no CI, no branch protection (free private repo). #75 merged 3 min after it opened.

## Scope
- New project skill `.claude/skills/review/`, separate from /verify. Review reads the diff and runs nothing; /verify proves outputs (clips, sheets, proofs, image review in `review.md` stay there).
- Review goes before /verify, not in parallel, so its fixes don't make the clips rerun (see Flow).
- Review posts findings, never an approval. The human still merges.
- Out of scope: the validation milestone's blind markers (`validation-milestone.md`), CI, a PR template (CLAUDE.md already sets the PR body), parallel hunters + voting, a reviewer eval set (see Later).

## Roles
| Role | Model | Context |
|---|---|---|
| Main agent (the session) | Opus | Full session: plan, briefs, subagent reports |
| Developers | Sonnet | Only its brief |
| Reviewer | Opus | Clean: diff, plan item, spec section, CLAUDE.md |
| Finding checker | Sonnet | Clean: the findings and the code they cite |

- The main agent knows the plan and the briefs, so it can't be the independent reviewer. It does only a light check (each unit did its brief; the developers' pytest + pyright are green, not rerun or recorded here: see Overlap with /verify) and the triage: sends Important findings to new Sonnet subagents and writes the answers. It never writes findings.
- The reviewer is Opus for every review, full and diff-only: Sonnet wrote the code, and the same model shares its blind spots.

## Flow
1. Developers finish. With parallel units, review waits until all are done and sees the combined diff, not one unit at a time.
2. Main agent: light check.
3. /review → fixes → diff-only review of the fixes; at most 3 find-and-fix rounds per commit. Still not clean after 3 → stop and ask whether the approach is right.
4. Commit.
5. /verify. FAIL → fix → diff-only review of the fix → /verify again.
6. Push, open the PR.
7. Post the `/review` comment and the `/verify` evidence comment. Review runs on the local diff before the PR exists; its comment is posted once the PR is open.
8. Stop hook checks both.
9. The human merges.

## Which commits get reviewed
| Commit | Review |
|---|---|
| First code commit (before the first push) | Full: `git diff main...HEAD` |
| Later code commit | Diff-only: that commit's diff; the reviewer sees the earlier findings and doesn't repeat them |
| Later commit that changes the approach, rewrites a large part, or touches the deep-review paths (Depth by risk) | Full again |
| Trivial fix (a few lines, one file; same rule as CLAUDE.md's trivial edits) | None |
| Only `.scratch/` or `docs/` | None |

## Reviewer
- Input: the diff, the plan item it claims to do (the PR's intent), the spec section for the stages the diff touches (not the whole `docs/pipeline-v2.html`) plus that stage's md, and CLAUDE.md. Not the briefs or the session history, so it isn't anchored on how the code was meant to work.
- Questions: does the change do what the item says, does it fit the spec and the stage contract, what does it break. On a bug fix: is it the root cause, not a patch over the symptom.
- Told what the checks already enforce (pytest, pyright, `check_pipeline.py`: exit codes, stage order, outputs non-empty, content thresholds), so it doesn't repeat them and looks for what they miss: silent wrong values, cache-key gaps, checks that pass trivially. A finding a check already catches is dropped.
- Finding checker: re-reads the code for each finding and drops any without file:line evidence (a guess from a name doesn't count), plus style- or cleanup-only findings. Skipped when there are no findings. (Not /verify; it runs nothing.)

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
- One PR comment per reviewed commit, header `## /review: <sha> — N findings`, so the Stop hook can find it.

## Answers
- Every finding gets an answer in that comment: fixed (commit) / wrong / intentional / didn't matter, with a reason. Keep the counts per category; that's the noise rate to look at later.
- A finding that comes back across PRs becomes a rule (CLAUDE.md, a `check_pipeline.py` check, a pyright setting) instead of being flagged again.

## Depth by risk
- Stage code: normal review.
- `check_pipeline.py`, `stage_cache.py`, the other verify scripts, `.claude/hooks/`, the S8 judge: deep review plus a "human should read" line at the top of the comment (a bug there makes all evidence lie).

## Stop hook (`require-evidence.sh`)
- Also requires a `/review` comment for HEAD with every Important finding answered. It accepts the last `/review` comment if every commit after it is a trivial fix or docs/plan only (the rows without review above).
- Also requires the pytest + pyright results (exit 0 and 0 errors), read from the /verify evidence comment.
- Keep the stop-on-retry fallback (the session must never get stuck).

## Overlap with /verify
- pytest + pyright: run by /verify only (already per commit, `SKILL.md` Fast gate). /verify records the results in its evidence comment (a change to `publish_evidence.sh`/`render_comment.py`); the Stop hook reads them there. /review neither runs nor records them.
- Spec vs code: `check_pipeline.py` checks it at runtime; the reviewer is told so (Reviewer) and doesn't repeat it.
- Naming: /verify's `review.md` (the image review) and "the reviewer" in `features/stage-guide.md` (the human reading the comment) clash with /review. This item decides whether to rename them (e.g. `review.md` → `sheets.md`) and updates /verify if so.

## CLAUDE.md
- Workflow: "Main agent (Opus) plans, reviews and verifies" → it plans, does the light check, triages review findings and verifies; the review itself is /review's clean-context reviewer. Name /review, then /verify, in that order.
- PR body: "what the checks would miss" on every PR, not only milestones.

## Done
- The skill run on its own PR and on one past stage PR (#74), findings posted to each.
- The hook blocks a stop without the review comment and lets it through with one.

## Later (not this item)
- Parallel hunters + voting, if one reviewer turns out noisy (many "wrong" / "didn't matter" answers) or misses bugs.
- Eval set: PRs that caused regressions (R5 tests cite them), rerun whenever the skill or the model changes; keep a change only if the score goes up.
- Track rounds-to-pass per PR.
