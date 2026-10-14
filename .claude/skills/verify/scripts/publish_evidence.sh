#!/bin/bash
# Publish a run_clip.sh evidence root to the open PR of the current branch.
# usage: .claude/skills/verify/scripts/publish_evidence.sh <evidence_root> "<review>"
#   review: what the shown images show, one line per image (markdown), put under the result;
#           name each image by its file stem and each frame of a <name>_worst.jpg by its number
#   DRY_RUN=1 prints the comment and pushes nothing
# Commits the root as <root name>/ to the branch evidence/pr-<n> (its own history, never
# merged), pushes it and comments on the PR: per clip ✅ / ❌ from the log's result line,
# the commit under test once, the run-state lines, the review, images at the top of the root
# (e.g. a screenshot.sh explainer, under "Explainer") and one link to the root's file tree,
# pinned to the evidence commit. Only the stages whose code changed vs the merge base with
# origin/main are shown, plus every stage after the first of them (stage_files.py show): their
# detail lines and images (the png/jpg outputs; of an mp4 its _sheet and _worst jpg, with the
# frames of its .worst); the clip's and the calibration's (calibrate_<T5>/). All stages when
# scripts/pipeline.py or uv.lock changed. SHOW_STAGES="S3 C3" adds stages by name (a changed
# sheet or check), SHOW_STAGES=all shows all. Fails before pushing when the review misses the
# file stem of a shown image or a frame of a shown .worst. The branch is deleted when the PR
# closes (.github/workflows/delete-evidence.yml); the comment text stays, its images and links break.
set -e
fail() { echo "FAIL: $1"; exit 1; }
[ -d "$1" ] && [ -n "$2" ] || fail 'usage: publish_evidence.sh <evidence_root> "<review of the frame sheets>"'
review=$2
ev=$(cd "$1" && pwd)
name=$(basename "$ev")
cd "$(dirname "$0")"
pr=$(gh pr view --json number -q .number 2>/dev/null) || pr=
[[ -n $pr || -n $DRY_RUN ]] || fail "no open PR for branch $(git rev-parse --abbrev-ref HEAD)"
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
# which stages to show (stage_files.py show), and the files of each
show=$(cd ../../../../prototype && uv run python "$PWD/../.claude/skills/verify/scripts/stage_files.py" show "$(git merge-base HEAD origin/main)" $SHOW_STAGES) || fail "stage_files.py show failed"
names() { awk -v k="$1" -v l="$2" '$1==k && $2==l {printf " %s", $3}' <<<"$show"; }
sa="$(names shown analyze) "; sc="$(names shown calibrate) "
allnames=$(awk '$1=="all" && !seen[$3]++ {printf " %s", $3}' <<<"$show")
shownames=$(awk '$1=="shown" && !seen[$3]++ {printf " %s", $3}' <<<"$show")
list() { printf '%s\n' "$@" | paste -sd ',' - | sed 's/,/, /g'; }
unchanged=$(for n in $allnames; do [[ " $shownames " == *" $n "* ]] || echo "$n"; done)
calonly=$(for n in $(names all calibrate); do [[ " $(names all analyze) " == *" $n "* ]] || echo "$n"; done)
calshow=
for n in $calonly S-1 S1 S2; do [[ $sc == *" $n "* ]] && calshow=1; done
shown_images() {  # shown_images <list> <dir>: the shown stages' images that exist in <dir>, relative to it
  awk -v l="$1" '$1=="shown" && $2==l {for (i = 4; i <= NF; i++) print $i}' <<<"$show" | while read -r o; do
    case $o in
      *.jpg|*.png) [ -f "$2/$o" ] && echo "$o" ;;
      *.mp4) for x in "${o%.mp4}_sheet.jpg" "${o%.mp4}_worst.jpg"; do [ -f "$2/$x" ] && echo "$x"; done ;;
    esac
  done
  return 0
}
worst_frames() {  # worst_frames <dir> <x_worst.jpg>: the frame numbers of its .worst
  head -1 "$1/${2%_worst.jpg}.worst"
}
render_images() {  # render_images <dir> <url dir> <list>
  shown_images "$3" "$1" | while read -r x; do
    echo "![$x]($2/$x?raw=true)"
    case $x in *_worst.jpg)
      w=${x%_worst.jpg}.worst
      echo "worst frames (from $(basename "$w")): $(for n in $(worst_frames "$1" "$x"); do printf 'f%s ' "$n"; done)— $(sed -n 2p "$1/$w")" ;;
    esac
  done
}
# the review must cover every shown image and use the frame numbers of its .worst
unmentioned() {
  for dir in "$ev"/*/; do
    d=$(basename "$dir"); case $d in athletes) continue ;; calibrate_*) l=calibrate ;; *) l=analyze ;; esac
    shown_images "$l" "$dir" | while read -r x; do
      s=$(basename "${x%.*}")
      grep -qF "$s" <<<"$review" || echo "$s"
      case $x in *_worst.jpg) for n in $(worst_frames "$dir" "$x"); do grep -qE "(^|[^0-9])$n([^0-9]|$)" <<<"$review" || echo "frame $n of $s"; done ;; esac
    done
  done
}
missing=$(unmentioned | sort -u | paste -sd ',' - | sed 's/,/, /g')
[ -z "$missing" ] || fail "the review does not mention: $missing"
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
  for log in "$ev"/*.log; do head -1 "$log"; break; done
  echo
  if [[ -n $shownames ]]; then
    echo "Shown: $(list $shownames).${unchanged:+ Unchanged vs main (code untouched, outputs in Files): $(list $unchanged).}"
  else
    echo "No stage code changed vs main; all outputs as on main (see Files)."
  fi
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
    echo "### $(result "$log") ${c%%_*}"
    echo '```'
    awk -v ga="$sa" -v gc="$sc" -v calshow="$calshow" '
      /^  [^ ]/ { n = $1; sub(/:$/, "", n)
                  if (ctx == "c") { if (calshow && index(gc, " " n " ")) print } else if (index(ga, " " n " ")) print; next }
      /^(\(cached\) )?calibrate/ { sub(/^\(cached\) /, ""); ctx = "c"; if (calshow) print; next }
      /^(first|rerun)/ { ctx = "a"; print; next }
      /^retry/ { print }' "$log"
    echo '```'
    echo
    render_images "$ev/$c" "$url/$c" analyze
  done
  for d in "$ev"/calibrate_*/; do
    [ -d "$d" ] || continue
    d=$(basename "$d")
    imgs=$(render_images "$ev/$d" "$url/$d" calibrate)
    [[ -n $imgs ]] || continue
    echo
    echo "### calibration"
    echo
    echo "$imgs"
  done
  echo
  echo "Files: https://github.com/$repo/tree/$commit/$name (branch \`$branch\`, deleted when this PR closes)"
} >"$body"
if [[ -n $DRY_RUN ]]; then cat "$body"; exit 0; fi
gh pr comment "$pr" --body-file "$body"
