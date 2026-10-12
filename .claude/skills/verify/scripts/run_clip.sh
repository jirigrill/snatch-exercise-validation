#!/bin/bash
# Drive pipeline v2 (prototype/scripts/pipeline.py) on ONE clip into an evidence dir and
# check it with check_pipeline.py. Never touches prototype/out/.
# usage: .claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
#   default clip: vids/test/T1_*.MOV
#   default root: <repo>/.scratch/verify/<UTC timestamp>   (gitignored, survives cleanup)
# Two runs on a fresh dir: every stage runs, then a rerun skips the hashed stages. The
# stage list comes from snatch.stages.STAGES, so a new stage is driven without editing
# this script; its content check goes in check_pipeline.py.
# A passing result is cached in .scratch/verify/cache/<clip>/<key>/. The key covers the
# clip (size + mtime), src/snatch, scripts/pipeline.py, uv.lock and these two scripts,
# so any change that could change the result reruns it. VERIFY_NO_CACHE=1 forces a run.
# Exit 0 = OK, 1 = FAIL.
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
clip=${1:-$(ls "$root"/vids/test/T1_*.MOV | head -1)}
clip=$(cd "$(dirname "$clip")" && pwd)/$(basename "$clip")
ev=${2:-$root/.scratch/verify/$(date -u +%Y%m%dT%H%M%SZ)}
mkdir -p "$ev" && ev=$(cd "$ev" && pwd)
c=$(basename "${clip%.MOV}")
out=$ev/$c
athletes=$ev/athletes
log=$ev/$c.log
cd "$root/prototype"
fail() { echo "FAIL: $1"; exit 1; }
rm -rf "$out" && : >"$log"
key=$( { stat -f '%z %m' "$clip"; find src/snatch -type f -name '*.py' | sort | xargs cat
         cat scripts/pipeline.py uv.lock "$here/run_clip.sh" "$here/check_pipeline.py"; } | shasum | cut -c1-16)
cache=$root/.scratch/verify/cache/$c/$key
if [[ -z $VERIFY_NO_CACHE && -f $cache/.done ]]; then
  cp -R "$cache/out" "$out" && cp "$cache/log" "$log"
  echo "cache $key (VERIFY_NO_CACHE=1 to rerun)" | tee -a "$log"
  grep -v '^==' "$cache/log" | grep -E '^(first|rerun|  )' || true
  echo "OK evidence: $out"
  exit 0
fi
# S0 stops without a skeleton (exit 2); a placeholder until C3 calibrate exists
mkdir -p "$athletes/verify"
[ -s "$athletes/verify/skeleton.json" ] || echo '{}' >"$athletes/verify/skeleton.json"
pipeline() {  # pipeline <run label> [pipeline.py options]
  local run=$1; shift
  echo "== $run" >>"$log"
  uv run python scripts/pipeline.py "$clip" --athlete verify --height 1.73 --out "$out" \
    --athletes "$athletes" "$@" >>"$log" 2>&1 || { tail -20 "$log"; fail "$run: pipeline.py exit $?, see $log"; }
  uv run python "$here/check_pipeline.py" "$out" "$run" | tee -a "$log"
  [[ ${PIPESTATUS[0]} == 0 ]] || fail "$run: check, see $log"
}
pipeline first
pipeline rerun
[[ -z $(git -C "$root" status --porcelain prototype/out) ]] || fail "stray writes in prototype/out"
rm -rf "$cache.tmp" && mkdir -p "$cache.tmp" && cp -R "$out" "$cache.tmp/out" && cp "$log" "$cache.tmp/log" &&
  touch "$cache.tmp/.done" && rm -rf "$cache" && mv "$cache.tmp" "$cache"
echo "OK evidence: $out"
