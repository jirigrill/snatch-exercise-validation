"""S6: fill the hidden near knee (snatch.fill).

Reads the raw pose and the attempt windows, the plate outline (a near hip, knee or ankle inside it,
10 % margin, is hidden), the near side from facing.json, S5's scale.json (factor and the thigh /
shank multipliers) and that side's length table from skeleton.json. Writes pose.npz: `keypoints`
(n, 26, 2) = raw_pose's with the near knee replaced by the hybrid (RTMPose's knee, the rebuilt one
where it is hidden, cross-faded at each switch), `scores`, `t`, `ranges` (copied), `hidden` (n, 26)
bool (near hip, knee, ankle inside the plate) and `filled` (n, 26) bool (the rebuilt knee
contributes). Frames outside the attempt windows stay NaN. Scale method none: nothing is filled.

overlays/6_filled.mp4 (attempt windows, every 4th frame, zoomed): grey = RTMPose's near leg (dot at its knee),
purple = the filled knee with its thigh and shank, yellow-orange ring = a hidden joint that was not filled,
white = the rest of the skeleton (the far leg is not drawn).
"""

import json
from pathlib import Path

import cv2
import numpy as np

from snatch import athlete_store, overlay
from snatch.fill import fill
from snatch.pose import HALPE26, SIDE_OF
from snatch.skeleton import LengthTable
from snatch.stage import CLIP, SKELETON, Context, Stage

OVERLAY = "overlays/6_filled.mp4"
FILLED_COLOR = (200, 40, 160)  # BGR: purple
RIG_COLOR = (150, 150, 150)  # BGR: grey, RTMPose's near leg
REST_COLOR = (235, 235, 235)  # BGR: near white, the rest of the skeleton (thin)
HIDDEN_COLOR = (0, 215, 255)  # BGR: yellow-orange ring
LEGEND = (("grey: RTMPose leg", RIG_COLOR), ("purple: filled", FILLED_COLOR), ("ring: hidden, not filled", HIDDEN_COLOR))


def _pt(a: np.ndarray) -> tuple[int, int]:
    return int(a[0]), int(a[1])


def draw(img: np.ndarray, raw: np.ndarray, kp: np.ndarray, hidden: np.ndarray, filled: np.ndarray,
         side: str, i: int) -> None:
    """Frame i: the near leg of `raw` in grey, the filled knee's thigh and shank in purple, hidden joints not filled as rings."""
    j = [HALPE26[f"{side}_{n}"] for n in ("hip", "knee", "ankle")]
    if filled[i, j[1]]:
        for a, b in ((0, 1), (1, 2)):
            cv2.line(img, _pt(kp[i, j[a]]), _pt(kp[i, j[b]]), FILLED_COLOR, 9)
        cv2.circle(img, _pt(kp[i, j[1]]), 14, FILLED_COLOR, -1)
    for a, b in ((0, 1), (1, 2)):  # on top, thinner, so both legs show
        cv2.line(img, _pt(raw[i, j[a]]), _pt(raw[i, j[b]]), RIG_COLOR, 3)
    cv2.circle(img, _pt(raw[i, j[1]]), 9, (0, 0, 0), -1)
    cv2.circle(img, _pt(raw[i, j[1]]), 7, RIG_COLOR, -1)
    for c in j:
        if hidden[i, c] and not (filled[i, c] and c == j[1]):
            cv2.circle(img, _pt(kp[i, c]), 18, HIDDEN_COLOR, 4)


def run(ctx: Context, tmp: Path) -> None:
    raw = np.load(ctx.path("raw_pose.npz"))
    side = SIDE_OF[json.loads(ctx.path("facing.json").read_text())["facing"]]
    windows = [(int(a["window"][0]), int(a["window"][1]))
               for a in json.loads(ctx.path("attempts.json").read_text())["attempts"]]
    sc = json.loads(ctx.path("scale.json").read_text())
    sk = athlete_store.load(ctx.athletes, str(ctx.params["athlete"]), athlete_store.SKELETON) or {}
    plate = dict(np.load(ctx.path("plate.npz")))
    t = np.asarray(raw["t"], float)
    tab = LengthTable.from_json(sk[side]).scaled(sc["factor"]) if sc["method"] != "none" else None
    res = fill(raw["keypoints"], plate, windows, t, side, tab, sc["thigh_factor"] or 1.0, sc["shank_factor"] or 1.0)
    np.savez_compressed(tmp / "pose.npz", allow_pickle=False, keypoints=res.keypoints, scores=raw["scores"], t=t,
                        ranges=raw["ranges"], hidden=res.hidden, filled=res.filled)
    # the near hip, knee and ankle are drawn by `draw`; the far leg is dropped (RTMPose often puts it far off)
    view = res.keypoints.copy()
    far = "l" if side == "r" else "r"
    view[:, [HALPE26[f"{side}_{n}"] for n in ("hip", "knee", "ankle")]] = np.nan
    view[:, [HALPE26[f"{far}_{n}"] for n in ("knee", "ankle", "big_toe", "small_toe", "heel")]] = np.nan
    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), poses=[{"keypoints": view}], plate=plate, step=4, zoom=True,
                   legend=LEGEND, colors=(REST_COLOR,) * 3, annotate=lambda img, i: draw(img, raw["keypoints"], res.keypoints, res.hidden,
                                                               res.filled, side, i))


STAGE = Stage("S6", (CLIP, "raw_pose.npz", "attempts.json", "plate.npz", "facing.json", "scale.json", SKELETON),
              ("pose.npz", OVERLAY), run)
