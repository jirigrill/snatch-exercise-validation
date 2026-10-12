# Feature map

Harness for all features: shell, from `prototype/`, `uv run python scripts/<x>.py`. Evidence goes to `.scratch/verify/`. Unless noted, a run on `vids/ladder/*_60fps.MOV` is enough.

| Feature | File | Entry |
|---|---|---|
| Pipeline v2 stages on a clip (S-1, S0, S1 so far) | [../SKILL.md](../SKILL.md#drive) | `run_clip.sh` |
| Pose + phases from a clip (old scripts) | [pose-and-phases.md](pose-and-phases.md) | `extract_person.py` … `analyze.py` |
| Plate and bar-path tracking | [plate-tracking.md](plate-tracking.md) | `track_plate.py` |
| Rep finding | [rep-finding.md](rep-finding.md) | `find_reps.py` |
| Spike analyses (arm bend, body height, camera views, knee skeleton) | [spike-analyses.md](spike-analyses.md) | `arm_bend.py`, `body_height.py`, `d1_views.py`, `skeleton_validate.py` |
| Batch orchestration | [batch-run.md](batch-run.md) | `run_all.sh` |
| Short test clips T1–T7 for per-commit / per-PR runs | [test-clips.md](test-clips.md) | `run_clip.sh vids/test/T1_*` |
| Unit tests and types | [tests.md](tests.md) | `pytest`, `pyright` |
