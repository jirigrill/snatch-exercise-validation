"""S5: the clip's scale factor for the athlete's leg skeleton (snatch.scale).

Reads the posed frames inside the attempt windows (raw_pose.npz, attempts.json), the plate
outline (plate.npz: joints inside it are not used), the near side from facing.json and that side's length table from skeleton.json. Writes scale.json
({factor, method, n_frames, spread, frames, thigh_shank, thigh_shank_cal}; `frames` are
[start, end) runs of clip frame indices) and overlays/5_scale.jpg: up to three of the frames
used (first, middle, last) with the near hip-ankle line, the factor, method and frame count.
No usable frames: method "none" (factor null, n_frames 0, frames []), exit 0; the overlay is one clip
frame saying so. Proportions off by more than 10 %: exit 5 (`cannot_scale`); scale.json and the
overlay are still written with what was measured.
"""

import json
from pathlib import Path

import cv2
import numpy as np

from snatch import athlete_store, overlay
from snatch import scale as sc
from snatch.pose import HALPE26, SIDE_OF
from snatch.skeleton import LengthTable
from snatch.stage import CLIP, SKELETON, Context, Stage, StageStop
from snatch.video import frames, probe

CANNOT_SCALE_EXIT = 5
OVERLAY = "overlays/5_scale.jpg"
STRIP_HEIGHT = 540  # px per frame in the strip


NONE_TEXT = "method none: no usable frames (plate covers the hip)"


def write_none_overlay(clip: str, path: Path, windows: list[tuple[int, int]]) -> None:
    """One clip frame (middle of the first attempt window) with NONE_TEXT."""
    info = probe(clip)
    s, e = windows[0] if windows else (0, info.n_frames)
    i = (s + e) // 2
    img = next(f for n, f in enumerate(frames(clip, info, stop=i + 1)) if n == i).copy()
    overlay._text(img, NONE_TEXT, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)


def write_overlay(clip: str, path: Path, k: np.ndarray, side: str, res: sc.Scale) -> None:
    used = res.frames
    picks = sorted({int(used[0]), int(used[len(used) // 2]), int(used[-1])})
    info = probe(clip)
    hip, ank = k[:, HALPE26[f"{side}_hip"]], k[:, HALPE26[f"{side}_ankle"]]
    tiles = []
    for i, img in enumerate(frames(clip, info, stop=picks[-1] + 1)):
        if i not in picks:
            continue
        img = img.copy()
        cv2.line(img, tuple(map(int, hip[i])), tuple(map(int, ank[i])), (0, 220, 0), 5)
        for p in (hip[i], ank[i]):
            cv2.circle(img, tuple(map(int, p)), 10, (255, 0, 255), -1)
        x0, y0, x1, y1 = overlay.zoom_window(np.stack([hip[i], ank[i]]), info.width, info.height, margin=300)
        tile = img[y0:y1, x0:x1]
        cv2.putText(tile, f"frame {i}", (10, tile.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 6)
        cv2.putText(tile, f"frame {i}", (10, tile.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        w = max(1, round(tile.shape[1] * STRIP_HEIGHT / tile.shape[0]))
        tiles.append(cv2.resize(tile, (w, STRIP_HEIGHT)))
    strip = np.hstack(tiles)
    overlay._text(strip, f"{res.method}, factor {res.factor:.3f}, {len(used)} frames", 0)
    overlay._text(strip, "green line: near hip - ankle", 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), strip)


def run(ctx: Context, tmp: Path) -> None:
    raw = np.load(ctx.path("raw_pose.npz"))
    facing = json.loads(ctx.path("facing.json").read_text())["facing"]
    side = SIDE_OF[facing]
    windows = [(int(a["window"][0]), int(a["window"][1]))
               for a in json.loads(ctx.path("attempts.json").read_text())["attempts"]]
    sk = athlete_store.load(ctx.athletes, str(ctx.params["athlete"]), athlete_store.SKELETON) or {}
    tab = LengthTable.from_json(sk[side])
    t = np.asarray(raw["t"], float)
    k = sc.smoothed(raw["keypoints"], t, windows, side)
    cov = sc.covered(raw["keypoints"], np.load(ctx.path("plate.npz")), side)
    stop: sc.CannotScale | None = None
    try:
        res: sc.Scale | None = sc.estimate(k, raw["scores"], t, windows, tab, side, cov)
    except sc.CannotScale as e:
        res, stop = e.partial, e
    data = sc.to_json(res) if res else {"factor": None, "method": "none", "n_frames": 0, "spread": None,
                                        "frames": [], "thigh_shank": None, "thigh_shank_cal": None}
    (tmp / "scale.json").write_text(json.dumps(data, indent=2) + "\n")
    if res is None or res.method == "none":
        write_none_overlay(str(ctx.clip), tmp / OVERLAY, windows)
    else:
        write_overlay(str(ctx.clip), tmp / OVERLAY, k, side, res)
    if stop:
        raise StageStop(CANNOT_SCALE_EXIT, "cannot_scale", stop.reason)


STAGE = Stage("S5", (CLIP, "raw_pose.npz", "attempts.json", "plate.npz", "facing.json", SKELETON), ("scale.json", OVERLAY), run)
