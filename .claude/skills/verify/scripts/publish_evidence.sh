#!/bin/bash
# Publish a run_clip.sh evidence root to the open PR of the current branch.
# usage: .claude/skills/verify/scripts/publish_evidence.sh <evidence_root> <sheets.md>
#   sheets.md: `## <stage>` sections of bullets `- <clip id> <image stem>: <plain-English verdict>`,
#   one per image shown for that stage, naming every frame of a _worst image (render_comment.py has
#   the format; a `no proof: <reason>` line under a stage stands in for its proof). DRY_RUN=1 prints the comment and pushes nothing.
# What is shown: with a baseline (<root>/base/, from base_run.sh) the stages whose outputs differ from
# main's on any clip (diff_outputs.py, rerun here); without one the stages whose code changed vs the
# merge base with origin/main (stage_files.py show; SHOW_STAGES="S2 C3" adds names, `all` shows all) and
# the comment says so. A new/changed stage needs a proof or a `no proof:` line, and the root a log for
# every test clip T1-T8 (render_comment.py fails otherwise). render_comment.py checks the review (fails here, before anything is pushed) and
# writes the comment: result per clip, a table of every stage (new / changed / identical / absent), then
# per shown stage its guide text (features/stage-guide.md), proof (<root>/proof/<stage>/verdict.md +
# images, written by the PR's own script) and per clip the detail lines, images and review bullets.
# Before rendering it runs `uv run pytest -q` and `uv run pyright` in prototype/ and writes <root>/fast_gate.txt
# (`checks: pytest P passed, F failed · pyright E errors`; test failures are recorded, not fatal); the comment
# shows that line and render_comment.py FAILs when it is missing. FAILs here when either output can't be parsed.
# Commits the root (without base/) as <root name>/ to the branch evidence/pr-<n> (own history, never
# merged), pushes it and comments on the PR, links pinned to that commit. The branch is deleted when the
# PR closes (.github/workflows/delete-evidence.yml); the comment text stays, its images and links break.
set -e
fail() { echo "FAIL: $1"; exit 1; }
[ -d "$1" ] && [ -f "$2" ] || fail 'usage: publish_evidence.sh <evidence_root> <sheets.md>'
ev=$(cd "$1" && pwd)
review=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
name=$(basename "$ev")
here=$(cd "$(dirname "$0")" && pwd)
cd "$here"
if [[ -z $DRY_RUN && -n $(git status --porcelain -- ../../../../prototype . ) ]]; then
  fail 'uncommitted changes under prototype/ or .claude/skills/verify/scripts: the gate would measure them under the log commit'
fi
pr=$(gh pr view --json number -q .number 2>/dev/null) || pr=
[[ -n $pr || -n $DRY_RUN ]] || fail "no open PR for branch $(git rev-parse --abbrev-ref HEAD)"
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
branch=evidence/pr-$pr
stage=$(mktemp -d)
index=$(mktemp -u)
trap 'rm -rf "$stage" "$index"' EXIT
render() {  # render <blob url> <files line>: the comment on stdout, FAIL (exit 1) when the review does not fit
  (cd "$here/../../../../prototype" &&
    uv run python "$here/render_comment.py" "$ev" "$review" "$1" "$2")
}
if [ -d "$ev/base" ]; then
  (cd "$here/../../../../prototype" && uv run python "$here/diff_outputs.py" "$ev" >/dev/null) || fail "diff_outputs.py failed"
fi
pt=$(cd "$here/../../../../prototype" && uv run pytest -q 2>&1) || true
pr_out=$(cd "$here/../../../../prototype" && uv run pyright 2>&1) || true
pline=$(printf '%s\n' "$pt" | grep -E '^=*[^=]*[0-9]+ (passed|failed|error)' | tail -1)
pp=$(printf '%s' "$pline" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || true)
pf=0 pfn=
for pfn in $(printf '%s' "$pline" | grep -oE '[0-9]+ (failed|errors?)' | grep -oE '[0-9]+' || true); do pf=$((pf + pfn)); done
pe=$(printf '%s\n' "$pr_out" | grep -oE '[0-9]+ errors?' | tail -1 | grep -oE '[0-9]+' || true)
rm -f "$ev/fast_gate.txt"
if [[ -n $pline && -n $pe && ( -n $pp || $pf -gt 0 ) ]]; then
  echo "checks: pytest ${pp:-0} passed, ${pf:-0} failed · pyright $pe errors" >"$ev/fast_gate.txt"
else
  fail 'pytest/pyright results missing (output not parsed)'
fi
render "" "" >/dev/null  # the gate, before anything is pushed
mkdir "$stage/$name" && tar -C "$ev" --exclude=./base -cf - . | tar -C "$stage/$name" -xf -
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
body=$(mktemp)
trap 'rm -rf "$stage" "$index" "$body"' EXIT
render "https://github.com/$repo/blob/$commit/$name" \
  "Files: https://github.com/$repo/tree/$commit/$name (branch \`$branch\`, deleted when this PR closes)" >"$body"
if [[ -n $DRY_RUN ]]; then cat "$body"; exit 0; fi
gh pr comment "$pr" --body-file "$body"
