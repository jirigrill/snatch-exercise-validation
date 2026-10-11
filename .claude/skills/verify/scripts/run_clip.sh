#!/bin/bash
# Run the full pipeline (person -> pose -> plate -> analyze -> compare) on ONE clip
# into an evidence dir, then assert the outputs. Never touches prototype/out/.
# usage: .claude/skills/verify/scripts/run_clip.sh [clip.MOV] [evidence_root]
#   default clip: vids/ladder/20261001_3_..._0deg_60fps.MOV (625 frames, ~50 s on an M4)
#   default root: <repo>/.scratch/verify/<UTC timestamp>   (gitignored, survives cleanup)
# Plate options follow scripts/run_all.sh: "ellipse" for 30deg/45deg names,
# "--radius 70:140" for 20261005_*/20261007_*_0deg_* clips.
set -e
root=$(cd "$(dirname "$0")/../../../.." && pwd)
clip=${1:-$root/vids/ladder/20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg_60fps.MOV}
ev=${2:-$root/.scratch/verify/$(date -u +%Y%m%dT%H%M%SZ)}
c=$(basename "${clip%.MOV}")
out=$ev/$c
mkdir -p "$out"
cd "$root/prototype"
opts=()
[[ $c == *30deg* || $c == *45deg* ]] && opts+=(ellipse)
[[ $c == 20261005_* || ($c == 20261007_* && $c == *_0deg_*) ]] && opts+=(--radius 70:140)
log=$ev/$c.log
# person+pose are the slow steps: reuse them from a shared cache while the clip
# and the person/pose code are unchanged (VERIFY_NO_CACHE=1 forces a rerun).
cache=$root/.scratch/verify/cache/$c
key=$({ stat -f '%z %m' "$clip"; cat src/snatch/person.py src/snatch/pose.py src/snatch/video.py \
  scripts/extract_person.py scripts/extract_pose.py; } | shasum | cut -c1-16)
{
  if [[ -z $VERIFY_NO_CACHE && -s $cache/$key/raw_pose.npz ]]; then
    cp "$cache/$key/person.npz" "$cache/$key/raw_pose.npz" "$out/" && echo "person+pose: cache $key"
  else
    uv run python scripts/extract_person.py "$clip" "$out"
    uv run python scripts/extract_pose.py "$clip" "$out"
    mkdir -p "$cache/$key" && cp "$out/person.npz" "$out/raw_pose.npz" "$cache/$key/"
  fi
  [[ $c == *_bar_* ]] || uv run python scripts/track_plate.py "$clip" "$out" "${opts[@]}"
  uv run python scripts/analyze.py "$clip" "$out"
  [[ $c == *_bar_* ]] || uv run python scripts/compare_phases.py "$out"
} >"$log" 2>&1 || { echo "FAIL: see $log"; tail -20 "$log"; exit 1; }
need=(person.npz raw_pose.npz angles.csv phases.json phase_sheet.jpg overlay.mp4)
[[ $c == *_bar_* ]] || need+=(plate.npz plate_check.jpg phases_v2.json)
for f in "${need[@]}"; do [ -s "$out/$f" ] || { echo "FAIL: missing $out/$f"; exit 1; }; done
python3 -I - "$out/phases.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
reps = d if isinstance(d, list) else d.get("reps", d)
assert reps, "no reps found"
print("reps:", len(reps), reps[0])
PY
echo "OK evidence: $out"
