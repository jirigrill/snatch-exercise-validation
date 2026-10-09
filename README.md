# snatch-exercise-validation

Validation, not a product. The question: can one phone video of a snatch tell a lifter why a lift failed, well enough to build a subscription app on it? The answer goes in [`VERDICT.md`](VERDICT.md) (GO / NO-GO / CONDITIONAL-GO), and it is not reached yet.

**Where are we?** Read [`docs/STATUS.md`](docs/STATUS.md). It lists the two tests that decide the verdict, their pass rules, every ticket with its state, and the next step.

## Map

| Path | What |
|---|---|
| `VERDICT.md` | The final verdict, once #10 is written |
| `docs/STATUS.md` | Plan, pass rules, ticket states, next step |
| `docs/README.md` | Index of everything under `docs/` |
| `docs/research/` | Market and feasibility research (tickets #1–#8) and the later design notes |
| `docs/results/` | One file per measured result, with its bottom line first |
| `docs/recording-protocol.md` | How clips are filmed, and the gate 1 rule |
| `docs/clip-log.md` | Every clip, its role and what is wrong with it |
| `prototype/` | The pipeline (Python, uv): video → pose → plate → angles → phases. See `prototype/README.md` |
| `tools/check_status.py` | Checks `docs/STATUS.md` against GitHub issue states |
| `vids/` | Original clips. Gitignored, not in a clone |

## Run

```
cd prototype && uv sync && uv run pytest -q
```

The full pipeline needs the clips in `vids/` and takes about 50 s per 60 fps clip, much longer at 240 fps. Steps and options are in `prototype/README.md`. `.claude/skills/verify/` is the scripted way to drive and prove it.
