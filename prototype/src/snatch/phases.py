"""Snatch phases from smoothed signals (S7). Pure: signals in, border frames out.

Signals are per attempt window, smoothed by the caller, near side only, in image pixels (y grows
down: "hub above X" = hub_y < X_y) or degrees. Every frame index is local to the window; every
duration comes from `t` (seconds), never from a frame rate. Rules, decided 2026-10-21
(docs/results/37-s7-phases.md; v2's rules, #13, are kept for liftoff, deepest_rebend,
full_extension and standing):

- bar_overhead (a marker, not a phase): runs of the hub above the nose lasting >= MIN_OVERHEAD_S;
  the longest one, [start, end) or None.
- liftoff: anchor = the last frame before bar_overhead.start with the hub below the hip; from
  there skip a stall, then step back to the start of the continuous rise (hub rising faster than
  RISE_PX_S). Without bar_overhead the anchor ends at the frame of the highest hub instead.
- full_extension: highest knee angle in [liftoff, bar_overhead.start] (no overhead: [liftoff,
  highest hub]).
- deepest_rebend: knee minima in [liftoff, full_extension] with prominence >= REBEND_DEG measured
  on that whole segment; only those at or after the first frame the hub is above the near knee
  count; the most prominent. None if there is none.
- first_knee_max: highest knee angle in [liftoff, deepest_rebend]; None without a re-bend.
- bar_peak: first peak of hub height in [full_extension, bar_overhead.end) with prominence >=
  PEAK_M (2 cm); none = "no dip" (a muscle snatch): the highest hub in that range. No overhead:
  the highest hub in [full_extension, window end).
- bar_lowest: the catch bottom. knee_low = lowest knee angle in [bar_peak, bar_overhead.end); upper =
  first frame >= knee_low with the knee within STAND_DEG of its maximum over [knee_low,
  bar_overhead.end); bar_lowest = lowest hub in [bar_peak, upper] (so the bar being lowered at the end
  of the hold is not counted); = bar_peak with no dip. None without bar_overhead.
- standing: first frame >= bar_lowest with the knee within STAND_DEG of its maximum over
  [bar_lowest, bar_overhead.end). None without bar_overhead.

Phases: starting_position (window start to liftoff), first_pull (to first_knee_max), transition
(to deepest_rebend), second_pull (to full_extension), turnover (to bar_peak), catch (to
bar_lowest), recovery (to standing), hold (to bar_overhead.end). A phase with a null border has a
null start or end. Same rules for every snatch type.
"""

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks

MIN_OVERHEAD_S = 0.25  # hub above the nose at least this long
RISE_PX_S = 50.0  # the hub rises faster than this: the pull is under way
REBEND_DEG = 3.0  # knee minimum prominence
PEAK_M = 0.02  # bar peak prominence, m
STAND_DEG = 5.0  # standing: knee within this of its maximum
SMOOTH_S = 0.1  # smoothing window of the signals (the caller smooths)
HOLD_DROP_M = 0.05  # hold ends when the hub falls this far below its median since standing

BORDERS = ("liftoff", "first_knee_max", "deepest_rebend", "full_extension", "bar_peak", "bar_lowest", "standing")
PHASES = (("starting_position", None, "liftoff"), ("first_pull", "liftoff", "first_knee_max"),
          ("transition", "first_knee_max", "deepest_rebend"), ("second_pull", "deepest_rebend", "full_extension"),
          ("turnover", "full_extension", "bar_peak"), ("catch", "bar_peak", "bar_lowest"),
          ("recovery", "bar_lowest", "standing"), ("hold", "standing", None))
PARAMS = dict(min_overhead_s=MIN_OVERHEAD_S, rise_px_s=RISE_PX_S, rebend_deg=REBEND_DEG, peak_m=PEAK_M,
              stand_deg=STAND_DEG, smooth_s=SMOOTH_S, hold_drop_m=HOLD_DROP_M)


@dataclass(frozen=True)
class Found:
    """Border frames (local to the window), the overhead marker, and the phases (name, start, end)."""
    borders: dict[str, int | None]
    bar_overhead: tuple[int, int] | None
    phases: list[tuple[str, int | None, int | None]]


def overhead_runs(above: np.ndarray, t: np.ndarray, min_s: float) -> list[tuple[int, int]]:
    """[start, end) runs of True spanning at least min_s seconds of `t`."""
    edges = np.diff(np.r_[0, above.astype(np.int8), 0])
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    t_end = np.r_[t, t[-1] + np.median(np.diff(t))]  # a run to the last frame ends one frame later
    return [(int(s), int(e)) for s, e in zip(starts, ends) if t_end[e] - t[s] >= min_s - 1e-9]


def liftoff_frame(hub_y: np.ndarray, end: int, t: np.ndarray, rise_px_s: float = RISE_PX_S) -> int:
    """From `end`: skip a stall, then back to the start of the continuous rise faster than rise_px_s."""
    rise = np.zeros(len(hub_y))
    rise[1:] = -np.diff(hub_y) / np.diff(t)
    i = end
    while i > 0 and rise[i] <= rise_px_s:
        i -= 1
    while i > 0 and rise[i] > rise_px_s:
        i -= 1
    return i + 1


def deepest_rebend(knee: np.ndarray, start: int, end: int, accept_from: int | None, deg: float = REBEND_DEG) -> int | None:
    """Most prominent knee minimum in [start, end] (prominence on the whole segment) at or after accept_from."""
    minima, props = find_peaks(-knee[start:end + 1], prominence=deg)
    prom = props["prominences"]
    ok = start + minima >= accept_from if accept_from is not None else np.ones(len(minima), bool)
    minima, prom = minima[ok], prom[ok]
    return start + int(minima[np.argmax(prom)]) if len(minima) else None


def bar_peak_frame(hub_y: np.ndarray, start: int, end: int, prominence_px: float) -> tuple[int, bool]:
    """First peak of hub height in [start, end) with the prominence, and True; none: the highest hub, False (no dip)."""
    height = -hub_y[start:end]
    peaks, _ = find_peaks(height, prominence=prominence_px)
    return (start + int(peaks[0]), True) if len(peaks) else (start + int(np.argmax(height)), False)


def hold_end(hub_y: np.ndarray, ppm: np.ndarray, stand: int, end: int, drop_m: float = HOLD_DROP_M) -> int:
    """First frame in (stand, end) with the hub > drop_m below its median over [stand, frame]; none: end."""
    for i in range(stand + 1, end):
        if hub_y[i] - np.median(hub_y[stand:i + 1]) > drop_m * ppm[i]:
            return i
    return end


def find_phases(*, knee: np.ndarray, hub_y: np.ndarray, hip_y: np.ndarray, knee_y: np.ndarray,
                nose_y: np.ndarray, t: np.ndarray, px_per_m: float, px_per_m_frame: np.ndarray | None = None) -> Found:
    """The borders and phases of one attempt window (arrays: one value per frame of the window).
    px_per_m_frame: per-frame scale for the hold end (default: px_per_m everywhere)."""
    n = len(t)
    runs = overhead_runs(hub_y < nose_y, t, MIN_OVERHEAD_S)
    over = max(runs, key=lambda r: (t[r[1] - 1] - t[r[0]], -r[0])) if runs else None
    top = int(np.argmax(-hub_y))  # highest hub
    pull_end = over[0] if over else top
    b: dict[str, int | None] = dict.fromkeys(BORDERS)
    below = np.flatnonzero(hub_y[:pull_end] > hip_y[:pull_end])
    if len(below):
        b["liftoff"] = liftoff_frame(hub_y, int(below[-1]), t)
    lo = b["liftoff"]
    if lo is not None and lo <= pull_end:
        b["full_extension"] = fe = lo + int(np.argmax(knee[lo:pull_end + 1]))
        above = np.flatnonzero(hub_y[lo:fe + 1] < knee_y[lo:fe + 1])
        b["deepest_rebend"] = deepest_rebend(knee, lo, fe, lo + int(above[0]) if len(above) else None)
        if b["deepest_rebend"] is not None:
            b["first_knee_max"] = lo + int(np.argmax(knee[lo:b["deepest_rebend"] + 1]))
        end = over[1] if over else n
        bp, dip = bar_peak_frame(hub_y, fe, end, PEAK_M * px_per_m)
        b["bar_peak"] = bp
        if over:
            bl = bp  # no dip (muscle snatch): the catch has no length
            if dip:
                kl = bp + int(np.argmin(knee[bp:end]))
                tail = knee[kl:end]
                upper = kl + int(np.argmax(tail >= tail.max() - STAND_DEG))
                bl = bp + int(np.argmax(hub_y[bp:upper + 1]))
            b["bar_lowest"] = bl
            seg = knee[bl:end]
            b["standing"] = bl + int(np.argmax(seg >= seg.max() - STAND_DEG))
    else:
        b["liftoff"] = None  # no pull found before the bar went up
    ppm = np.full(n, px_per_m) if px_per_m_frame is None else px_per_m_frame
    hold_e = None if over is None else (over[1] if b["standing"] is None else hold_end(hub_y, ppm, b["standing"], over[1]))
    phases: list[tuple[str, int | None, int | None]] = []
    for name, a, z in PHASES:
        s = 0 if a is None else b[a]
        e = hold_e if z is None else b[z]
        phases.append((name, s, e))
    return Found(b, over, phases)
