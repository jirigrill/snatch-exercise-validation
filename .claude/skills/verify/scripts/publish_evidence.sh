#!/bin/bash
# Publish a run_clip.sh evidence root to the open PR of the current branch.
# usage: .claude/skills/verify/scripts/publish_evidence.sh <evidence_root>
# Commits the root as <root name>/ to the branch evidence/pr-<n> (its own history, never
# merged), pushes it and comments on the PR: the commit under test, the check lines, every
# jpg inline and links to the other files, all pinned to the evidence commit. The branch is
# deleted when the PR closes (.github/workflows/delete-evidence.yml); the comment text
# stays, its images and links break.
set -e
fail() { echo "FAIL: $1"; exit 1; }
[ -d "$1" ] || fail "usage: publish_evidence.sh <evidence_root>"
ev=$(cd "$1" && pwd)
name=$(basename "$ev")
cd "$(dirname "$0")"
pr=$(gh pr view --json number -q .number 2>/dev/null) || fail "no open PR for branch $(git rev-parse --abbrev-ref HEAD)"
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
branch=evidence/pr-$pr
stage=$(mktemp -d)
index=$(mktemp -u)
body=$(mktemp)
trap 'rm -rf "$stage" "$index" "$body"' EXIT
cp -R "$ev" "$stage/$name"
# a private index, so the checkout and its index stay untouched
export GIT_INDEX_FILE=$index
parent=
if git fetch -q origin "refs/heads/$branch" 2>/dev/null; then
  parent=$(git rev-parse FETCH_HEAD)
  git read-tree "$parent"
else
  git read-tree --empty
fi
git --work-tree="$stage" add -f -- "$name"
commit=$(git commit-tree "$(git write-tree)" ${parent:+-p "$parent"} -m "verify evidence for PR #$pr: $name")
unset GIT_INDEX_FILE
git push -q origin "$commit:refs/heads/$branch"
url=https://github.com/$repo/blob/$commit/$name
{
  echo "## /verify evidence: \`$name\`"
  for log in "$ev"/*.log; do
    c=$(basename "${log%.log}")
    echo
    echo "### \`$c\`"
    echo '```'
    head -1 "$log"
    grep -E '^(cache |first|rerun|  )' "$log" || true
    echo '```'
    find "$ev/$c" -type f -name '*.jpg' | sort | while read -r f; do
      echo "![${f#"$ev/$c/"}]($url/$c/${f#"$ev/$c/"}?raw=true)"
    done
    echo
    find "$ev/$c" -type f ! -name '*.jpg' | sort | while read -r f; do
      echo "[\`${f#"$ev/$c/"}\`]($url/$c/${f#"$ev/$c/"})"
    done | paste -sd ' ' -
    echo "[\`$c.log\`]($url/$c.log)"
  done
  echo
  echo "Files: https://github.com/$repo/tree/$commit/$name (branch \`$branch\`, deleted when this PR closes)"
} >"$body"
gh pr comment "$pr" --body-file "$body"
