"""Run the pipeline-v2 stages on one clip (docs/pipeline-v2.html).

    uv run scripts/pipeline.py clip.MOV --athlete jiri [--height 1.80] [--only S-1 | --from S-1] [--force]
    uv run scripts/pipeline.py --calibrate bar.MOV --athlete jiri
"""

import argparse
import sys
from pathlib import Path

from snatch.stage import Context, run_stages
from snatch.stages import CALIBRATE, STAGES


def _radius(s: str) -> tuple[int, int]:
    try:
        lo, hi = (int(v) for v in s.split(":"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a:b, got {s!r}") from None
    return lo, hi


def parse(argv: list[str] | None = None) -> tuple[Context, argparse.Namespace]:
    names = list(dict.fromkeys(s.name for s in STAGES + CALIBRATE))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", type=Path, nargs="?")
    ap.add_argument("--calibrate", type=Path, metavar="BAR.MOV", help="calibrate the skeleton from a bar-only clip")
    ap.add_argument("--athlete", required=True)
    ap.add_argument("--height", type=float, help="athlete height in m, stored in athlete.json")
    ap.add_argument("--out", type=Path, help="default out/<clip stem>")
    ap.add_argument("--athletes", type=Path, default=Path("athletes"), help="athlete profiles root")
    pick = ap.add_mutually_exclusive_group()
    pick.add_argument("--only", choices=names, help="run this stage alone, always")
    pick.add_argument("--from", dest="start", choices=names, help="rerun this stage and every later one")
    ap.add_argument("--force", action="store_true", help="ignore the hashes")
    ap.add_argument("--load", type=float, help="kg on the bar incl. the bar, else from the filename")
    ap.add_argument("--intended", choices=("squat", "power", "muscle"), help="intended snatch type for S7")
    ap.add_argument("--radius", type=_radius, help="plate radius range in px, a:b")
    args = ap.parse_args(argv)
    if (args.clip is None) == (args.calibrate is None):
        ap.error("give one clip: <clip.MOV> or --calibrate <bar.MOV>")
    clip = args.calibrate or args.clip
    stages = CALIBRATE if args.calibrate else STAGES
    pick = args.only or args.start
    if pick and pick not in [s.name for s in stages]:
        ap.error(f"{pick} is not a stage of {'--calibrate' if args.calibrate else 'an analyze run'}")

    params = {"athlete": args.athlete, "height": args.height, "load": args.load, "intended": args.intended,
              "radius": args.radius, "calibrate": args.calibrate is not None}
    return Context(clip, args.out or Path("out") / clip.stem, params, athletes=args.athletes), args


def main(argv: list[str] | None = None) -> int:
    ctx, args = parse(argv)
    return run_stages(CALIBRATE if args.calibrate else STAGES, ctx, only=args.only, start=args.start, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
