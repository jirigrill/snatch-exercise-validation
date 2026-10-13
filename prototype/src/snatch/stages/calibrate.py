"""C3: fit the athlete's leg skeleton on a bar-only clip (snatch.skeleton).

--calibrate runs S-1, S0, S1 and S2 on the bar-only clip (C1 and C2 of the
spec are the same stages), then this. It writes the near side's entry of
athletes/<athlete>/skeleton.json, keeping the other side's, and
calibration_overlay.mp4: green = RTMPose (smoothed, as fitted), magenta = the
same pose with the near knee rebuilt from hip, ankle and the length table, so
the two should agree wherever the knee is visible (a straight leg is ill
conditioned, so up to ~20 px there). Too few usable frames
stops with exit 3 (clip unusable).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from snatch import athlete_store, overlay, skeleton
from snatch.angles import HALPE26
from snatch.pose import SIDE_OF
from snatch.stage import CLIP, SKELETON, Context, Stage, StageStop

UNUSABLE_EXIT = 3
OVERLAY = "overlays/calibration_overlay.mp4"
FLAG_PX = 20  # red border: rebuilt knee this far off the visible one (~6 cm); a straight leg reaches ~18 on T5


def run(ctx: Context, tmp: Path) -> None:
    raw = np.load(ctx.path("raw_pose.npz"))
    facing = json.loads(ctx.path("facing.json").read_text())["facing"]
    side = SIDE_OF[facing]
    try:
        entry, k, rebuilt = skeleton.fit(raw["keypoints"], raw["scores"], raw["t"], facing)
    except skeleton.FitError as e:
        raise StageStop(UNUSABLE_EXIT, "calibration_failed", f"cannot fit the {side} skeleton: {e}") from None
    entry = {**entry, "clip": ctx.clip.name, "width": int(raw["width"]), "height": int(raw["height"]),
             "fitted": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    sk = athlete_store.load(ctx.athletes, str(ctx.params["athlete"]), athlete_store.SKELETON) or {}
    (tmp / SKELETON).write_text(json.dumps({**sk, side: entry}, indent=2) + "\n")

    fitted = {"keypoints": k, "scores": raw["scores"]}
    with_knee = k.copy()
    with_knee[:, HALPE26[f"{side}_knee"]] = rebuilt
    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), poses=[fitted, {**fitted, "keypoints": with_knee}],
                   step=4, zoom=True, flag_px=FLAG_PX, notes=("green RTMPose", f"magenta {side} knee from table"))


STAGE = Stage("C3", (CLIP, "raw_pose.npz", "facing.json"), (SKELETON, OVERLAY), run)
