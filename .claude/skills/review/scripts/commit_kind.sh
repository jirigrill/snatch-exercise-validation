#!/bin/bash
# Classifies a commit for /review and the Stop hook (.scratch/plan/review-skill.md, "Which commits
# get reviewed"). Check order: docs (every path under .scratch/ or docs/), trivial (1 file, <= 10
# added+deleted lines, not a deep path, not an add/delete under prototype/src/), full (adds/deletes a file under prototype/src/, or >= 4
# files, or > 150 lines, or a deep path), else diff. Deep paths: .claude/skills/verify/scripts/**,
# .claude/hooks/**, .claude/skills/review/**, prototype/src/snatch/**/judge*.py (the S8 judge).
# Usage: commit_kind.sh <sha>  ->  docs|trivial|full|diff;  commit_kind.sh deep <git diff args>  ->  yes|no;
# commit_kind.sh deep-files (paths on stdin)  ->  yes|no
# Also sourceable: commit_kind <sha>, is_deep_path <path>, diff_touches_deep <git diff args>.

is_deep_path() {
  case $1 in
    .claude/skills/verify/scripts/* | .claude/hooks/* | .claude/skills/review/*) return 0 ;;
    prototype/src/snatch/*/judge*.py | prototype/src/snatch/judge*.py) return 0 ;;
  esac
  return 1
}

diff_touches_deep() {
  local p
  while IFS= read -r p; do
    [[ -n $p ]] && is_deep_path "$p" && { echo yes; return 0; }
  done < <(git diff --name-only --no-renames "$@")
  echo no
}

deep_files() {
  local p
  while IFS= read -r p; do
    [[ -n $p ]] && is_deep_path "$p" && { echo yes; return 0; }
  done
  echo no
}

commit_kind() {
  local sha=$1 files=0 lines=0 add del path deep=0 docs=1 srcchange=0 st
  while IFS=$'\t' read -r add del path; do
    [[ -n $path ]] || continue
    files=$((files + 1))
    [[ $add == - ]] && add=0
    [[ $del == - ]] && del=0
    lines=$((lines + add + del))
    [[ $path == .scratch/* || $path == docs/* ]] || docs=0
    is_deep_path "$path" && deep=1
  done < <(git show --numstat --no-renames --format= "$sha")
  while IFS=$'\t' read -r st path; do
    [[ $st == [AD] && $path == prototype/src/* ]] && srcchange=1
  done < <(git show --name-status --no-renames --format= "$sha")
  if ((docs)); then echo docs
  elif ((files == 1 && lines <= 10 && !deep && !srcchange)); then echo trivial
  elif ((srcchange || files >= 4 || lines > 150 || deep)); then echo full
  else echo diff; fi
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  if [[ ${1:-} == deep ]]; then shift; diff_touches_deep "$@"
  elif [[ ${1:-} == deep-files ]]; then deep_files
  else commit_kind "${1:?usage: commit_kind.sh <sha> | deep <git diff args>}"; fi
fi
