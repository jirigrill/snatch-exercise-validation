"""Fill the hidden near knee (S6): rebuild it from the hip, ankle and the leg's segment lengths.

Side-on, the near plate hides the near knee around the transition and RTMPose guesses there
(docs/results/36-skeleton-fill.md). The knee is where the circle of thigh length around the hip meets
the circle of shank length around the ankle (`snatch.skeleton.two_circle_knee`). The lengths are
the athlete's table x S5's factor, thigh and shank each x their own multiplier (scale.json).

- hidden: a raw near hip, knee or ankle inside the plate outline grown by HIDDEN_DIST (10 % margin
  around the rim: RTMPose starts to drift just before the rim), on a frame where the plate was found.
- rebuilt where the knee is hidden, the hip and ankle are not, the circles meet and the leg is bent
  enough (knee_gain <= MAX_GAIN). Anywhere else RTMPose's knee stays (a straight leg, or the hip /
  ankle hidden too: hidden but not filled).
- `fill_hidden` cross-fades RTMPose's and the rebuilt knee over FADE_S at each switch, so the switch
  itself adds no step that could read as a knee re-bend. Only the near knee is ever filled.
"""

from dataclasses import dataclass

import numpy as np

from snatch.pose import HALPE26
from snatch.scale import covered, smoothed
from snatch.signals import window_frames
from snatch.skeleton import MAX_GAIN, LengthTable, knee_gain, two_circle_knee

HIDDEN_DIST = 1.1  # x the plate outline: inside = hidden
FADE_S = 25 / 240  # cross-fade length, s (25 frames at 240 fps)


def fade_frames(t: np.ndarray, fade_s: float = FADE_S) -> int:
    """Odd number of frames spanning `fade_s` of the times `t`."""
    return window_frames(t, fade_s) | 1


def fill_hidden(observed: np.ndarray, rebuilt: np.ndarray, use: np.ndarray, t: np.ndarray,
                fade_s: float = FADE_S) -> tuple[np.ndarray, np.ndarray]:
    """(points, weight): observed where `use` is False, rebuilt where True, cross-faded over
    `fade_s` seconds at each switch (a moving average of `use`). (n, 2) points; NaN rows in
    `rebuilt` fall back to observed. weight = the share of rebuilt in each point."""
    n = fade_frames(t, fade_s)
    w = np.convolve(np.asarray(use, float), np.ones(n) / n, mode="same")
    w = np.where(np.isnan(rebuilt).any(1), 0.0, w)[:, None]
    return w * np.nan_to_num(rebuilt) + (1 - w) * observed, w[:, 0]


def rebuild(hip: np.ndarray, ankle: np.ndarray, tab: LengthTable, thigh_f: float, shank_f: float,
            sign: float) -> tuple[np.ndarray, np.ndarray]:
    """(knee (n, 2), fillable (n,) bool): `tab` already scaled by the clip's factor; thigh and shank
    x their multipliers. fillable: the circles meet and knee_gain <= MAX_GAIN."""
    lt, ls = tab.lengths(np.hypot(*(ankle - hip).T))
    lt, ls = lt * thigh_f, ls * shank_f
    knee, clipped = two_circle_knee(hip, ankle, lt, ls, sign)
    return knee, ~clipped & (knee_gain(hip, ankle, lt, ls, sign) <= MAX_GAIN)


@dataclass(frozen=True)
class Filled:
    keypoints: np.ndarray  # (n, 26, 2) raw, the near knee replaced by the hybrid
    hidden: np.ndarray  # (n, 26) bool: near hip, knee, ankle hidden
    filled: np.ndarray  # (n, 26) bool: the rebuilt knee contributes (weight > 0)


def fill(raw: np.ndarray, plate: dict, windows: list[tuple[int, int]], t: np.ndarray, side: str,
         tab: LengthTable | None, thigh_f: float, shank_f: float) -> Filled:
    """`tab`: the athlete's table already scaled by S5's factor; None (scale method none): fill nothing."""
    hid = covered(raw, plate, side, HIDDEN_DIST)  # hip, knee, ankle
    hidden = np.zeros(raw.shape[:2], bool)
    for c, name in enumerate(("hip", "knee", "ankle")):
        hidden[:, HALPE26[f"{side}_{name}"]] = hid[:, c]
    knee_j = HALPE26[f"{side}_knee"]
    rebuilt = np.full((len(raw), 2), np.nan)
    use = np.zeros(len(raw), bool)
    if tab is not None:
        k = smoothed(raw, t, windows, side)
        hip, ank = k[:, HALPE26[f"{side}_hip"]], k[:, HALPE26[f"{side}_ankle"]]
        knee, fillable = rebuild(hip, ank, tab, thigh_f, shank_f, 1.0 if side == "r" else -1.0)
        has = ~np.isnan(hip).any(1) & ~np.isnan(ank).any(1)
        rebuilt[has] = knee[has]
        use = hid[:, 1] & ~hid[:, 0] & ~hid[:, 2] & fillable & has
    out = raw.copy()
    out[:, knee_j], weight = fill_hidden(raw[:, knee_j], rebuilt, use, t)
    filled = np.zeros(raw.shape[:2], bool)
    filled[:, knee_j] = weight > 0
    return Filled(out, hidden, filled)
