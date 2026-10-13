#!/bin/bash
# Drive pipeline v2 (prototype/scripts/pipeline.py) on ONE clip into an evidence dir and
# check it with check_pipeline.py. Never touches prototype/out/.
# usage: .claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
#   default clip: vids/test/T1_*.MOV
# First it calibrates the athlete `verify` on the bar-only T5 (pipeline.py --calibrate, C3)
# into <root>/calibrate_<T5>/ and <root>/athletes/ (once per root: a root that has it only
# reruns it, expecting every hashed stage skipped), then runs the clip with that skeleton.
#   default root: <repo>/.scratch/verify/<UTC timestamp>   (gitignored, survives cleanup)
# Two runs on a fresh dir: every stage runs, then a rerun skips the hashed stages. The
# stage list comes from snatch.stages.STAGES, so a new stage is driven without editing
# this script; its content check goes in check_pipeline.py.
# A passing result is cached in .scratch/verify/cache/<clip>/<key>/. The key covers the
# clip and T5 (size + mtime), src/snatch, scripts/pipeline.py, uv.lock and these two scripts,
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
bar=$(ls "$root"/vids/test/T5_*.MOV | head -1)
c=$(basename "${clip%.MOV}")
cb=$(basename "${bar%.MOV}")
out=$ev/$c
calout=$ev/calibrate_$cb
athletes=$ev/athletes
log=$ev/$c.log
cd "$root/prototype"
fail() { echo "FAIL: $1" | tee -a "$log"; exit 1; }
rm -rf "$out"
echo "commit $(git rev-parse --short HEAD) $(git rev-parse --abbrev-ref HEAD), dirty files: $(git -C "$root" status --porcelain | wc -l | tr -d ' ')" >"$log"
key=$( { stat -f '%z %m' "$clip" "$bar"; find src/snatch -type f -name '*.py' | sort | xargs cat
         cat scripts/pipeline.py uv.lock "$here/run_clip.sh" "$here/check_pipeline.py"; } | shasum | cut -c1-16)
cache=$root/.scratch/verify/cache/$c/$key
if [[ -z $VERIFY_NO_CACHE && -f $cache/.done ]]; then
  cp -R "$cache/out" "$out" && { [ -e "$calout" ] || cp -R "$cache/calout" "$calout"; } && mkdir -p "$athletes" &&
    { [ -e "$athletes/verify" ] || cp -R "$cache/athletes/verify" "$athletes/"; } && tail -n +2 "$cache/log" >>"$log"
  echo "cache $key (VERIFY_NO_CACHE=1 to rerun)" | tee -a "$log"
  grep -v '^==' "$cache/log" | grep -E '^(calibrate|first|rerun|  )' || true
  echo "OK evidence: $out" | tee -a "$log"
  exit 0
fi
pipeline() {  # pipeline <run label> <check run> <out> [pipeline.py options]: clip or --calibrate bar
  local run=$1 check=$2 o=$3; shift 3
  local cal=(); [[ $1 == --calibrate ]] && cal=(--calibrate "$athletes/verify/skeleton.json")
  echo "== $run" >>"$log"
  uv run python scripts/pipeline.py "$@" --athlete verify --height 1.73 --out "$o" \
    --athletes "$athletes" >>"$log" 2>&1 || { tail -20 "$log"; fail "$run: pipeline.py exit $?, see $log"; }
  uv run python "$here/check_pipeline.py" "$o" "$check" "${cal[@]}" | sed "s/^$check:/$run:/" | tee -a "$log"
  [[ ${PIPESTATUS[0]} == 0 ]] || fail "$run: check, see $log"
}
sheet() {  # sheet <mp4>: 8 evenly spaced frames, 4 x 2, 360 px high
  local n; n=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$1")
  ffmpeg -v error -y -i "$1" -vf "select='not(mod(n\,$(( n / 8 > 0 ? n / 8 : 1 ))))',scale=-2:360,tile=4x2" \
    -frames:v 1 "${1%.mp4}_sheet.jpg" || fail "frame sheet of $1"
}
[ -f "$calout/C3.meta.json" ] || { rm -rf "$calout" "$athletes/verify"; pipeline calibrate first "$calout" --calibrate "$bar"; }
pipeline "calibrate rerun" rerun "$calout" --calibrate "$bar"
pipeline first first "$out" "$clip"
pipeline rerun rerun "$out" "$clip"
for v in "$calout"/overlays/*.mp4 "$out"/overlays/*.mp4; do if [ -e "$v" ]; then sheet "$v"; fi; done
[[ -z $(git -C "$root" status --porcelain prototype/out) ]] || fail "stray writes in prototype/out"
rm -rf "$cache.tmp" && mkdir -p "$cache.tmp" && cp -R "$out" "$cache.tmp/out" && cp -R "$calout" "$cache.tmp/calout" &&
  mkdir -p "$cache.tmp/athletes" && cp -R "$athletes/verify" "$cache.tmp/athletes/" && cp "$log" "$cache.tmp/log" &&
  touch "$cache.tmp/.done" && rm -rf "$cache" && mv "$cache.tmp" "$cache"
echo "OK evidence: $out" | tee -a "$log"
