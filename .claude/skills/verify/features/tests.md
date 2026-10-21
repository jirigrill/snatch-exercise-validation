# Unit tests and types

## Sub-features
- `tests/`: unit tests per `CLAUDE.md` (exit codes, edge cases no clip covers, regressions)
- pyright over the project (0 errors)

## How to get to it (user POV)
Developer runs before committing.

## Driving it with the shell harness
`cd prototype && uv run pytest -q` -> all pass; `uv run pyright` -> 0 errors (main is clean; any error fails).
Proof: pass counts in output. Tests do not need clips or models.

## Gotchas
- Passing tests do not prove the pipeline on real video; also run `run_clip.sh`.
