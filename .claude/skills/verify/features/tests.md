# Unit tests and types

## Sub-features
- `tests/`: unit tests per `CLAUDE.md` (exit codes, edge cases no clip covers, regressions)
- pyright over the project (baseline 20 errors)

## How to get to it (user POV)
Developer runs before committing.

## Driving it with the shell harness
`cd prototype && uv run pytest -q` -> all pass; `uv run pyright`: main has 20 pre-existing errors; a change must not raise the count.
Proof: pass counts in output. Tests do not need clips or models.

## Gotchas
- Passing tests do not prove the pipeline on real video; also run `run_clip.sh`.
