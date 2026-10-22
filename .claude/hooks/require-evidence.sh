#!/bin/bash
# Claude Code Stop hook: an agent on a branch with an open PR may stop only when HEAD is
# pushed and, if prototype/ or the verify scripts changed vs main, the PR has a ✅ /verify
# evidence comment (publish_evidence.sh) for HEAD, or for an earlier commit with the same
# prototype/ and verify scripts (a docs-only commit needs no new run). The /verify comment must
# carry a "checks: pytest N passed, 0 failed · pyright 0 errors" line. A change under prototype/,
# the verify scripts, .claude/hooks or .claude/skills/review also needs a "## /review: <sha> — N
# findings" comment: the newest one whose sha is HEAD or an ancestor and after which every commit
# not on origin/main is docs or trivial (commit_kind.sh), with every Important answered
# ("**Answer:** fixed|wrong|intentional|didn't matter"). A branch changing none of these needs
# nothing. Else exit 2: the reason goes back to the agent and it keeps working.
# Blocks once per stop: on the retry (stop_hook_active) it lets the agent stop, so a check
# that cannot pass never loops. Fails open when git or gh cannot answer (offline, no PR).
input=$(cat)
[[ $(jq -r '.stop_hook_active // false' <<<"$input") == true ]] && exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
[[ $branch == main || $branch == HEAD || $branch == evidence/* ]] && exit 0
pr=$(gh pr view --json number,state -q 'select(.state == "OPEN") | .number' 2>/dev/null)
[[ -n $pr ]] || exit 0
block() { echo "PR #$pr: $1 (CLAUDE.md, checks after each commit)" >&2; exit 2; }
head=$(git rev-parse HEAD)
[[ $(git rev-parse '@{u}' 2>/dev/null) == "$head" ]] || block "HEAD $(git rev-parse --short HEAD) is not pushed; push it, then run /verify and publish_evidence.sh <root> <sheets.md>"
vpaths=(prototype .claude/skills/verify/scripts)
rpaths=("${vpaths[@]}" .claude/hooks .claude/skills/review)
base=$(git merge-base origin/main "$head" 2>/dev/null) &&
  git diff --quiet "$base" "$head" -- "${rpaths[@]}" && exit 0
need_verify=1
git diff --quiet "$base" "$head" -- "${vpaths[@]}" && need_verify=0
head_s=$(git rev-parse --short HEAD)
# comments as base64 lines, oldest first; each body is decoded where needed
comments=$(gh pr view "$pr" --json comments -q '.comments[].body | @base64' 2>/dev/null) || exit 0
checks_re='^checks: pytest ([0-9]+) passed, ([0-9]+) failed · pyright ([0-9]+) errors'
bad_checks=0 verified=0
while IFS= read -r b64; do
  [[ -n $b64 ]] || continue
  body=$(base64 -d <<<"$b64" 2>/dev/null) || continue
  first=${body%%$'\n'*}
  [[ $first == "## /verify evidence:"* && $first == *"✅ OK"* ]] || continue
  sha=$(sed -n 's/^commit \([0-9a-f]\{7,\}\) .*/\1/p' <<<"$body" | head -1)
  [[ -n $sha ]] && git cat-file -e "$sha^{commit}" 2>/dev/null &&
    git diff --quiet "$sha" "$head" -- prototype .claude/skills/verify/scripts || continue
  ok=0
  while IFS= read -r line; do
    if [[ $line =~ $checks_re ]] && ((BASH_REMATCH[1] > 0 && BASH_REMATCH[2] == 0 && BASH_REMATCH[3] == 0)); then ok=1; break; fi
  done <<<"$body"
  if ((ok)); then verified=1; else bad_checks=1; fi
done <<<"$comments"
((verified || !need_verify)) || {
  ((bad_checks)) && block "/verify comment for $head_s lacks pytest/pyright results or shows failures; rerun publish_evidence.sh"
  block "no ✅ /verify evidence for HEAD $head_s; run run_clip.sh on T1, base_run.sh <root>, look at the images of the changed stages and write sheets.md, then publish_evidence.sh <root> sheets.md. If a check fails, fix it, or report it in the PR"
}

# /review (spec rule): the newest "## /review: <sha> — N findings" comment whose sha is HEAD or an
# ancestor, with only docs/trivial non-merge commits (commit_kind.sh) after it that are not on
# origin/main; its Importants must all be answered.
kind_sh=.claude/skills/review/scripts/commit_kind.sh
[[ -f $kind_sh ]] || block "commit_kind.sh missing; cannot classify commits"
review_re='^## /review: ([0-9a-f]{7,}) — [0-9]+ findings'
rshas=() rbodies=()
while IFS= read -r b64; do
  [[ -n $b64 ]] || continue
  body=$(base64 -d <<<"$b64" 2>/dev/null) || continue
  first=${body%%$'\n'*}
  [[ $first =~ $review_re ]] || continue
  sha=$(git rev-parse --verify -q "${BASH_REMATCH[1]}^{commit}") || continue
  git merge-base --is-ancestor "$sha" "$head" 2>/dev/null || continue
  rshas+=("$sha") rbodies+=("$body")
done <<<"$comments"
((${#rshas[@]})) || block "no /review comment; run /review (.claude/skills/review/SKILL.md) and post it with review.sh comment"
first_open() { # first non-docs, non-trivial non-merge commit in $1..HEAD not on origin/main
  local c k
  for c in $(git rev-list --reverse --no-merges "$1..$head" --not origin/main); do
    k=$(bash "$kind_sh" "$c"); [[ $k == docs || $k == trivial ]] || { echo "$c"; return; }
  done
}
pick=-1
for ((i = ${#rshas[@]} - 1; i >= 0; i--)); do
  [[ -z $(first_open "${rshas[i]}") ]] && { pick=$i; break; }
done
if ((pick < 0)); then
  c=$(first_open "${rshas[${#rshas[@]} - 1]}")
  block "commit $(git rev-parse --short "$c") ($(git log -1 --format=%s "$c")) is after the newest /review comment and is not docs or trivial; run /review and post it with review.sh comment"
fi
# findings part = from the first "### " line to the details sentinel line
unanswered=$(awk '
  $0 == "<details><summary>Reviewer prompt</summary>" { exit }
  /^### / { if (id != "" && !ok) printf "%s ", id; id = ""; ok = 0
            if ($0 ~ /^### F[0-9]+ · Important/) { id = $2 } next }
  id != "" && /^\*\*Answer:\*\* (fixed|wrong|intentional|didn.t matter)/ { ok = 1 }
  END { if (id != "" && !ok) printf "%s ", id }' <<<"${rbodies[pick]}")
[[ -z $unanswered ]] || block "/review comment for $(git rev-parse --short "${rshas[pick]}") has Important findings without an **Answer:** (fixed, wrong, intentional or didn't matter): ${unanswered% }; answer them and repost with review.sh comment"
exit 0
