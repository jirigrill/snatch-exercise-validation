---
name: review
description: Clean-context code review of a diff before /verify. Use before /verify on any change under prototype/, .claude/skills/verify/scripts, .claude/hooks or .claude/skills/review. Reads the diff and runs nothing; posts findings (never an approval) as a /review PR comment.
---

# Review: clean-context diff review

Reads the diff, runs nothing. /verify proves outputs (clips, sheets, proofs); /review goes first so its fixes don't rerun clips. Findings only, never an approval; the human merges. Spec: `.scratch/plan/review-skill.md`. Scripts: `.claude/skills/review/scripts/` (`review.sh`, `build_prompt.py`, `commit_kind.sh`); prompts: `reviewer.md`, `checker.md`.

## Roles
| Role | Model | Context |
|---|---|---|
| Main agent | Opus | Full session. Light check (each unit did its brief; developers' pytest + pyright green, not rerun here) and triage. Never writes findings |
| Developers | Sonnet | Only its brief |
| Reviewer | Opus, every review | Clean: the prompt file only (diff, plan item, spec section + stage md, CLAUDE.md, prior findings) |
| Finding checker | Sonnet | Clean: findings + the code they cite |

## Flow
1. Developers finish (parallel units: wait for all, review the combined diff). 2. Light check. 3. /review -> fixes -> diff-only review of the fixes; at most **3 find-and-fix rounds per commit** (`review.sh` counts per HEAD sha; the 4th prints STOP, exit 3: ask the user whether the approach is right). 4. Commit. 5. /verify (FAIL -> fix -> diff-only review of the fix -> /verify). 6. Push, open the PR. 7. Post the `/review` comment + /verify evidence. 8. Stop hook checks both.

## Which commits get reviewed
`commit_kind.sh <sha>` prints the kind:
| Kind | Review |
|---|---|
| first code commit, before the first push | `full`: `main...HEAD` + uncommitted (`review.sh prep full`) |
| later code commit | `diff`: only that diff; the reviewer gets the earlier findings (`--prior`) and doesn't repeat them |
| approach change / large (adds or deletes a file under `prototype/src/`, >= 4 files, > 150 lines) or a deep path | `full` again |
| `trivial` (1 file, <= 10 lines, not a deep path) | none |
| `docs` (only `.scratch/`, `docs/`) | none |
Before a commit exists (`review.sh prep`), judge by the same numbers from `git diff --numstat`. A past commit: `review.sh prep full <sha>^ <sha> -- <paths>`.

## Depth by risk
Stage code: normal. `check_pipeline.py`, `stage_cache.py`, other verify scripts, `.claude/hooks/`, the S8 judge (`commit_kind.sh deep <diff args>` = `yes`): deep. The reviewer reads each changed function in full and its callers, and the comment gets a `> **Human should read:**` line (a bug there makes all evidence lie).

## Steps (main agent)
1. `.claude/skills/review/scripts/review.sh prep <full|diff> [<git diff args>] [--item <plan item file>] [--prior <findings.md>]` -> prints the prompt file path (`.scratch/review/<branch>/<HEAD sha 7>/round<k>/prompt.md`), or `STOP: ...` (exit 3). Default item = first unchecked line of `.scratch/plan/README.md`.
2. Spawn the reviewer: `Agent` with `model: "opus"`, prompt = exactly `Read <abs path of prompt.md> in full and follow it; output only what it asks for.` (the file is the reviewer's whole input; pointing at it keeps a 100 KB prompt out of the main context). Nothing else: no briefs, no session history, no hints. Save its output to `round<k>/findings.md`. If `REVIEW_STUB` is set, `prep` printed `stub: ...` and copied the stub to `round<k>/findings.md`: use that as the reviewer output, do not spawn (the only test hook).
3. Findings present: spawn the checker, `Agent` with `model: "sonnet"`, prompt = `checker.md` with `{{FINDINGS}}` replaced by the findings (it reads the cited code itself). Use its kept list; its `Dropped:` list goes to the PR text. No findings: skip.
4. Triage: every **Important** goes to new Sonnet fix subagents (brief = the finding, its bug class, "fix every instance"); Nit and Pre-existing don't block (Pre-existing that matters goes in the plan). Then `review.sh prep diff --prior <findings.md>` reviews the fixes (next round, max 3).
5. After the commit, push and PR: merge the rounds' kept findings into one file for the commit (renumber F1..., one count line first, the `Human should read` line first when deep), write an `**Answer:**` under each finding, then `review.sh comment <sha> <findings.md> <prompt.md>` (prompt = the prompt of the round you are posting, normally round 1, the full review, with all rounds' findings merged into the findings file). It validates and posts; `DRY_RUN=1` prints only.

## Output format
Reviewer / findings file:
```
<a> Important, <b> Nit, <c> Pre-existing        (". Nothing to fix." when a = 0)

### F1 · Important · <bug class> · `path/file.py:123`
<what is wrong, evidence (quote the line), what breaks, what the fix must cover>
**Answer:** fixed (<sha>): <reason>
```
Tags: **Important** (blocks), **Nit** (max 3, never blocks), **Pre-existing** (bug the PR didn't add). Every finding names its bug class so the fix covers every instance.

PR comment (one per reviewed commit; the Stop hook parses the text before `<details>`):
```
## /review: <sha 7+ hex> — <N> findings            N = a + b + c
<a> Important, <b> Nit, <c> Pre-existing[. Nothing to fix.]
> **Human should read:** <deep paths touched>      (only when deep)
Review: <base 7>..<sha 7> (full|diff), round <k> of 3
Answers: <x> fixed, <y> wrong, <z> intentional, <w> didn't matter
### F1 ... (as above, with **Answer:**)
<details><summary>Reviewer prompt</summary> the exact prompt, fenced </details>
```
The `Review:` line is written by `review.sh comment` from `meta`; it is informational, the hook ignores it. `prep` records in `meta`: `base=<full sha>` (where the reviewed diff starts: default full = merge-base with origin/main, default diff = HEAD, explicit args = the first commit-ish), plus `mode`, `round`, `head`, `deep`, `args`.

Stop hook rule (spec cases 4/5): a /review comment for HEAD, or for an older sha with only `trivial`/`docs` commits after it.

Every PR that touches the review paths (`prototype/`, `.claude/skills/verify/scripts`, `.claude/hooks`, `.claude/skills/review`) needs at least one /review comment, even when all its commits are `trivial` (intentional; the hook's "no /review comment" block).

`review.sh comment` FAILs (exit 1) on missing round meta, a missing/wrong count line, an Important without `**Answer:**`, an answer not in the 4 categories (`fixed (<sha>)` / `wrong` / `intentional` / `didn't matter`, each `: <reason>`), or a deep diff without the human line (that line counts only before the first `### ` finding). It fills the Answers counts and truncates the prompt part past 65000 chars, saying so.

## Answers and learning
- Every finding is answered: fixed (sha) / wrong / intentional / didn't matter, with a reason. Counts per category = the noise rate.
- A finding that comes back across PRs becomes a rule (CLAUDE.md, a `check_pipeline.py` check, a pyright setting), not flagged again.
- A bug review missed and /verify, the milestone or the human found later: ask what the reviewer lacked (context, failure-list entry, spec section) and add it to the failure list in `reviewer.md` or to `build_prompt.py`'s input. General changes only, never naming the case.

## Standards
Reviewer sees nothing but the prompt file. Exclude `.scratch/` and `docs/results/` from the diff (`review.sh` does). State lives in `.scratch/review/<branch>/<HEAD sha 7>/` (`round<k>/`, plus `count`, the round counter); each HEAD has its own folder, so a later commit never overwrites an earlier one's round files. Gitignored with `.scratch/`; don't delete it by hand during a commit's rounds.

## Known gap
A commit that is not trivial, followed by a later commit with its own diff-only review, passes the hook unreviewed (c1 reviewed, c2 not, c3 diff-reviewed); accepted 2026-10-22, in the plan. `comment` does not check that <sha> is the reviewed code; posting for the wrong commit is caught by nobody (accepted 2026-10-22).
