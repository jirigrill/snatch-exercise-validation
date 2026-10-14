#!/bin/bash
# Drive pipeline v2 (prototype/scripts/pipeline.py) on ONE clip into an evidence dir and
# check it with check_pipeline.py. Never touches prototype/out/.
# usage: .claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
#   default clip: vids/test/T1_*.MOV
#   default root: <repo>/.scratch/verify/<branch>__<clip id>__<short sha>[-dirty]
#                 (gitignored; sweep_evidence.sh deletes it once the branch has no open PR)
# First it calibrates the athlete `verify` on the bar-only T5 (pipeline.py --calibrate, C3)
# into <root>/calibrate_<T5>/ and <root>/athletes/, then runs the clip with that skeleton.
# The calibration is cached in .scratch/verify/cache/calibrate/<key>/; the key covers T5 and
# only the code the calibration runs (stage_files.py calibrate), so a commit to a later
# stage reuses it. A root whose calibration has another key recalibrates.
# Two runs on a fresh dir: every stage runs, then a rerun skips the hashed stages. The
# stage list comes from snatch.stages.STAGES, so a new stage is driven without editing
# this script; its content check goes in check_pipeline.py. A clip that stops by design
# is in expected_stop below.
# Stage reuse (stage_cache.py): before the first run, every stage whose exact key (its
# code and imports, input contents, params, pipeline.py, uv.lock, models, macOS) has a
# cached output is restored, in pipeline order up to the first miss; pipeline.py reports
# those `skipped`, check_pipeline.py --reused expects that and still checks their content.
# After a passing run each stage is stored; a fresh run (VERIFY_NO_CACHE=1) of a stage
# whose key is cached must give the same content, else FAIL (the key misses something).
# A passing result is cached in .scratch/verify/cache/<clip>/<key>/. The key covers the
# clip and T5 (size + mtime), src/snatch, scripts/pipeline.py, uv.lock and these scripts,
# so any change that could change the result reruns it. VERIFY_NO_CACHE=1 forces a run
# (all three caches: whole result, stages, calibration).
# Every overlays/*.mp4 gets a frame sheet overlays/<name>_sheet.jpg (8 frames, evenly spaced)
# and, where check_pipeline.py wrote overlays/<name>.worst, <name>_worst.jpg (the frames the
# stage scores worst on). The log starts with the commit under test and ends with the
# result line (OK evidence: … or FAIL: …).
# One run at a time (lock .scratch/verify/.run_clip.lock): a second one fails at once.
# Publish an evidence root to the branch's PR with publish_evidence.sh.
# Exit 0 = OK, 1 = FAIL.
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
clip=${1:-$(ls "$root"/vids/test/T1_*.MOV | head -1)}
clip=$(cd "$(dirname "$clip")" && pwd)/$(basename "$clip")
c=$(basename "${clip%.MOV}")
id=${c%%_*}
branch=$(git -C "$root" rev-parse --abbrev-ref HEAD)
dirty=$(git -C "$root" status --porcelain -- prototype .claude/skills/verify | wc -l | tr -d ' ')
ev=${2:-$root/.scratch/verify/${branch//\//-}__${id}__$(git -C "$root" rev-parse --short HEAD)$([[ $dirty == 0 ]] || echo -dirty)}
lock=$root/.scratch/verify/.run_clip.lock
mkdir -p "$root/.scratch/verify"
if ! mkdir "$lock" 2>/dev/null; then
  pid=$(cat "$lock/pid" 2>/dev/null || true)
  if [[ -n $pid ]] && kill -0 "$pid" 2>/dev/null; then
    echo "FAIL: run_clip.sh already running (pid $pid: $(cat "$lock/what")); wait for it or kill it"; exit 1
  fi
  rm -rf "$lock" && mkdir "$lock"
fi
echo $$ >"$lock/pid" && echo "$c -> $ev" >"$lock/what"
trap 'rm -rf "$lock"' EXIT
mkdir -p "$ev" && ev=$(cd "$ev" && pwd)
bar=$(ls "$root"/vids/test/T5_*.MOV | head -1)
cb=$(basename "${bar%.MOV}")
out=$ev/$c
calout=$ev/calibrate_$cb
athletes=$ev/athletes
log=$ev/$c.log
cd "$root/prototype"
fail() { echo "FAIL: $1" | tee -a "$log"; exit 1; }
expected_stop() {  # expected_stop <clip id>: "<exit> <stage>" when the clip stops by design
  case $1 in
    T4) echo "2 side" ;;  # faces left; T5 calibrates the right side only
    T5) echo "6 S3" ;;  # bar-only clip given to analyze: no plate (hough_share < 0.5) -> exit 6
  esac
}
rm -rf "$out"
echo "commit $(git rev-parse --short HEAD) $branch, dirty files: $dirty" >"$log"
key=$( { stat -f '%z %m' "$clip" "$bar"; find src/snatch -type f -name '*.py' | sort | xargs cat
         cat scripts/pipeline.py uv.lock "$here"/*.sh "$here"/*.py; } | shasum | cut -c1-16)
cache=$root/.scratch/verify/cache/$c/$key
if [[ -z $VERIFY_NO_CACHE && -f $cache/.done ]]; then
  rm -rf "$calout" "$athletes/verify"
  cp -R "$cache/out" "$out" && cp -R "$cache/calout" "$calout" && mkdir -p "$athletes" &&
    cp -R "$cache/athletes/verify" "$athletes/" && tail -n +2 "$cache/log" >>"$log"
  echo "cache $key (VERIFY_NO_CACHE=1 to rerun)" | tee -a "$log"
  grep -v '^==' "$cache/log" | grep -E '^(calibrate|first|rerun|retry|  )' || true
  echo "OK evidence: $out (root $ev)" | tee -a "$log"
  exit 0
fi
pipeline() {  # pipeline <run label> <check run> <out> [pipeline.py options]: clip or --calibrate bar
  local run=$1 check=$2 o=$3; shift 3
  local opts=() want_rc=0 rc try reused=$REUSED
  if [[ $1 == --calibrate ]]; then
    opts=(--calibrate "$athletes/verify/skeleton.json")
  else
    local s; s=$(expected_stop "$id")
    [[ -z $s ]] || { want_rc=${s%% *}; opts=(--stop "${s#* }"); }
  fi
  for try in 1 2; do
    echo "== $run" >>"$log"
    rc=0
    uv run python scripts/pipeline.py "$@" --athlete verify --height 1.73 --out "$o" \
      --athletes "$athletes" >>"$log" 2>&1 || rc=$?
    # detector crash at interpreter exit (.scratch/plan notes): rerun once from a clean dir
    [[ $rc != 0 && $try == 1 ]] && tail -3 "$log" | grep -q 'recursive_mutex lock failed' || break
    echo "retry $run: pipeline.py exit $rc, recursive_mutex crash at exit" | tee -a "$log"
    [[ $check == first ]] && rm -rf "$o" && { [[ $1 != --calibrate ]] || rm -rf "$athletes/verify"; } && reused=
  done
  [[ $rc == "$want_rc" ]] || { tail -20 "$log"; fail "$run: pipeline.py exit $rc (expected $want_rc), see $log"; }
  [[ $check == first && -n $reused && $1 != --calibrate ]] && opts+=(--reused "$reused")
  uv run python "$here/check_pipeline.py" "$o" "$check" "${opts[@]}" | sed "s/^$check:/$run:/" | tee -a "$log"
  [[ ${PIPESTATUS[0]} == 0 ]] || fail "$run: check, see $log"
}
frames() { ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$1"; }
sheet() {  # sheet <mp4>: 8 evenly spaced frames, 4 x 2, 360 px high
  local n; n=$(frames "$1")
  ffmpeg -v error -y -i "$1" -vf "select='not(mod(n\,$(( n / 8 > 0 ? n / 8 : 1 ))))',scale=-2:360,tile=4x2" \
    -frames:v 1 "${1%.mp4}_sheet.jpg" || fail "frame sheet of $1"
}
worst() {  # worst <mp4>: the clip frames in <name>.worst (check_pipeline.py), 4 x 1, 360 px high
  local w=${1%.mp4}.worst n nc sel= f
  [ -s "$w" ] || return 0
  n=$(frames "$1")
  nc=$(sed -n 's/.*"n_frames": *\([0-9]*\).*/\1/p' "$(dirname "$1")/../clip.json")
  for f in $(head -1 "$w"); do sel+="${sel:++}eq(n\,$(( f * n / nc )))"; done
  ffmpeg -v error -y -i "$1" -vf "select='$sel',scale=-2:360,tile=4x1" -frames:v 1 "${1%.mp4}_worst.jpg" ||
    fail "worst-frames sheet of $1"
}
calkey=$( { stat -f '%z %m' "$bar"; uv run python "$here/stage_files.py" calibrate | xargs cat
            cat scripts/pipeline.py uv.lock "$here"/*.sh "$here"/*.py; } | shasum | cut -c1-16)
calcache=$root/.scratch/verify/cache/calibrate/$calkey
if [[ $(cat "$calout/.key" 2>/dev/null) != "$calkey" ]]; then
  rm -rf "$calout" "$athletes/verify"
  if [[ -z $VERIFY_NO_CACHE && -f $calcache/.done ]]; then
    cp -R "$calcache/calout" "$calout" && mkdir -p "$athletes" && cp -R "$calcache/athletes/verify" "$athletes/"
    grep -E '^(calibrate|retry|  )' "$calcache/log" | sed '1s/^/(cached) /' | tee -a "$log"
  else
    pipeline calibrate first "$calout" --calibrate "$bar"
    rm -rf "$calcache.tmp" && mkdir -p "$calcache.tmp/athletes" && cp -R "$calout" "$calcache.tmp/calout" &&
      cp -R "$athletes/verify" "$calcache.tmp/athletes/" && grep -A20 '^calibrate: ' "$log" | grep -v '^==' >"$calcache.tmp/log" &&
      touch "$calcache.tmp/.done" && rm -rf "$calcache" && mv "$calcache.tmp" "$calcache"
  fi
  echo "$calkey" >"$calout/.key"
fi
pipeline "calibrate rerun" rerun "$calout" --calibrate "$bar"
stages=$root/.scratch/verify/cache/stage/$c
REUSED=
if [[ -z $VERIFY_NO_CACHE ]]; then
  REUSED=$(uv run python "$here/stage_cache.py" restore "$out" "$athletes" "$clip" "$stages") ||
    fail "stage cache restore, see above"
  [[ -z $REUSED ]] || echo "reused (stage cache): $REUSED" | tee -a "$log"
fi
pipeline first first "$out" "$clip"
uv run python "$here/stage_cache.py" store "$out" "$athletes" "$clip" "$stages" | tee -a "$log"
[[ ${PIPESTATUS[0]} == 0 ]] || fail "stage cache store, see $log"
pipeline rerun rerun "$out" "$clip"
for v in "$calout"/overlays/*.mp4 "$out"/overlays/*.mp4; do if [ -e "$v" ]; then sheet "$v"; worst "$v"; fi; done
[[ -z $(git -C "$root" status --porcelain prototype/out) ]] || fail "stray writes in prototype/out"
rm -rf "$cache.tmp" && mkdir -p "$cache.tmp" && cp -R "$out" "$cache.tmp/out" && cp -R "$calout" "$cache.tmp/calout" &&
  mkdir -p "$cache.tmp/athletes" && cp -R "$athletes/verify" "$cache.tmp/athletes/" && cp "$log" "$cache.tmp/log" &&
  touch "$cache.tmp/.done" && rm -rf "$cache" && mv "$cache.tmp" "$cache"
echo "OK evidence: $out (root $ev)" | tee -a "$log"
