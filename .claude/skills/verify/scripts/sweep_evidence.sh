#!/bin/bash
# Delete local /verify evidence nobody needs: a root under .scratch/verify/ whose branch (from
# the `commit <sha> <branch>, …` line of its logs) is neither checked out nor has an open PR,
# so evidence goes once its PR is merged or closed. Keeps the newest CACHE_KEEP entries per
# cache dir; removes base worktrees (base_run.sh) beyond the newest CACHE_KEEP or that are not the merge
# base of the checked-out branch or an open PR. Run by the SessionStart hook (.claude/settings.json);
# safe to run by hand.
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
  [[ $(basename "$d") == cache || $(basename "$d") == base-worktrees ]] && continue
  branch=$(cat "$d"/*.log 2>/dev/null | sed -n 's/^commit [0-9a-f]* \([^,]*\),.*/\1/p' | head -1)
  [[ -n $branch && ( $branch == "$current" || $'\n'$open$'\n' == *$'\n'$branch$'\n'* ) ]] && continue
  rm_ "$d" && echo "sweep: deleted $d (branch ${branch:-unknown}, no open PR)"
done
for c in $v/cache/*/; do
  ls -t "$c" | tail -n +$((CACHE_KEEP + 1)) | while read -r k; do rm_ "$c$k"; done
done
# base worktrees (base_run.sh): keep one only when it is among the CACHE_KEEP newest and the merge base
# of the checked-out branch or of an open PR's branch; the others go through git (never rm -rf)
keep=$(for b in "$current" $open; do git merge-base origin/main "$b" 2>/dev/null || git merge-base origin/main "origin/$b" 2>/dev/null; done)
n=0
for w in $(ls -td $v/base-worktrees/*/ 2>/dev/null); do
  w=${w%/}; n=$((n + 1))
  [[ $n -le $CACHE_KEEP ]] && grep -q "^$(basename "$w")" <<<"$keep" && continue
  if [[ -n $DRY_RUN ]]; then echo "would remove base worktree $w"
  else git worktree remove --force "$w" && echo "sweep: removed base worktree $w"; fi
done
[[ -n $DRY_RUN ]] || git worktree prune
exit 0
