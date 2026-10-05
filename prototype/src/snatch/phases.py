"""Mark the four lift phases in each snatch rep.

Phase definition v1 (frozen in docs/results/12-walking-skeleton.md; later
tickets reuse it). All inputs are per-frame signals in image pixels (y grows
downward) or degrees, already smoothed by the caller.

- overhead run: contiguous frames with the wrists above the nose, at least
  `min_overhead_s` long. One run = one rep.
- setup: liftoff. Anchor on the last frame before the overhead run with the
  wrists still below the hips (mid-pull, bar rising), then step back to the
  first frame of that continuous rise (wrist rising faster than
  `still_px_s`). The anchor avoids the bar float near the top; stepping back
  on speed (not a floor height) avoids drift between reach-down and grip.
- transition: the deepest knee re-bend (local knee-angle minimum, at least
  `min_dip_deg` deep) between the moment the wrists rise above the knees and
  the peak knee extension before the wrists pass the nose. None if there is
  no such re-bend (= not detected).
- catch: lowest hip (largest hip y) between that peak extension and the end
  of the overhead run.
- lockout: first frame after the catch at which the knee angle is within
  `tol_deg` of its maximum for the rest of the overhead run.

Phase definition v2 (frozen 2026-10-02, before #15 runs; see
docs/results/14-ladder-and-plate.md): v1 with every use of wrist height
replaced by the height of the near plate's hub (snatch.plate), the bar the
hands grip. From the side the hands sit inside the plate's outline, so the
wrists are the least confident keypoints; the hub is visible. One more
change ("v2.1", chosen after seeing 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg): the re-bend's prominence is
measured on the whole setup -> peak-extension segment, and only minima after
the hub passes the knees count. The hub is lower than the wrists, so it can
pass the knees after the knee's local maximum, and a window starting there
cuts off the re-bend's left shoulder. Everything else as v1: same events,
thresholds and order. Clips without a plate (20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg, bar only) keep v1.

#13 (2026-10-02): the developer accepted all v2 marks on 6 side-on reps.
v2 is final; do not change it (docs/results/13-phase-check.md).
"""

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks


@dataclass(frozen=True)
class Rep:
    setup: int
    transition: int | None
    catch: int
    lockout: int
    overhead_start: int
    overhead_end: int


def overhead_runs(above: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """[start, end) runs of True at least min_len long."""
    edges = np.diff(np.r_[0, above.astype(np.int8), 0])
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return [(int(s), int(e)) for s, e in zip(starts, ends) if e - s >= min_len]


def liftoff_frame(wrist_y: np.ndarray, end: int, fps: float,
                  still_px_s: float) -> int:
    rise_px_s = -np.diff(wrist_y, prepend=wrist_y[0]) * fps
    i = end
    while i > 0 and rise_px_s[i] <= still_px_s:  # skip a stall at the top
        i -= 1
    while i > 0 and rise_px_s[i] > still_px_s:
        i -= 1
    return i + 1


def pull_anchor_frame(wrist_y: np.ndarray, hip_y: np.ndarray, end: int) -> int:
    """Last frame up to `end` with the wrists still below the hips (mid-pull)."""
    below = np.flatnonzero(wrist_y[:end + 1] > hip_y[:end + 1])
    return int(below[-1])


def transition_frame(knee: np.ndarray, start: int, end: int,
                     min_dip_deg: float, accept_from: int | None = None
                     ) -> int | None:
    """Deepest knee re-bend in [start, end].

    accept_from (v2): prominence is still measured on the whole segment, but
    only minima at or after accept_from count.
    """
    seg = knee[start:end + 1]
    minima, props = find_peaks(-seg, prominence=min_dip_deg)
    prom = props["prominences"]
    if accept_from is not None:
        ok = start + minima >= accept_from
        minima, prom = minima[ok], prom[ok]
    if len(minima) == 0:
        return None
    return start + int(minima[np.argmax(prom)])


def catch_frame(hip_y: np.ndarray, start: int, end: int) -> int:
    return start + int(np.argmax(hip_y[start:end + 1]))


def lockout_frame(knee: np.ndarray, catch: int, end: int,
                  tol_deg: float) -> int:
    seg = knee[catch:end + 1]
    return catch + int(np.argmax(seg >= np.max(seg) - tol_deg))


def find_reps(*, wrist_y: np.ndarray, nose_y: np.ndarray, hip_y: np.ndarray,
              knee: np.ndarray, fps: float,
              knee_y: np.ndarray | None = None, min_overhead_s: float = 0.25,
              still_px_s: float = 50.0, min_dip_deg: float = 3.0,
              tol_deg: float = 5.0, prominence_from_setup: bool = False
              ) -> list[Rep]:
    reps = []
    runs = overhead_runs(wrist_y < nose_y, int(min_overhead_s * fps))
    for oh_start, oh_end in runs:
        anchor = pull_anchor_frame(wrist_y, hip_y, oh_start)
        setup = liftoff_frame(wrist_y, anchor, fps, still_px_s)
        peak = setup + int(np.argmax(knee[setup:oh_start + 1]))
        search_from = setup
        if knee_y is not None:  # re-bend only once the bar is above the knees
            above = np.flatnonzero(wrist_y[setup:peak + 1] < knee_y[setup:peak + 1])
            search_from = setup + int(above[0]) if len(above) else peak
        if prominence_from_setup:  # v2
            transition = transition_frame(knee, setup, peak, min_dip_deg,
                                          accept_from=search_from)
        else:  # v1
            transition = transition_frame(knee, search_from, peak, min_dip_deg)
        catch = catch_frame(hip_y, peak, oh_end - 1)
        lockout = lockout_frame(knee, catch, oh_end - 1, tol_deg)
        reps.append(Rep(setup, transition, catch, lockout, oh_start, oh_end))
    return reps


def find_reps_v2(*, hub_y: np.ndarray, nose_y: np.ndarray, hip_y: np.ndarray,
                 knee: np.ndarray, fps: float, knee_y: np.ndarray | None = None,
                 **thresholds: float) -> list[Rep]:
    """Phase definition v2: v1 timed from the plate hub, not the wrists,
    with the transition's prominence measured from setup."""
    return find_reps(wrist_y=hub_y, nose_y=nose_y, hip_y=hip_y, knee=knee,
                     fps=fps, knee_y=knee_y, prominence_from_setup=True,
                     **thresholds)
