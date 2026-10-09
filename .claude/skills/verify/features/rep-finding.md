# Rep finding

## Sub-features
- Propose reps from the plate hub (fallback: sparse pose) -> out/reps_proposed.csv, out/reps_check/<clip>.png

## How to get to it (user POV)
Analyst runs it over a clip directory, then hand-corrects into `docs/reps.csv`.

## Driving it with the shell harness
`cd prototype && uv run python scripts/find_reps.py ../vids` reads existing `out/<clip>/plate.npz` and **writes `prototype/out/`**. For a proof, copy needed `out/<clip>` dirs to a scratch dir first or `git checkout -- prototype/out` / `git status` afterward and report what changed. Never write `docs/reps.csv`.
Proof: rep count per clip equals `<N>rep` in the clip name; reps_check png shows shaded lifts over the hub-height curve.

## Gotchas
- `docs/reps.csv` is hand-checked ground truth; the script never writes it.
- Outcome and fail cause are copied from the file name and marked unchecked.
