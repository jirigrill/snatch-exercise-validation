# Code review skill

Source: "How the Claude Code team does code review" (claude.dev blog, 2026-10-15). Agreed 2026-10-21.

Problem: the agent that plans a change also reviews its diff (CLAUDE.md, Workflow), and that review leaves nothing on the PR. GitHub only gets the output evidence from /verify. No second reviewer, no CI, no branch protection (free private repo). #75 merged 3 min after it opened.

## Scope
- New project skill `.claude/skills/review/`, separate from /verify. Review reads the diff and runs nothing; /verify proves outputs (clips, sheets, proofs, image review in `review.md` stay there).
- Review goes before /verify, not in parallel, so its fixes don't make the clips rerun (see Flow).
- Review posts findings, never an approval. The human still merges.
- Out of scope: the validation milestone's blind markers (`validation-milestone.md`), CI, a PR template (CLAUDE.md already sets the PR body), parallel hunters + voting, a full reviewer eval set (the 3 recall cases and the noise check in Done are the minimum; the rest is in Later).

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
| Trivial fix (defined below) | None |
| Only `.scratch/` or `docs/` | None |

- **Trivial fix** (all three, from `git show --numstat <sha>`): 1 file; at most 10 added + deleted lines; the file is not a deep-review path. 10 = CLAUDE.md's "a few lines, one file". The Stop hook uses the same check.
- **Changes the approach / rewrites a large part** (any one, from git, no judgement): the commit adds or deletes a file under `prototype/src/`; it touches 4 or more files; or it changes more than 150 added + deleted lines. Reason: mechanical, so the hook and the main agent agree without asking the reviewer.

## Reviewer
- Input: the diff, the plan item it claims to do (the PR's intent), the spec section for the stages the diff touches (not the whole `docs/pipeline-v2.html`) plus that stage's md, and CLAUDE.md. Not the briefs or the session history, so it isn't anchored on how the code was meant to work. The exact prompt the reviewer got is pasted in the `/review` comment (in a `<details>`), so the input can be checked (Done, Reviewer input).
- Diff to spec (rule): a changed file `prototype/src/snatch/stages/<x>.py` (and the `snatch/<x>.py` module it wraps, e.g. `scale.py`) → its stage id, from the `## S<n> · ...` heading of `.claude/skills/verify/features/stage-guide.md` → the same-id entry in `docs/pipeline-v2.html` (the `S<n>: { t:"S<n> · ..."` object under "Steps, outputs and overlays", plus any "Decisions" item naming the id) and the plan md that covers it (`B-front.md`: S-1 to S4; `C-skeleton.md`: C3, S5, S6; `D-judge.md`: S7 to S9, report). A file in no stage (`reps.py`, `signals.py`, verify scripts, hooks, CLAUDE.md-level files) → no spec section; the reviewer gets the plan item and CLAUDE.md only, and checks the stage-contract text of `stage.py`'s callers instead.
- Questions: does the change do what the item says, does it fit the spec and the stage contract, what does it break. On a bug fix: is it the root cause, not a patch over the symptom. Which CLAUDE.md, spec or plan lines does the diff make stale (e.g. the pyright baseline in `features/tests.md` said 20 errors long after main was at 0)?
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
- A bug that review missed and /verify, the milestone or the human found later: ask what the reviewer lacked (context, a failure-list entry, a spec section), and add it to the skill's failure list or the reviewer's input.

## Depth by risk
- Stage code: normal review.
- `check_pipeline.py`, `stage_cache.py`, the other verify scripts, `.claude/hooks/`, the S8 judge: deep review plus a "human should read" line at the top of the comment (a bug there makes all evidence lie). "Deep" = the reviewer reads each changed function in full (not just the diff hunks) and the callers of what changed.

## Stop hook (`require-evidence.sh`)
- Extends today's checks (HEAD pushed, ✅ /verify evidence comment for HEAD or an earlier sha with the same `prototype/` + verify scripts, docs-only PR exits early). Same fail-open and block-once behaviour; same `block()` message style.
- A `/review` comment is found by header `## /review: <sha> — N findings`; its sha line is read like the /verify comment's `commit <sha>`. "Trivial" = the definition in Which commits get reviewed.
- Scripted cases, 9 (each is a Done line), in `.claude/hooks/test_require_evidence.sh`: a shell script run against a stub `gh` on `PATH` and a temp git repo, exit 0 = all pass. Not a pytest test: the CLAUDE.md test rule (R1–R5) covers the pipeline, not the hooks, and this script sits outside it.
| # | State | Result |
|---|---|---|
| 1 | no `/review` comment | block |
| 2 | `/review` comment for HEAD, every Important has an answer | allow |
| 3 | `/review` comment for HEAD, one Important unanswered | block |
| 4 | `/review` comment for an older sha + a later commit that is not trivial and not docs/plan only | block |
| 5 | `/review` comment for an older sha + only trivial or docs/plan commits after | allow |
| 6 | /verify comment lacks pytest/pyright results, or shows pytest failed or pyright errors > 0 | block |
| 7 | second stop attempt (`stop_hook_active` true; the stop-on-retry fallback) | allow |
| 8 | on `main` / `evidence/*`, or no open PR (today's behaviour, kept) | allow |
| 9 | PR with no change under the review paths vs main (`prototype/`, verify scripts, `.claude/hooks/`, `.claude/skills/review/`; docs-only) | allow without /review (a hooks/review-only PR needs /review but no /verify) |

## Overlap with /verify
- pytest + pyright: run by /verify only (already per commit, `SKILL.md` Fast gate). /verify records the results in its evidence comment (a change to `publish_evidence.sh`/`render_comment.py`); the Stop hook reads them there. /review neither runs nor records them.
- Spec vs code: `check_pipeline.py` checks it at runtime; the reviewer is told so (Reviewer) and doesn't repeat it.
- Naming (decided): rename /verify's `review.md` → `sheets.md` and "the reviewer" in `features/stage-guide.md` → "the reader". Reason: with a /review skill and a `/review` comment, "review.md" reads as the code review; the rename is 5 files (`SKILL.md`, `publish_evidence.sh`, `render_comment.py`, `require-evidence.sh` message, `stage-guide.md`) and no behaviour. The comment header `## /verify evidence:` stays. Done in this item's PR.

## CLAUDE.md
- Workflow: "Main agent (Opus) plans, reviews and verifies" → it plans, does the light check, triages review findings and verifies; the review itself is /review's clean-context reviewer. Name /review, then /verify, in that order.
- PR body: "what the checks would miss" on every PR, not only milestones.
- Anywhere CLAUDE.md says `review.md` (the image review) → `sheets.md` (Overlap with /verify, Naming).

## Done
Each line has a pass rule; all are checked and the results are in the PR.
- **Runs**: the skill run on its own PR and on #74 (past stage PR), a `/review` comment posted to each. Pass = both comments exist with the header and a count line.
- **Recall, past bug**: run the reviewer on the diff that introduced the cut-clip pre-roll bug (R5 test `test_video.py`, cites #52): commit `77cddcb` ("Real frame times for dropped-frame clips"), merged in #39; diff = `git show 77cddcb -- prototype/src/snatch/video.py` (`timestamps()` counts packets with negative pts that never decode). Pass = an **Important** finding citing `prototype/src/snatch/video.py` at a line of `timestamps()` and naming the class: its text contains (case-insensitive) one of `pre-roll`, `negative pts`, `undecoded`, `never decode`. Miss = see Recall rules. (#71's bug, `visible_knee` taking the plate hub for the ankle, was found and fixed inside its own PR before merge, so no introducing diff exists; not used.)
- **Recall, planted bugs**: take #74's diff (S6 fill, a real stage diff, merge `9a488cf`; `git diff 9a488cf^1 9a488cf`) and inject one failure-list bug per run, as a throwaway local patch (never committed): (a) drop `"scale.json"` from the inputs tuple of `STAGE = Stage("S6", ...)` in `prototype/src/snatch/stages/fill.py` (the stage cache misses an input, so a changed S5 factor serves a stale fill; failure list, cache bullet); (b) change `HOLDOUT_GATE_CM = 3.0` to `3000.0` in `check_pipeline.py` (the hold-out check can never fail; failure list, trivial-check bullet). Pass, each = an **Important** finding citing that file and the injected line (±2 lines) and naming the class: its text contains (case-insensitive) for (a) one of `cache key`, `stale`, `missing input`, `scale.json`; for (b) one of `never fail`, `unreachable`, `trivially`, `always pass`. Both must pass.
- **Recall rules** (all three recall cases): the class-word check is a grep on the finding text. On a miss, the input may change only in general ways (a failure-list entry, more spec context, a reviewer question), never by naming the case, its file, its line or its bug; the change has to read as true for any PR. At most 2 reruns per case after the first run. Still a miss → stop and report it in the PR with what was tried; don't tune further. Every input change made for a miss is listed in the PR. (b) is also a deep-review path, so the "human should read" line must be there too.
- **Noise check**: run on #69 (frames(): stop ffmpeg at the last needed frame; 3 files under `prototype/src`, 10 added / 7 deleted lines). Clean because: code under `prototype/src`, `git log` shows no later change to `video.py`'s `frames()` since it merged, and no R5 test or later PR cites it. Pass = 0 **Important**; the Nit and Pre-existing counts are reported in the PR, not gated.
- **Finding checker**: fed two findings, one with file:line evidence the code supports and one guessed from a name (no line), it keeps only the first; fed a style-only finding, it drops it. Pass = exactly those outcomes, shown as the checker's output in the PR.
- **Round cap**: a review that is still not clean after 3 find-and-fix rounds on a commit stops and asks (no 4th round). Pass = shown on a forced case: the skill reads env `REVIEW_STUB=<file>`; when set, the reviewer step returns that file's findings instead of spawning the agent (the only test hook in the skill). With a stub file holding one Important, the session stops after round 3 with the question.
- **Reviewer input**: the prompt the reviewer got is pasted in the PR comment and contains no briefs or session history. Pass = the pasted prompt holds only the diff, plan item, spec section + stage md, and CLAUDE.md (checked by a clean-context Sonnet agent given the pasted prompt and this rule, plus a grep for brief / session text; no human step).
- **Deep-review paths**: a diff touching `check_pipeline.py`, `stage_cache.py`, another verify script, `.claude/hooks/` or the S8 judge gets the "human should read" line at the top of the comment. Pass = present on the skill's own PR (it edits the hook) and absent on #69.
- **Evidence comment**: `/verify`'s comment records the pytest and pyright results. Pass = the comment on the skill's PR shows pytest passed count and pyright error count (0), and `publish_evidence.sh` FAILs when they are missing.
- **Hook**: `require-evidence.sh` passes the 9 scripted cases in Stop hook, each with its expected block/allow. Pass = all 9 as expected.
- **CLAUDE.md**: the Workflow and PR body edits listed in CLAUDE.md above are made, and `review.md` → `sheets.md` leaves no `review.md` anywhere (`git grep review.md` empty outside this plan). Pass = both.

## Later (not this item)
- Parallel hunters + voting, if one reviewer turns out noisy (many "wrong" / "didn't matter" answers) or misses bugs.
- Eval set: PRs that caused regressions (R5 tests cite them), rerun whenever the skill or the model changes; keep a change only if the score goes up.
- Track rounds-to-pass per PR.
- One full-code review (not a diff) before Milestone D: most of the code was never reviewed independently. Findings tagged Pre-existing go into the plan.
