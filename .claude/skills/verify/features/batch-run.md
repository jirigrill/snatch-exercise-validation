# Batch orchestration

## Sub-features
- `scripts/run_all.sh [vids_dir [clip…]]`: fills missing outputs for each clip, two lanes (pose on CoreML, plate on CPU)
- Logs: `out/run_all/<clip>.log`, `out/run_all/summary.log`

## How to get to it (user POV)
Analyst drops new clips in `vids/` and runs it once.

## Driving it with the shell harness
`cd prototype && scripts/run_all.sh <vids_dir> <clip…>` writes to `prototype/out/`. To verify without polluting, `bash -n scripts/run_all.sh` (syntax, allowed) and read `summary.log` of an earlier run. A real run only when the user asks; then tail `out/run_all/summary.log` for `ok`/`FAIL` lines.
Proof: every line `ok`, no `FAIL`; a second run starts with `0 clips` (idempotent).

## Gotchas
- Skips clips whose outputs all exist; never deletes.
- IMG_*.MOV in `vids/` are originals of renamed clips: skipped by the glob `2026*.MOV`.
