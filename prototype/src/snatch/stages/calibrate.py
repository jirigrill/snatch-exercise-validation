"""C3: fit the athlete's leg skeleton on a bar-only clip (snatch.skeleton).

--calibrate runs S-1, S0, S1 and S2 on the bar-only clip (C1 and C2 of the
spec are the same stages), then this. It writes the near side's entry of
athletes/<athlete>/skeleton.json (the length table and its hide test),
keeping the other side's, and two checks by eye:

- calibration.jpg: left, thigh and shank length per frame vs leg bend, with
  the table; right, the hide test: knee angle over the clip, true vs rebuilt
  where a virtual plate hides the knee.
- calibration_overlay.mp4: the hidden frames only. Orange = the virtual plate,
  green = the true (visible) pose, magenta = the same pose with the knee
  rebuilt; the knee keeps RTMPose's where the leg is too straight to rebuild.

Too few usable frames, or no frame to rebuild, stops with exit 3 (clip unusable).
The cm in the hide test come from the height in athlete.json, which is not
hashed: a new height shows on the next refit (--only C3).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from snatch import athlete_store, overlay, skeleton  # noqa: E402
from snatch.angles import HALPE26, joint_angle  # noqa: E402
from snatch.pose import SIDE_OF  # noqa: E402
from snatch.stage import CLIP, SKELETON, Context, Stage, StageStop  # noqa: E402

UNUSABLE_EXIT = 3
OVERLAY = "overlays/calibration_overlay.mp4"
FIGURE = "overlays/calibration.jpg"
FLAG_PX = 20  # red border: rebuilt knee this far off the visible one (~6 cm)


def _figure(path: Path, k: np.ndarray, t: np.ndarray, tab: skeleton.LengthTable, side: str,
            test: dict, arrays: dict[str, np.ndarray]) -> None:
    hip, knee, ank = (k[:, HALPE26[f"{side}_{p}"]] for p in ("hip", "knee", "ankle"))
    r = np.hypot(*(ank - hip).T) / tab.d_ref
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ax[0].scatter(r, np.hypot(*(knee - hip).T), s=2, alpha=.25, c="tab:blue", label="thigh, each frame")
    ax[0].scatter(r, np.hypot(*(ank - knee).T), s=2, alpha=.25, c="tab:orange", label="shank, each frame")
    c = (tab.edges[:-1] + tab.edges[1:]) / 2
    ax[0].plot(c, tab.thigh, "-o", c="navy", label="thigh, table")
    ax[0].plot(c, tab.shank, "-o", c="darkred", label="shank, table")
    lo, hi = min(tab.thigh.min(), tab.shank.min()), max(tab.thigh.max(), tab.shank.max())
    ax[0].set(xlabel="leg bend: hip-ankle / standing hip-ankle (1 = straight)", ylabel="px",
              title=f"{side} leg: bone length vs leg bend (standing hip-ankle {tab.d_ref:.0f} px)",
              ylim=(lo - 0.15 * hi, hi * 1.15))
    ax[0].legend(fontsize=8)
    true, rebuilt = joint_angle(hip, knee, ank), joint_angle(hip, arrays["knee"], ank)
    ax[1].fill_between(t, 0, 1, where=arrays["hidden"], color="0.85", transform=ax[1].get_xaxis_transform(),
                       label="knee behind the virtual plate")
    ax[1].plot(t, true, c="green", label="true knee")
    ax[1].plot(t, rebuilt, c="magenta", ls="--", label="rebuilt where hidden")
    e, a = test["knee_err_cm"], test["angle_err_deg"]
    ax[1].set(xlabel="s", ylabel="knee angle deg",
              title=f"Hide test: {test['rebuilt_frames']}/{test['hidden_frames']} hidden rebuilt, "
                    f"median {e['median']} cm / {a['median']}° off")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def run(ctx: Context, tmp: Path) -> None:
    raw = np.load(ctx.path("raw_pose.npz"))
    facing = json.loads(ctx.path("facing.json").read_text())["facing"]
    side = SIDE_OF[facing]
    athlete = str(ctx.params["athlete"])
    height = float(athlete_store.load(ctx.athletes, athlete, athlete_store.ATHLETE)["height_m"])  # type: ignore[index]
    try:
        entry, tab, k = skeleton.fit(raw["keypoints"], raw["scores"], raw["t"], facing)
        test, arrays = skeleton.hide_test(k, tab, facing, height)
    except skeleton.FitError as e:
        raise StageStop(UNUSABLE_EXIT, "calibration_failed", f"cannot fit the {side} skeleton: {e}") from None
    entry = {**entry, "hide_test": test, "clip": ctx.clip.name, "width": int(raw["width"]),
             "height": int(raw["height"]), "fitted": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    sk = athlete_store.load(ctx.athletes, athlete, athlete_store.SKELETON) or {}
    (tmp / SKELETON).write_text(json.dumps({**sk, side: entry}, indent=2) + "\n")

    (tmp / FIGURE).parent.mkdir(parents=True, exist_ok=True)
    _figure(tmp / FIGURE, k, raw["t"], tab, side, test, arrays)
    shown = np.where(arrays["hidden"][:, None, None], k, np.nan)  # draws only the hidden frames
    with_knee = shown.copy()
    with_knee[:, HALPE26[f"{side}_knee"]] = np.where(arrays["hidden"][:, None], arrays["knee"], np.nan)
    r = np.full(len(k), skeleton.PLATE_R * tab.d_ref)
    plate = {"hub_x": arrays["hub"][:, 0], "hub_y": arrays["hub"][:, 1], "a": r, "b": r,
             "angle": np.zeros(len(k)), "found": arrays["hidden"]}
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), poses=[{"keypoints": shown}, {"keypoints": with_knee}],
                   plate=plate, step=2, zoom=True, flag_px=FLAG_PX,
                   notes=("orange: virtual plate", "green: true knee", "magenta: rebuilt"))


STAGE = Stage("C3", (CLIP, "raw_pose.npz", "facing.json"), (SKELETON, OVERLAY, FIGURE), run, version=2)
