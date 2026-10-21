# Feature map

Harness for all features: shell, from `prototype/`. Evidence goes to `.scratch/verify/`.

| Feature | File | Entry |
|---|---|---|
| Pipeline v2 stages on a clip (S-1, S0, S1, S4, side, S5; calibrate C3) | [../SKILL.md](../SKILL.md#drive) | `run_clip.sh` |
| Evidence: main as baseline, output diff, review file, publish to the PR, sweep after the PR closes | [../SKILL.md](../SKILL.md#evidence) | `base_run.sh`, `diff_outputs.py`, `publish_evidence.sh` (+ `render_comment.py`), `sweep_evidence.sh` |
| What each stage does and what to look for in its images | [stage-guide.md](stage-guide.md) | one section per stage; add one with a new stage |
| Short test clips: T1 per commit, T1–T7 for milestones | [test-clips.md](test-clips.md) | `run_clip.sh vids/test/T1_*` |
| Unit tests and types | [tests.md](tests.md) | `pytest`, `pyright` |

## Blind marking strips

`scripts/mark_strips.py` writes contact sheets of raw clip frames (no pipeline output), each cell labelled with its frame index (same as the pipeline's, via `snatch.video.frames`), for marking phase borders blind. From `prototype/`: `uv run python ../.claude/skills/verify/scripts/mark_strips.py CLIP.MOV --start F --end F --step N --out DIR [--crop x0,y0,x1,y1] [--cols 4] [--rows 3] [--cell-width 480] [--times frame_times.npy]`. End is exclusive; sheets are `DIR/strip_<first>-<last>.jpg`, cells left to right, top to bottom.
