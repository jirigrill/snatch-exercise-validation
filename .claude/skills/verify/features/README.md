# Feature map

Harness for all features: shell, from `prototype/`. Evidence goes to `.scratch/verify/`.

| Feature | File | Entry |
|---|---|---|
| Pipeline v2 stages on a clip (S-1, S0, S1, S4, side, S5; calibrate C3) | [../SKILL.md](../SKILL.md#drive) | `run_clip.sh` |
| Evidence: main as baseline, output diff, review file, publish to the PR, sweep after the PR closes | [../SKILL.md](../SKILL.md#evidence) | `base_run.sh`, `diff_outputs.py`, `publish_evidence.sh` (+ `render_comment.py`), `sweep_evidence.sh` |
| What each stage does and what to look for in its images | [stage-guide.md](stage-guide.md) | one section per stage; add one with a new stage |
| Short test clips: T1 per commit, T1–T7 for milestones | [test-clips.md](test-clips.md) | `run_clip.sh vids/test/T1_*` |
| Unit tests and types | [tests.md](tests.md) | `pytest`, `pyright` |
