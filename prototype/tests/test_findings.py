"""R3: the S9 rule table on synthetic tracks — B5/B6 start at setup, B4/B6 use the highest hub, the A1 range and A4
sign, and the skip paths for a missing border and an unsure joint. No test clip isolates a wrong baseline or a
second bar peak; the clips show the normal path only."""

import numpy as np
import pytest

from snatch.findings import FAULTS, PLATE_RADIUS_M, Body, Track, metrics, rules

N = 100  # frames at 100 fps; window 0-100, borders as in the S7 phase model
LO, FK, DR, FE, BP, BL, ST, HOLD_END = 10, 20, 25, 30, 50, 60, 70, 90
HEIGHT_M = 2.0
PPM = 100.0


def _case(*, x_setup: float = 100.0, x_liftoff: float = 100.0, x_lowest: float = 100.0,
          y_setup: float = 1000.0, y_liftoff: float = 1000.0, y_peak: float = 600.0, y_lowest: float = 620.0,
          shoulder_x: float = 100.0, hip_x: float = 280.0, shoulder_why: str = "", hip_why: str = "",
          bar_peak: bool = True, bar_lowest: bool = True) -> tuple[dict, Track, Body]:
    hub_x = np.full(N, x_liftoff)
    hub_x[:LO + 1] = np.linspace(x_setup, x_liftoff, LO + 1)
    hub_x[BP:BL + 1] = np.linspace(x_liftoff, x_lowest, BL - BP + 1)
    hub_x[BL:] = x_lowest
    hub_y = np.full(N, y_setup)
    hub_y[:LO + 1] = np.linspace(y_setup, y_liftoff, LO + 1)
    hub_y[LO:BP + 1] = np.linspace(y_liftoff, y_peak, BP - LO + 1)
    hub_y[BP:BL + 1] = np.linspace(y_peak, y_lowest, BL - BP + 1)
    hub_y[BL:] = y_lowest
    track = Track(hub_x, hub_y, np.ones(N, bool), np.full(N, PPM))
    sw, hw = [""] * N, [""] * N
    sw[LO], hw[LO] = shoulder_why, hip_why
    body = Body(np.tile([shoulder_x, 500.0], (N, 1)), np.tile([hip_x, 700.0], (N, 1)), sw, hw, np.arange(N) / PPM)
    borders = {"liftoff": {"frame": LO}, "first_knee_max": {"frame": FK}, "deepest_rebend": {"frame": DR},
               "full_extension": {"frame": FE}, "bar_peak": {"frame": BP} if bar_peak else None,
               "bar_lowest": {"frame": BL} if bar_lowest else None, "standing": {"frame": ST}}
    rec = dict(attempt=1, window=[0, N], bar_overhead={"start": 40, "end": HOLD_END}, borders=borders,
               phases=[dict(name="hold", start=ST, end=HOLD_END)])
    return rec, track, body


def _run(rec: dict, track: Track, body: Body) -> tuple[dict, dict, dict, list[dict]]:
    ms = metrics(rec, track, 1, HEIGHT_M)
    findings, checked, skipped = rules(rec, ms, track, body, 1, HEIGHT_M)
    assert sorted([c["fault"] for c in checked] + [s["fault"] for s in skipped]) == sorted(FAULTS)
    return ms, {c["fault"]: c for c in checked}, {s["fault"]: s for s in skipped}, findings


def test_b5_b6_start_at_setup() -> None:
    """B5 is setup to bar catch (30 cm), not liftoff to bar catch (15 cm); B6 is setup to peak plus the plate radius
    (86.25 % of height), not liftoff to peak (25 %)."""
    rec, tr, body = _case(x_setup=85.0, x_liftoff=100.0, x_lowest=115.0,
                          y_setup=1000.0, y_liftoff=900.0, y_peak=850.0, y_lowest=870.0)
    ms, ck, _, findings = _run(rec, tr, body)
    assert ms["net_x_cm"]["value"] == pytest.approx(30.0)
    assert ms["catch_x_cm"]["value"] == pytest.approx(15.0)  # the old baseline: below the 17 cm rule
    assert ck["catch_jump"]["value"] == pytest.approx(30.0) and ck["catch_jump"]["found"]
    assert ms["peak_rise_pct"]["value"] == pytest.approx(75.0)
    assert ms["peak_height_pct"]["value"] == pytest.approx(25.0)  # the old baseline: below the 85 % rule
    assert ck["pulled_too_high"]["value"] == pytest.approx(75.0 + 100 * PLATE_RADIUS_M / HEIGHT_M)
    assert ck["pulled_too_high"]["found"]
    assert {f["fault"] for f in findings} >= {"catch_jump", "pulled_too_high"}


def test_b4_b6_use_highest_hub() -> None:
    """B4/B6 start from the highest hub (min hub_y), which can be after S7's first bar_peak border."""
    rec, tr, body = _case(x_liftoff=100.0, x_lowest=90.0, y_setup=1000.0, y_liftoff=1000.0,
                          y_peak=850.0, y_lowest=870.0)
    tr.hub_y[BP + 5] = 840.0  # higher than the bar_peak border
    tr.hub_x[BP + 5] = 120.0  # and farther forward, so B4 must start here
    ms, ck, _, findings = _run(rec, tr, body)
    assert ms["peak_rise_pct"]["frames"] == [0, BP + 5]
    assert ms["peak_rise_pct"]["at"] == BP + 5
    assert ms["peak_rise_pct"]["value"] == pytest.approx(80.0)
    assert ck["pulled_too_high"]["value"] == pytest.approx(80.0 + 100 * PLATE_RADIUS_M / HEIGHT_M)
    assert ck["big_loop"]["value"] == pytest.approx(30.0) and ck["big_loop"]["found"]
    ev = {f["fault"]: f["evidence_frames"] for f in findings}
    assert ev["pulled_too_high"] == [0, BP + 5]
    assert ev["big_loop"] == [BP + 5, BL]
    assert {f["fault"] for f in findings} >= {"big_loop", "pulled_too_high"}


@pytest.mark.parametrize("fault, kw, value, found", [
    ("catch_jump", dict(x_setup=100.0, x_liftoff=100.0, x_lowest=117.0), 17.0, False),
    ("pulled_too_high", dict(y_setup=1000.0, y_liftoff=1000.0, y_peak=852.5, y_lowest=852.5), 85.0, False),
    ("pulled_too_high", dict(y_setup=1000.0, y_liftoff=1000.0, y_peak=850.0, y_lowest=850.0), 86.25, True),
    ("bad_start_back_angle", dict(hip_x=280.0), 41.987, False),
    ("bad_start_back_angle", dict(hip_x=200.0), 26.565, True),
    ("shoulders_behind_bar", dict(shoulder_x=120.0), 20.0, False),
    ("shoulders_behind_bar", dict(shoulder_x=80.0), -20.0, True),
])
def test_s9_rule_table(fault: str, kw: dict, value: float, found: bool) -> None:
    """The threshold edge is not a fault (A1 is a range, A4 is < 0, the rest are >)."""
    rec, tr, body = _case(**kw)
    _, ck, _, _ = _run(rec, tr, body)
    assert ck[fault]["value"] == pytest.approx(value, abs=1e-3)
    assert ck[fault]["found"] is found


@pytest.mark.parametrize("kw, fault, reason", [
    (dict(bar_lowest=False), "catch_jump", "net_x_cm null: bar_lowest"),
    (dict(bar_lowest=False), "pulled_too_high", "peak_rise_pct null: bar_lowest"),
    (dict(bar_peak=False), "two_peak_pull", "missing border bar_peak"),
    (dict(shoulder_why="hidden"), "bad_start_back_angle", "at liftoff: shoulder hidden"),
    (dict(shoulder_why="hidden"), "shoulders_behind_bar", "at liftoff: shoulder hidden"),
])
def test_s9_skips(kw: dict, fault: str, reason: str) -> None:
    """A missing border or an unsure joint is skipped with the reason, never found."""
    rec, tr, body = _case(**kw)
    _, ck, sk, findings = _run(rec, tr, body)
    assert fault not in ck and fault not in {f["fault"] for f in findings}
    assert sk[fault]["reason"] == reason
