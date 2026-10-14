#!/bin/bash
# Delete local /verify evidence nobody needs: a root under .scratch/verify/ whose branch (from
# the `commit <sha> <branch>, …` line of its logs) is neither checked out nor has an open PR,
# so evidence goes once its PR is merged or closed. Keeps the newest CACHE_KEEP entries per
# cache dir. Run by the SessionStart hook (.claude/settings.json); safe to run by hand.
# Offline or without gh: deletes nothing. DRY_RUN=1 only prints. The remote evidence/pr-<n>
# branch goes with the PR (.github/workflows/delete-evidence.yml).
CACHE_KEEP=3
cd "$(dirname "$0")/../../../.." || exit 0
v=.scratch/verify
[ -d $v ] || exit 0
open=$(gh pr list --state open --limit 200 --json headRefName -q '.[].headRefName' 2>/dev/null) || exit 0
current=$(git rev-parse --abbrev-ref HEAD)
rm_() { if [[ -n $DRY_RUN ]]; then echo "would delete $1"; else rm -rf "$1"; fi; }
for d in $v/*/; do
  d=${d%/}
  [[ $(basename "$d") == cache ]] && continue
  branch=$(cat "$d"/*.log 2>/dev/null | sed -n 's/^commit [0-9a-f]* \([^,]*\),.*/\1/p' | head -1)
  [[ -n $branch && ( $branch == "$current" || $'\n'$open$'\n' == *$'\n'$branch$'\n'* ) ]] && continue
  rm_ "$d" && echo "sweep: deleted $d (branch ${branch:-unknown}, no open PR)"
done
for c in $v/cache/*/; do
  ls -t "$c" | tail -n +$((CACHE_KEEP + 1)) | while read -r k; do rm_ "$c$k"; done
done
exit 0
