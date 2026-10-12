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
# Every overlays/*.mp4 gets a frame sheet overlays/<name>_sheet.jpg (8 frames, evenly spaced),
# so the result can be checked as an image. The log starts with the commit under test and
# ends with the result line (OK evidence: … or FAIL: …).
# Publish an evidence root to the branch's PR with publish_evidence.sh.
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
fail() { echo "FAIL: $1" | tee -a "$log"; exit 1; }
rm -rf "$out"
echo "commit $(git rev-parse --short HEAD) $(git rev-parse --abbrev-ref HEAD), dirty files: $(git -C "$root" status --porcelain | wc -l | tr -d ' ')" >"$log"
key=$( { stat -f '%z %m' "$clip"; find src/snatch -type f -name '*.py' | sort | xargs cat
         cat scripts/pipeline.py uv.lock "$here/run_clip.sh" "$here/check_pipeline.py"; } | shasum | cut -c1-16)
cache=$root/.scratch/verify/cache/$c/$key
if [[ -z $VERIFY_NO_CACHE && -f $cache/.done ]]; then
  cp -R "$cache/out" "$out" && tail -n +2 "$cache/log" >>"$log"
  echo "cache $key (VERIFY_NO_CACHE=1 to rerun)" | tee -a "$log"
  grep -v '^==' "$cache/log" | grep -E '^(first|rerun|  )' || true
  echo "OK evidence: $out" | tee -a "$log"
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
sheet() {  # sheet <mp4>: 8 evenly spaced frames, 4 x 2, 360 px high
  local n; n=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$1")
  ffmpeg -v error -y -i "$1" -vf "select='not(mod(n\,$(( n / 8 > 0 ? n / 8 : 1 ))))',scale=-2:360,tile=4x2" \
    -frames:v 1 "${1%.mp4}_sheet.jpg" || fail "frame sheet of $1"
}
pipeline first
pipeline rerun
for v in "$out"/overlays/*.mp4; do if [ -e "$v" ]; then sheet "$v"; fi; done
[[ -z $(git -C "$root" status --porcelain prototype/out) ]] || fail "stray writes in prototype/out"
rm -rf "$cache.tmp" && mkdir -p "$cache.tmp" && cp -R "$out" "$cache.tmp/out" && cp "$log" "$cache.tmp/log" &&
  touch "$cache.tmp/.done" && rm -rf "$cache" && mv "$cache.tmp" "$cache"
echo "OK evidence: $out" | tee -a "$log"
