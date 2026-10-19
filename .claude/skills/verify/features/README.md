# Feature map

Harness for all features: shell, from `prototype/`. Evidence goes to `.scratch/verify/`.

| Feature | File | Entry |
|---|---|---|
| Pipeline v2 stages on a clip (S-1, S0, S1, S4, side, S5; calibrate C3) | [../SKILL.md](../SKILL.md#drive) | `run_clip.sh` |
| Evidence: worst-frames sheets, publish to the PR, sweep after the PR closes | [../SKILL.md](../SKILL.md#evidence) | `publish_evidence.sh`, `sweep_evidence.sh` |
| Short test clips: T1 per commit, T1–T7 for milestones | [test-clips.md](test-clips.md) | `run_clip.sh vids/test/T1_*` |
| Unit tests and types | [tests.md](tests.md) | `pytest`, `pyright` |
