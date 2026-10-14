#!/bin/bash
# Publish a run_clip.sh evidence root to the open PR of the current branch.
# usage: .claude/skills/verify/scripts/publish_evidence.sh <evidence_root> "<review>"
#   review: what the frame sheets show, one line per sheet (markdown), put under the result;
#           for a <name>_worst.jpg, name each of its frames
#   DRY_RUN=1 prints the comment and pushes nothing
# Commits the root as <root name>/ to the branch evidence/pr-<n> (its own history, never
# merged), pushes it and comments on the PR: per clip ✅ / ❌ from the log's result line,
# the commit under test, the check lines, the review, every jpg inline (the clip's and the
# calibration's, calibrate_<T5>/; images at the top of the root, e.g. a screenshot.sh explainer,
# under "Explainer") and links to the other files, all pinned to the evidence commit. The branch is deleted when the PR closes (.github/workflows/delete-evidence.yml); the comment text
# stays, its images and links break.
set -e
fail() { echo "FAIL: $1"; exit 1; }
[ -d "$1" ] && [ -n "$2" ] || fail 'usage: publish_evidence.sh <evidence_root> "<review of the frame sheets>"'
review=$2
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
result() {  # result <log>: the last OK / FAIL line, else the run did not finish
  local r; r=$(grep -E '^(OK evidence:|FAIL:)' "$1" | tail -1)
  case $r in "OK evidence:"*) echo "✅ OK" ;; FAIL:*) echo "❌ $r" ;; *) echo "❌ no result line (run did not finish)" ;; esac
}
results=$(for log in "$ev"/*.log; do result "$log"; done)
if grep -q '^❌' <<<"$results"; then overall="❌ FAIL"; else overall="✅ OK"; fi
commit=DRY_RUN
if [[ -z $DRY_RUN ]]; then
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
fi
url=https://github.com/$repo/blob/$commit/$name
{
  echo "## /verify evidence: \`$name\` $overall"
  echo
  echo "**Review:**"
  echo
  echo "$review"
  explainers=$(find "$ev" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' \) | sort)
  if [[ -n $explainers ]]; then
    echo
    echo "### Explainer"
    while read -r f; do echo "![$(basename "$f")]($url/$(basename "$f")?raw=true)"; done <<<"$explainers"
  fi
  for log in "$ev"/*.log; do
    c=$(basename "${log%.log}")
    echo
    echo "### $(result "$log") \`$c\`"
    echo '```'
    head -1 "$log"
    grep -E '^(cache |\(cached\) |calibrate|first|rerun|retry|  )' "$log" || true
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
  for d in "$ev"/calibrate_*/; do
    [ -d "$d" ] || continue
    d=$(basename "$d")
    echo
    echo "### calibration \`$d\`"
    find "$ev/$d" -type f -name '*.jpg' | sort | while read -r f; do
      echo "![${f#"$ev/$d/"}]($url/$d/${f#"$ev/$d/"}?raw=true)"
    done
  done
  echo
  echo "Files: https://github.com/$repo/tree/$commit/$name (branch \`$branch\`, deleted when this PR closes)"
} >"$body"
if [[ -n $DRY_RUN ]]; then cat "$body"; exit 0; fi
gh pr comment "$pr" --body-file "$body"
