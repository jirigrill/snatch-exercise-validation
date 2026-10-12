#!/bin/bash
# Run the full pipeline (person -> pose -> plate -> analyze -> compare) on ONE clip
# into an evidence dir, then assert the outputs. Never touches prototype/out/.
# usage: .claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
#   default clip: vids/ladder/20261001_3_..._0deg_60fps.MOV (625 frames, ~50 s on an M4)
#   default root: <repo>/.scratch/verify/<UTC timestamp>   (gitignored, survives cleanup)
# Plate options follow scripts/run_all.sh: "ellipse" for 30deg/45deg names,
# "--radius 70:140" for 20261005_*/20261007_*_0deg_* clips.
# Exit 0 = OK, 1 = FAIL, 4 = XFAIL (a clip listed in EXPECTED_FAIL failed as expected).
set -e
root=$(cd "$(dirname "$0")/../../../.." && pwd)
clip=${1:-$root/vids/ladder/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg_60fps.MOV}
ev=${2:-$root/.scratch/verify/$(date -u +%Y%m%dT%H%M%SZ)}
c=$(basename "${clip%.MOV}")
out=$ev/$c
mkdir -p "$out"
cd "$root/prototype"
# Clips whose phase check is known to fail (prefix match). Keep in sync with SKILL.md.
EXPECTED_FAIL=(20261001_2_ T7_)  # standup, no snatch (ladder clip and its cut T7): phase finder has nothing to find
xfail=
for p in "${EXPECTED_FAIL[@]}"; do [[ $c == "$p"* ]] && xfail=1; done
fail() { echo "FAIL: $1"; exit 1; }
# Only the phase check may be an expected failure; crashes and missing files stay FAIL.
phase_fail() {
  if [[ -n $xfail ]]; then echo "XFAIL (expected): $1"; exit 4; fi
  fail "$1"
}
opts=()
src_stem=${c#T[0-9]_}  # test clips T<n>_<source stem>: same camera, same plate options
[[ $c == *30deg* || $c == *45deg* ]] && opts+=(ellipse)
[[ $src_stem == 20261005_* || ($src_stem == 20261007_* && $c == *_0deg_*) ]] && opts+=(--radius 70:140)
bar=; [[ $c == *_bar_* ]] && bar=1
log=$ev/$c.log
# Every step is cached in .scratch/verify/cache/<clip>/<step>-<key>/ (VERIFY_NO_CACHE=1
# forces reruns). A key covers the clip, the step's scripts, src/snatch and the key of
# the step it reads from, so a change upstream invalidates everything below it.
cache=$root/.scratch/verify/cache/$c
src=$(find src/snatch -type f -name '*.py' | sort | xargs cat | cat - uv.lock | shasum | cut -c1-16)
key() { { printf '%s\0' "$@"; cat "${scripts[@]}"; } | shasum | cut -c1-16; }
# step <name> <key> <outputs...> -- <command...>: restore outputs from cache or run and store.
step() {
  local name=$1 k=$2; shift 2
  local files=(); while [[ $1 != -- ]]; do files+=("$1"); shift; done; shift
  local d=$cache/$name-$k
  local f hit=
  if [[ -z $VERIFY_NO_CACHE && -f $d/.done ]]; then
    hit=1; for f in "${files[@]}"; do [ -e "$d/$f" ] || hit=; done
  fi
  if [[ -n $hit ]]; then
    cp -R "$d/." "$out/" && rm -f "$out/.done" && echo "$name: cache $k"; return
  fi
  "$@" || return 1
  # Store only a complete entry: an output missing after a run (e.g. no phase_sheet when no
  # rep is found) leaves the step uncached, so it reruns next time.
  for f in "${files[@]}"; do [ -e "$out/$f" ] || { echo "$name: not cached, missing $f"; return 0; }; done
  rm -rf "$d.tmp" && mkdir -p "$d.tmp" && cp -R "${files[@]/#/$out/}" "$d.tmp/" &&
    touch "$d.tmp/.done" && rm -rf "$d" && mv "$d.tmp" "$d" || return 1
}
clipid=$(stat -f '%z %m' "$clip")
scripts=(scripts/extract_person.py scripts/extract_pose.py); kpose=$(key "$clipid" "$src")
scripts=(scripts/track_plate.py); kplate=$(key "$clipid" "$src" "${opts[@]}")
scripts=(scripts/analyze.py scripts/compare_phases.py); kan=$(key "$clipid" "$src" "$kpose" "$kplate" "$bar")
{
  step pose "$kpose" person.npz raw_pose.npz -- \
    eval 'uv run python scripts/extract_person.py "$clip" "$out" && uv run python scripts/extract_pose.py "$clip" "$out"' &&
  { [[ -n $bar ]] || step plate "$kplate" plate.npz plate.csv plate_check.jpg bar_path.png -- \
    uv run python scripts/track_plate.py "$clip" "$out" "${opts[@]}"; } &&
  step analyze "$kan" angles.csv angles.png phases.json phases_v2.json phases_v1_v2.md \
    phase_sheet.jpg overlay.mp4 grabs -- \
    eval 'uv run python scripts/analyze.py "$clip" "$out" && { [[ -n $bar ]] || uv run python scripts/compare_phases.py "$out"; }'
} >"$log" 2>&1 || { tail -20 "$log"; fail "see $log"; }
need=(person.npz raw_pose.npz angles.csv phases.json overlay.mp4)
[[ -n $bar ]] || need+=(plate.npz plate_check.jpg phases_v2.json)
for f in "${need[@]}"; do [ -s "$out/$f" ] || fail "missing $out/$f"; done
python3 -I - "$out/phases.json" <<'PY' || phase_fail "phase check on $out/phases.json"
import json, sys
d = json.load(open(sys.argv[1]))
reps = d if isinstance(d, list) else d.get("reps", d)
assert reps, "no reps found"
print("reps:", len(reps), reps[0])
PY
[ -s "$out/phase_sheet.jpg" ] || fail "missing $out/phase_sheet.jpg"
[[ -n $xfail ]] && echo "XPASS: $c is in EXPECTED_FAIL but passed; remove it from the list"
echo "OK evidence: $out"
