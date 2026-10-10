"""Run the pipeline-v2 stages on one clip (docs/pipeline-v2.html).

    uv run scripts/pipeline.py clip.MOV --athlete jiri [--only S-1 | --from S-1] [--force]
"""

import argparse
import sys
from pathlib import Path

from snatch.stage import Context, run_stages
from snatch.stages import STAGES


def main(argv: list[str] | None = None) -> int:
    names = [s.name for s in STAGES]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", type=Path)
    ap.add_argument("--athlete")
    ap.add_argument("--out", type=Path, help="default out/<clip stem>")
    pick = ap.add_mutually_exclusive_group()
    pick.add_argument("--only", choices=names, help="run this stage alone, always")
    pick.add_argument("--from", dest="start", choices=names, help="rerun this stage and every later one")
    ap.add_argument("--force", action="store_true", help="ignore the hashes")
    ap.add_argument("--load", type=float, help="kg on the bar incl. the bar, else from the filename")
    args = ap.parse_args(argv)

    params = {"athlete": args.athlete, "load": args.load}
    ctx = Context(args.clip, args.out or Path("out") / args.clip.stem, params)
    return run_stages(STAGES, ctx, only=args.only, start=args.start, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
