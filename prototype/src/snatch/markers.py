"""Bar markers per rep from the plate hub (docs/research/11-technique-markers.md).

Inputs are the hub's image position in pixels (y grows downward, the lifter
faces +x, so "toward the lifter" is -x), already smoothed by the caller, and
the plate-plane scale px_per_m. Windows:

- peak height: highest hub point between `setup` and the hip catch (`catch`);
  the window ends there because the bar is high again at lockout.
- bar catch: lowest hub point after the peak, up to `lockout` (Shah); not
  the hip catch.
- X1 (B2): from setup back to the rearmost point up to `transition`, the end
  of the first pull. Doc 11 says "up to the first reversal"; the transition
  stands in for it because in the side-on reps (#30) the bar keeps moving
  toward the lifter through the second pull, so a window up to the peak
  puts the X1 point at the peak and X2 at 0. NaN if no transition.
- X2 (B3): from that point forward to the foremost point before the peak.
- Xloop (B4): back toward the lifter from the peak to the bar catch.
- Xnet (B5): bar catch minus setup; negative = caught behind the start.
- drop (B8): bar catch height below the peak.
- C1: peak upward bar speed between setup and the peak.
- D4 turnover: peak upward speed -> lowest (most downward) speed before the
  bar catch (Ahn & Kipp). Doc 11's other end point, peak speed -> bar
  catch, is kept as turnover_to_bar_catch_s.

Verdict for a lower frame rate (#30, frozen before the results were seen):
ratio = worst |difference from 240 fps| / rep-to-rep SD at 240 fps.
usable <= 0.5, marginal <= 1, unusable above or if not detected; n/a if
there is no spread at 240 fps. A group takes its markers' most common
verdict (plurality, n/a left out); ties go to the worse one.
"""

import math
from collections import Counter
from dataclasses import dataclass

import numpy as np

from snatch.phases import Rep


@dataclass(frozen=True)
class BarMarkers:
    peak_frame: int
    bar_catch_frame: int
    x1_cm: float
    x2_cm: float
    xloop_cm: float
    xnet_cm: float
    drop_cm: float
    peak_v_m_s: float
    turnover_s: float
    turnover_to_bar_catch_s: float


def bar_markers(hub_x: np.ndarray, hub_y: np.ndarray, px_per_m: float,
                fps: float, rep: Rep, t: np.ndarray | None = None) -> BarMarkers:
    """`t`: frame times (s), for clips with dropped frames; default i / fps."""
    t = np.arange(len(hub_y)) / fps if t is None else t
    cm = 100 / px_per_m
    s = rep.setup
    peak = s + int(np.argmin(hub_y[s:rep.catch + 1]))
    bar_catch = peak + int(np.argmax(hub_y[peak:rep.lockout + 1]))
    vy = -np.gradient(hub_y, t) / px_per_m
    v_peak = s + int(np.argmax(vy[s:peak + 1]))
    v_low = v_peak + int(np.argmin(vy[v_peak:bar_catch + 1]))
    x1 = x2 = math.nan
    if rep.transition is not None:
        back = s + int(np.argmin(hub_x[s:rep.transition + 1]))
        x1 = float(hub_x[s] - hub_x[back]) * cm
        x2 = float(np.max(hub_x[back:peak + 1]) - hub_x[back]) * cm
    return BarMarkers(
        peak_frame=peak,
        bar_catch_frame=bar_catch,
        x1_cm=x1,
        x2_cm=x2,
        xloop_cm=float(hub_x[peak] - hub_x[bar_catch]) * cm,
        xnet_cm=float(hub_x[bar_catch] - hub_x[s]) * cm,
        drop_cm=float(hub_y[bar_catch] - hub_y[peak]) * cm,
        peak_v_m_s=float(vy[v_peak]),
        turnover_s=float(t[v_low] - t[v_peak]),
        turnover_to_bar_catch_s=float(t[bar_catch] - t[v_peak]),
    )


VERDICTS = ("usable", "marginal", "unusable")


def verdict(max_err: float, spread: float) -> str:
    if spread == 0:
        return "n/a"
    ratio = max_err / spread
    if math.isnan(ratio) or ratio > 1:
        return "unusable"
    return "usable" if ratio <= 0.5 else "marginal"


def group_verdict(verdicts: list[str]) -> str:
    counts = Counter(v for v in verdicts if v != "n/a")
    if not counts:
        return "n/a"
    return max(reversed(VERDICTS), key=lambda v: counts[v])
