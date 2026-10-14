"""Side check after S4: the athlete needs a skeleton for the clip's near side.

The near side follows from facing.json (S4). S0 only checks that skeleton.json
exists; a clip filmed from the other side than the calibration stops here with
exit 2. Not hashed and runs every time, like S0, so a recalibration does not
rerun pose.
"""

import json
from pathlib import Path

from snatch import athlete_store
from snatch.pose import SIDE_OF
from snatch.stage import Context, Stage, StageStop
from snatch.stages.athlete import NO_SKELETON_EXIT


def run(ctx: Context, _tmp: Path) -> None:
    athlete = str(ctx.params["athlete"])
    facing = json.loads(ctx.path("facing.json").read_text())["facing"]
    side = SIDE_OF[facing]
    sk = athlete_store.load(ctx.athletes, athlete, athlete_store.SKELETON) or {}
    if side not in sk:
        raise StageStop(NO_SKELETON_EXIT, "needs_calibration",
                        f"No {side} skeleton for {athlete} (the clip faces {facing}). Record a bar-only snatch "
                        f"clip facing {facing} (no plates, same camera spot) and run: "
                        f"pipeline.py --calibrate <bar.MOV> --athlete {athlete}")


STAGE = Stage("side", (), (), run, always=True)
