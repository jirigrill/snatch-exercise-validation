"""S8 judge: performed type, intended type and lift_result per attempt. Pure: per-attempt signals in, a record out.

Rules (.scratch/plan/D-judge.md, "S8 judge", decided 2026-10-23); S7's border names. Every frame index is global.
performed_type: unknown when there is no bar_peak / bar_overhead / bar_lowest (failed pull), or hip/knee filled or
hidden at bar_lowest, or no knee angle over bar_peak -> standing (low_confidence); muscle when the knee drops <= MUSCLE_DROP_DEG below its full_extension
value over bar_peak -> standing; else squat when the hip is at or below the knee at bar_lowest, else power.
Hold = S7's `hold` phase (standing -> hold end). Check 2 = elbow < ELBOW_MIN_DEG on hold frames with the wrist seen (none seen: unsure);
check 3 = S7 standing is null (hip/knee filled or hidden at standing: unsure); check 4 unsure when the plate is lost
in the hold (S7's hold end relies on the hub); type_mismatch unsure when performed is unknown for low_confidence. Checks 1-7 in order, each pass / fail / unsure / skipped; the first fail is the reason (a fail always beats an
unsure); with no fail, an unsure gives unknown: low_confidence; completed = every check passes (or is skipped).
"""

from dataclasses import dataclass

import numpy as np

ELBOW_MIN_DEG = 165.0  # check 2: elbow locked
HOLD_MIN_S = 0.5  # check 4
MUSCLE_DROP_DEG = 10.0  # performed type: knee drop below full_extension that is still "no rebend"
PARAMS = dict(elbow_min_deg=ELBOW_MIN_DEG, hold_min_s=HOLD_MIN_S, muscle_drop_deg=MUSCLE_DROP_DEG)
CHECKS = ("no_overhead", "elbow_unlocked", "no_standup", "hold_short", "type_mismatch", "low_confidence")
TYPES = ("muscle", "power", "squat")


@dataclass(frozen=True)
class Signals:
    """Per-frame clip arrays (global frame index), near side. y grows down (hip above knee = hip_y < knee_y)."""
    t: np.ndarray
    knee: np.ndarray  # deg (S7 angles.csv; NaN outside the windows)
    elbow: np.ndarray  # deg
    wrist_hidden: np.ndarray  # bool: elbow unusable
    leg_unsure: np.ndarray  # bool: near hip or knee filled / hidden by S6
    hip_y: np.ndarray
    knee_y: np.ndarray
    plate_found: np.ndarray  # bool


def _frame(rec: dict, name: str) -> int | None:
    b = rec["borders"].get(name)
    return None if b is None else int(b["frame"])


def performed_type(rec: dict, s: Signals) -> tuple[str, str | None]:
    """(type, why unknown or None)."""
    oh, peak, low, fe = rec["bar_overhead"], _frame(rec, "bar_peak"), _frame(rec, "bar_lowest"), _frame(rec, "full_extension")
    if oh is None or peak is None or low is None or fe is None:
        return "unknown", "failed_pull"
    if s.leg_unsure[low]:
        return "unknown", "low_confidence"
    stand = _frame(rec, "standing")
    end = stand + 1 if stand is not None else int(oh["end"])
    seg = s.knee[peak:end]
    if not np.isfinite(seg).any() or not np.isfinite(s.knee[fe]):
        return "unknown", "low_confidence"
    if np.nanmin(seg) >= s.knee[fe] - MUSCLE_DROP_DEG:
        return "muscle", None
    return ("squat" if s.hip_y[low] >= s.knee_y[low] else "power"), None


def _check(value: float | None, threshold: float | None, unit: str, result: str, frames: tuple[int, int] | None,
           worst: int | None = None, **extra: object) -> dict:
    return dict(value=None if value is None else round(float(value), 3), threshold=threshold, unit=unit, result=result,
                frames=None if frames is None else [int(frames[0]), int(frames[1])],
                worst=None if worst is None else int(worst), **extra)


def _skipped() -> dict:
    return _check(None, None, "", "skipped", None)


def intended(param: str | None, label: str | None, performed: str) -> tuple[str, str]:
    """(intended_type, intended_source): --intended > labels.csv > inferred (= performed). An empty label = none."""
    if param:
        return param, "param"
    if label:
        return label, "labels"
    return performed, "inferred"


def _unsure_if(flag: bool, result: str) -> str:
    return "unsure" if flag and result == "pass" else result


def judge(rec: dict, s: Signals, intended_param: str | None = None, label: str | None = None) -> dict:
    """The judgement of one S7 phases.json attempt record."""
    performed, why = performed_type(rec, s)
    want, source = intended(intended_param, label, performed)
    oh, stand = rec["bar_overhead"], _frame(rec, "standing")
    w0, w1 = int(rec["window"][0]), int(rec["window"][1])
    c: dict[str, dict] = {}
    c["no_overhead"] = _check(None, None, "", "fail" if oh is None else "pass",
                              (w0, w1) if oh is None else (int(oh["start"]), int(oh["end"])))
    hp = {p["name"]: p for p in rec["phases"]}.get("hold")
    hold = None if oh is None or stand is None or hp is None or hp["end"] is None else (int(hp["start"]), int(hp["end"]))
    if hold is None:
        c["elbow_unlocked"] = _skipped()
    else:
        h = np.arange(*hold)
        seen = ~s.wrist_hidden[h] & np.isfinite(s.elbow[h])
        elbow_min = float(np.min(s.elbow[h][seen])) if seen.any() else None
        res = "unsure" if elbow_min is None else "fail" if elbow_min < ELBOW_MIN_DEG else "pass"
        worst = int(h[seen][int(np.argmin(s.elbow[h][seen]))]) if elbow_min is not None else None
        c["elbow_unlocked"] = _check(elbow_min, ELBOW_MIN_DEG, "deg", res, hold, worst, elbow_frames_seen=int(seen.sum()))
    if oh is None:
        c["no_standup"] = _skipped()
    elif stand is None:
        c["no_standup"] = _check(None, None, "", "fail", (int(oh["start"]), int(oh["end"])))
    else:
        c["no_standup"] = _check(None, None, "", _unsure_if(bool(s.leg_unsure[stand]), "pass"), (stand, stand), stand)
    if hold is None:
        c["hold_short"] = _skipped()
    else:
        a, e = hold
        dur = float(s.t[min(e, len(s.t) - 1)] - s.t[a])
        res = "pass" if dur >= HOLD_MIN_S else "fail"
        c["hold_short"] = _check(dur, HOLD_MIN_S, "s", _unsure_if(not s.plate_found[a:e].all(), res), hold, e - 1)
    low = _frame(rec, "bar_lowest")
    if performed == "unknown" and why == "low_confidence":
        c["type_mismatch"] = _check(None, None, "", "unsure", None if low is None else (low, low), low,
                                    performed=performed, intended=want)
    elif source == "inferred" or performed == "unknown":
        c["type_mismatch"] = _skipped()
    else:
        c["type_mismatch"] = _check(None, None, "", "pass" if performed == want else "fail",
                                    None if low is None else (low, low), low, performed=performed, intended=want)
    unsure = [k for k, v in c.items() if v["result"] == "unsure"]
    c["low_confidence"] = _check(None, None, "", "unsure" if unsure else "pass", c[unsure[0]]["frames"] if unsure else None,
                                 unsure=unsure)
    fails = [k for k in CHECKS if c[k]["result"] == "fail"]
    if fails:
        result, reason = "failed", fails[0]
    elif unsure:
        result, reason = "unknown", "low_confidence"
    else:
        result, reason = "completed", None
    return dict(attempt=int(rec["attempt"]), performed_type=performed, performed_unknown_why=why, intended_type=want,
                intended_source=source, lift_result=result, reason=reason,
                evidence_frames=None if reason is None else c[reason]["frames"], checks=c)
