# Unit tests and types

## Sub-features
- `tests/` (16 files, 123 tests): angles, armbend, height, ladder, markers, overlay, person, phases, plate, pose, reps, signals, skeleton, spread, video, views
- pyright over the project (56 errors at f7ac11d)

## How to get to it (user POV)
Developer runs before committing.

## Driving it with the shell harness
`cd prototype && uv run pytest -q` -> `123 passed`; `uv run pyright`: main has 56 pre-existing errors; a change must not raise the count.
Proof: pass counts in output. Tests do not need clips or models.

## Gotchas
- Passing tests do not prove the pipeline on real video; also run `run_clip.sh`.
