#!/bin/bash
# Claude Code Stop hook: an agent on a branch with an open PR may stop only when HEAD is
# pushed and the PR has a ✅ /verify evidence comment (publish_evidence.sh) for HEAD, or
# for an earlier commit with the same prototype/ and verify scripts (a docs-only commit
# needs no new run). Else exit 2: the reason goes back to the agent and it keeps working.
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
[[ $(git rev-parse '@{u}' 2>/dev/null) == "$head" ]] || block "HEAD $(git rev-parse --short HEAD) is not pushed; push it, then run /verify and publish_evidence.sh"
proven=$(gh pr view "$pr" --json comments \
  -q '.comments[].body | select(startswith("## /verify evidence:") and (split("\n")[0] | contains("✅ OK")))' 2>/dev/null |
  sed -n 's/^commit \([0-9a-f]\{7,\}\) .*/\1/p' | sort -u) || exit 0
for sha in $proven; do
  git cat-file -e "$sha^{commit}" 2>/dev/null &&
    git diff --quiet "$sha" "$head" -- prototype .claude/skills/verify/scripts && exit 0
done
block "no ✅ /verify evidence for HEAD $(git rev-parse --short HEAD); run run_clip.sh on T1, look at the frame sheets, then publish_evidence.sh <root> \"<review>\". If a check fails, fix it, or report it in the PR"
