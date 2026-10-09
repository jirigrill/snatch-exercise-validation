# Rep finding

## Sub-features
- Propose reps from the plate hub (fallback: sparse pose) -> out/reps_proposed.csv, out/reps_check/<clip>.png

## How to get to it (user POV)
Analyst runs it over a clip directory, then checks the proposals by eye with `rep_sheets.py`.

## Driving it with the shell harness
`cd prototype && uv run python scripts/find_reps.py ../vids` reads existing `out/<clip>/plate.npz` and **writes `prototype/out/`**. For a proof, copy needed `out/<clip>` dirs to a scratch dir first or `git checkout -- prototype/out` / `git status` afterward and report what changed.
Proof: rep count per clip equals `<N>rep` in the clip name; reps_check png shows shaded lifts over the hub-height curve.

## Gotchas
- The proposals are not hand-checked; a checked rep list is deferred to the gate 1 set (#20).
- Outcome and fail cause are copied from the file name and marked unchecked.
