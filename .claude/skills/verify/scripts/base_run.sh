#!/bin/bash
# Run main's pipeline on the same clips as an evidence root, so the PR comment can show only what
# the PR changed (diff_outputs.py compares <root>/<clip>/ with <root>/base/<clip>/).
# usage: .claude/skills/verify/scripts/base_run.sh <evidence_root>
# Baseline = `git merge-base HEAD origin/main`, checked out as a git worktree in
# .scratch/verify/base-worktrees/<short sha> (reused; sweep_evidence.sh removes old ones) with
# .scratch and vids symlinked to this checkout's, so main's own run_clip.sh shares the caches
# (.scratch/verify/cache) and the lock. For every clip with a <root>/<clip>.log it runs the
# WORKTREE's run_clip.sh on the same clip into <root>/base/ (one at a time). Main's stage
# outputs are mostly cached, so this is cheap. Prints the base sha. Idempotent: a clip whose
# <root>/base/<clip>.log has the same base sha and a result line is skipped.
# Exit 0 = every clip OK on main, 1 = a base run FAILed (that clip is then not compared).
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
[ -d "$1" ] || { echo "usage: base_run.sh <evidence_root>"; exit 1; }
ev=$(cd "$1" && pwd)
real=$(cd -P "$root/.scratch/.." && pwd)  # the main checkout (root itself may be a worktree)
base=$(git -C "$root" merge-base HEAD origin/main)
wt=$real/.scratch/verify/base-worktrees/$(git -C "$root" rev-parse --short "$base")
mkdir -p "$real/.scratch/verify/base-worktrees"
if [ ! -d "$wt" ]; then
  git -C "$root" worktree add -q --detach "$wt" "$base"
  rm -rf "$wt/.scratch" "$wt/vids"  # .scratch/plan is tracked: the symlink replaces the checked-out copy
  ln -s "$real/.scratch" "$wt/.scratch" && ln -s "$real/vids" "$wt/vids"
fi
[ -d "$wt/prototype/.venv" ] || (cd "$wt/prototype" && uv sync -q)
short=$(git -C "$wt" rev-parse --short HEAD)
echo "base $base (merge-base of HEAD and origin/main), worktree $wt"
mkdir -p "$ev/base"
bad=0
for log in "$ev"/*.log; do
  c=$(basename "${log%.log}")
  if [ "$(head -1 "$ev/base/$c.log" 2>/dev/null | cut -d' ' -f2)" = "$short" ] &&
     grep -qE '^(OK evidence:|FAIL:)' "$ev/base/$c.log"; then
    echo "base $c: already run ($(grep -E '^(OK evidence:|FAIL:)' "$ev/base/$c.log" | tail -1 | cut -c1-40))"; continue
  fi
  "$wt/.claude/skills/verify/scripts/run_clip.sh" "$real/vids/test/$c.MOV" "$ev/base" || bad=1
done
exit $bad
