#!/bin/bash
# Fill in missing pipeline outputs (⓪–④) for the clips in vids/; nothing is deleted.
#
# usage: cd prototype && scripts/run_all.sh
# logs:  out/run_all/<clip>.log (one per clip), out/run_all/summary.log (one line per step)
#
# A step runs only if its output is missing (or an earlier step was just rerun):
# ⓪ person.npz, ① raw_pose.npz, ② plate_check.jpg, ③ phase_sheet.jpg, ④ phases_v2.json.
# Clips with every output except person.npz are complete and skipped. IMG_*.MOV are
# the original copies of renamed clips (docs/clip-log.md) and are skipped.
# Lane 1 runs ⓪ then ① (detector on the CPU, pose on CoreML); lane 2 runs ② at the
# same time. ③ and ④ run once both lanes are done. A failed step is logged and the
# run carries on. Plate options come from the clip name: "ellipse" for ±30° views,
# "--radius 70:140" for 2026-10-05.

cd "$(dirname "$0")/.." || exit 1
logs=out/run_all
mkdir -p "$logs"

step() {  # step <clip> <label> <command…>
  local clip=$1 label=$2 t0=$SECONDS
  shift 2
  echo "=== $label: $*" >>"$logs/$clip.log"
  if "$@" >>"$logs/$clip.log" 2>&1; then
    echo "$(date +%T) ok   $clip $label $((SECONDS - t0))s" >>"$logs/summary.log"
  else
    echo "$(date +%T) FAIL $clip $label $((SECONDS - t0))s" >>"$logs/summary.log"
  fi
}

missing() {  # missing <clip> <file…>: true if any file is absent
  local f
  for f in "${@:2}"; do [ -e "out/$1/$f" ] || return 0; done
  return 1
}

clips=()
for f in ../vids/2026*.MOV; do
  c=$(basename "${f%.MOV}")
  missing "$c" raw_pose.npz plate_check.jpg phase_sheet.jpg phases_v2.json && clips+=("$c")
done
echo "$(date +%T) start: ${#clips[@]} clips: ${clips[*]}" >>"$logs/summary.log"

lane1() {
  for c in "${clips[@]}"; do
    missing "$c" person.npz &&
      step "$c" person uv run python scripts/extract_person.py "../vids/$c.MOV" "out/$c"
    missing "$c" raw_pose.npz && touch "out/$c/.rerun_pose" &&
      step "$c" pose uv run python scripts/extract_pose.py "../vids/$c.MOV" "out/$c"
  done
}

lane2() {
  for c in "${clips[@]}"; do
    [[ $c == *_bar_* ]] && continue  # bar only, no plate to track
    opts=()
    [[ $c == *30deg* ]] && opts+=(ellipse)
    [[ $c == 20261005_* ]] && opts+=(--radius 70:140)
    missing "$c" plate_check.jpg && touch "out/$c/.rerun_plate" &&
      step "$c" plate uv run python scripts/track_plate.py "../vids/$c.MOV" "out/$c" "${opts[@]}"
  done
}

lane1 &
lane2 &
wait

for c in "${clips[@]}"; do
  opts=()
  [[ $c == 20261001_5_* ]] && opts+=(spread)
  if missing "$c" phase_sheet.jpg || [ -e "out/$c/.rerun_pose" ] || [ -e "out/$c/.rerun_plate" ]; then
    step "$c" analyze uv run python scripts/analyze.py "../vids/$c.MOV" "out/$c" "${opts[@]}"
  fi
  if missing "$c" phases_v2.json || [ -e "out/$c/.rerun_pose" ] || [ -e "out/$c/.rerun_plate" ]; then
    step "$c" compare uv run python scripts/compare_phases.py "out/$c"
  fi
  rm -f "out/$c/.rerun_pose" "out/$c/.rerun_plate"
done
echo "$(date +%T) done" >>"$logs/summary.log"
