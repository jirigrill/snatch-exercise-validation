import numpy as np
import pytest

from snatch.judge import Signals, judge

N = 400  # frames at 100 fps; window 0-400, liftoff 20, full_extension 100, bar_peak 130, bar_lowest 160, standing 220
LOW, STAND, END = 160, 220, 360


def _case(*, knee_low: float = 100.0, hip_below: bool = False, overhead: bool = True, standing: bool = True,
          hold_end: int = END, elbow: float = 175.0, wrist_seen: bool = True,
          filled_low: bool = False, filled_stand: bool = False, plate_lost: bool = False) -> tuple[dict, Signals]:
    f = np.arange(N)
    knee = np.interp(f, [0, 100, 130, LOW, STAND, N], [90, 175, 170, knee_low, 175, 175])
    found = np.ones(N, bool)
    if plate_lost:
        found[STAND + 30:STAND + 40] = False
    unsure = np.zeros(N, bool)
    unsure[LOW] = filled_low
    unsure[STAND] = filled_stand
    s = Signals(t=f / 100, knee=knee, elbow=np.full(N, elbow), wrist_hidden=np.full(N, not wrist_seen), leg_unsure=unsure,
                hip_y=np.where((f == LOW) & hip_below, 700.0, 500.0), knee_y=np.full(N, 650.0),
                plate_found=found)
    b = dict(liftoff=20, first_knee_max=None, deepest_rebend=None, full_extension=100, bar_peak=130,
             bar_lowest=LOW if overhead else None, standing=STAND if overhead and standing else None)
    rec = dict(attempt=1, window=[0, N], bar_overhead=dict(start=120, end=hold_end) if overhead else None,
               borders={k: None if v is None else dict(frame=v) for k, v in b.items()},
               phases=[dict(name="hold", start=b["standing"], end=hold_end if b["standing"] else None)])
    return rec, s


@pytest.mark.parametrize("kw, intended, want", [
    (dict(), "power", ("power", "completed", None)),
    (dict(hip_below=True), "squat", ("squat", "completed", None)),
    (dict(knee_low=170.0), "muscle", ("muscle", "completed", None)),
    (dict(overhead=False), "power", ("unknown", "failed", "no_overhead")),
    (dict(elbow=150.0), "power", ("power", "failed", "elbow_unlocked")),
    (dict(wrist_seen=False), "power", ("power", "unknown", "low_confidence")),
    (dict(standing=False), "power", ("power", "failed", "no_standup")),
    (dict(hold_end=STAND + 40), "power", ("power", "failed", "hold_short")),
    (dict(), "squat", ("power", "failed", "type_mismatch")),
    (dict(filled_low=True), "power", ("unknown", "unknown", "low_confidence")),
    (dict(filled_low=True), None, ("unknown", "unknown", "low_confidence")),
    (dict(filled_stand=True), "power", ("power", "unknown", "low_confidence")),
    (dict(plate_lost=True), "power", ("power", "unknown", "low_confidence")),
    (dict(plate_lost=True, elbow=150.0), "power", ("power", "failed", "elbow_unlocked")),
    (dict(), None, ("power", "completed", None)),
])
def test_judge_rule_table(kw: dict, intended: str | None, want: tuple) -> None:
    """R4: the S8 judge rule table, one synthetic attempt per reason and per performed type (elbow: min over hold frames with
    the wrist seen; wrist hidden on every hold frame = unsure) (muscle, power, squat,
    unknown: no overhead or hip/knee filled at bar_lowest = type_mismatch unsure; filled at standing = no_standup unsure; plate lost in the hold = hold_short unsure). A clear fail on seen frames beats an unsure (plate lost);
    no label = inferred, so type_mismatch is skipped."""
    rec, s = _case(**kw)
    j = judge(rec, s, label=intended)
    assert (j["performed_type"], j["lift_result"], j["reason"]) == want
    assert j["intended_source"] == ("labels" if intended else "inferred")
