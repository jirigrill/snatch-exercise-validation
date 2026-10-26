"""S9 bar-path metrics of one attempt (rules in .scratch/plan/D-judge.md, "S9 findings").

Pure: the plate hub track, the S7 borders, the facing and the athlete height in, the 6 metrics out. x is signed by
facing (+ = away from the lifter, i.e. forward), heights are up. cm via the plate scale px_per_m (median over the
attempt window's found frames, as S7). Each metric: {value, value_px, unit, frames [start, end] (the found
frames the hub is read at: nearest to each border within the span), at (the arrow tip), missing (borders, or
plate@<border> when the span has no found plate frame)}; x metrics are from the hub x at the start border. Rules (`rules`) below the metrics.
"""

from dataclasses import dataclass

import numpy as np

# name: (unit, start border, end border, extra borders that must exist)
METRICS: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "pull1_away_cm": ("cm", "liftoff", "first_knee_max", ()),
    "pull2_toward_cm": ("cm", "first_knee_max", "full_extension", ()),
    "loop_away_cm": ("cm", "full_extension", "bar_lowest", ()),
    "peak_height_pct": ("%", "liftoff", "bar_peak", ("bar_overhead",)),
    "drop_under_cm": ("cm", "bar_peak", "bar_lowest", ("bar_overhead",)),
    "catch_x_cm": ("cm", "liftoff", "bar_lowest", ("bar_overhead",)),
}


@dataclass(frozen=True)
class Track:
    hub_x: np.ndarray
    hub_y: np.ndarray
    found: np.ndarray
    px_per_m: np.ndarray


def scale(track: Track, window: tuple[int, int]) -> float | None:
    """px per m: median plate scale over the window's found frames; None without one."""
    s, e = window
    v = track.px_per_m[s:e][track.found[s:e]]
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else None


def _num(v: float) -> float | None:
    return round(float(v), 3) if np.isfinite(v) else None


def metrics(rec: dict, track: Track, sign: int, height_m: float) -> dict[str, dict]:
    """rec = one phases.json attempt; sign = +1 facing right, -1 facing left."""
    b = {k: (v["frame"] if v else None) for k, v in rec["borders"].items()}
    have = {**b, "bar_overhead": 0 if rec["bar_overhead"] else None}
    ppm = scale(track, (rec["window"][0], rec["window"][1]))
    def x(i: int) -> float:
        return sign * float(track.hub_x[i])

    def up(i: int) -> float:
        return -float(track.hub_y[i])

    def near(i: int, s: int, e: int) -> int | None:
        """The found frame in s..e nearest to i (the hub at a border when the plate is lost there)."""
        ok = [j for j in range(s, e + 1) if track.found[j]]
        return min(ok, key=lambda j: (abs(j - i), j)) if ok else None

    def span_max(s: int, e: int, s2: int = 1) -> tuple[float, int]:
        """Max of s2 * (x - x at s) over the found frames of s..e and its frame (the arrow tip); s is found."""
        return max((s2 * (x(i) - x(s)), i) for i in range(s, e + 1) if track.found[i])

    def value(name: str, s: int, e: int) -> tuple[float, int]:
        if name == "pull2_toward_cm":
            return span_max(s, e, -1)
        if name in ("pull1_away_cm", "loop_away_cm"):
            return span_max(s, e)
        if name == "peak_height_pct":
            return up(e) - up(s), e
        if name == "drop_under_cm":
            return up(s) - up(e), e
        return x(e) - x(s), e  # catch_x_cm

    out = {}
    for name, (unit, s_b, e_b, extra) in METRICS.items():
        missing = [n for n in (s_b, e_b, *extra) if have.get(n) is None]
        s, e = b.get(s_b), b.get(e_b)
        rec_m: dict = dict(value=None, value_px=None, unit=unit, frames=None if s is None or e is None else [s, e],
                           at=None, missing=missing)
        if not missing and s is not None and e is not None:
            fs, fe = near(s, s, e), near(e, s, e)
            if fs is None or fe is None:
                missing += [f"plate@{s_b}", f"plate@{e_b}"]
            else:
                px, at = value(name, fs, fe)
                rec_m["frames"], rec_m["at"], rec_m["value_px"] = [fs, fe], int(at), _num(px)
                if ppm is not None:
                    m = px / ppm
                    rec_m["value"] = _num(100 * m / height_m if unit == "%" else 100 * m)
        out[name] = rec_m
    return out


# S9 rules (.scratch/plan/D-judge.md "S9 rules"; markers in docs/research/11-technique-markers.md). Every finding is a
# warning: no source says one of these faults costs the lift. Thresholds are the sources' ranges, not fitted to clips.
X2_MAX_CM = 14.0  # B3: Shah, X2 3-14 cm
XLOOP_MAX_CM = 12.0  # B4: Shah, Xloop 3-12 cm
XNET_MAX_CM = 17.0  # B5: Shah, Xnet 0-17 cm
PEAK_MAX_PCT = 85.0  # B6: Shah, peak bar height 70-85 % of body height
PLATE_RADIUS_M = 0.225  # B6: the bar axis sits one plate radius (450 mm plate, assumed) above the floor at rest
DROP_MAX_CM = 25.0  # B8: Shah, Ydrop 6.5-25 cm
TRUNK_DEG = (40.0, 65.0)  # A1: Soviet norm, trunk 25-50 deg to the platform = 40-65 deg from vertical (10b)
SHOULDER_AHEAD_CM = 0.0  # A4: coaching cue, shoulder over or ahead of the bar; no number
# E3: no source. 2 cm hub SD (max of x, y): standing with the bar at the hips the hub sways 3.5 cm peak to peak
# (marker E3 reference, #14), an SD of about 1 cm; twice that is sway beyond standing still.
HOLD_SD_MAX_CM = 2.0
# C2: no source gives a dip depth; a dip shallower than this is taken as smoothing noise (0.1 s savgol on the hub).
DIP_MIN_M_S = 0.05

FAULTS = ("bar_away_second_pull", "big_loop", "catch_jump", "pulled_too_high", "deep_drop", "two_peak_pull",
          "bad_start_back_angle", "shoulders_behind_bar", "unstable_overhead")


@dataclass(frozen=True)
class Body:
    """Near-side shoulder and hip x/y (S6 pose.npz) per frame, why each is unsure ('filled' / 'hidden' / ''), frame times."""
    shoulder: np.ndarray  # (n, 2)
    hip: np.ndarray  # (n, 2)
    shoulder_why: list[str]
    hip_why: list[str]
    t: np.ndarray


def _hold(rec: dict) -> tuple[int, int] | None:
    ph = next((p for p in rec["phases"] if p["name"] == "hold"), None)
    return (ph["start"], ph["end"]) if ph and ph["start"] is not None and ph["end"] is not None else None


def rules(rec: dict, ms: dict[str, dict], track: Track, body: Body, sign: int, height_m: float
          ) -> tuple[list[dict], list[dict], list[dict]]:
    """(findings, checked, skipped) of one attempt: each fault in FAULTS is in checked (evaluated; found or not) or in
    skipped (with the reason). ms = metrics(rec, ...)."""
    from snatch.signals import smooth

    b: dict[str, int] = {k: int(v["frame"]) for k, v in rec["borders"].items() if v}
    ppm = scale(track, (rec["window"][0], rec["window"][1]))
    findings: list[dict] = []
    checked: list[dict] = []
    skipped: list[dict] = []

    def skip(fault: str, reason: str) -> None:
        skipped.append(dict(fault=fault, reason=reason))

    def judge(fault: str, phase: str, value: float, threshold, unit: str, bad: bool, frames: list[int]) -> None:
        v = round(float(value), 3)
        checked.append(dict(fault=fault, value=v, threshold=threshold, unit=unit, found=bool(bad)))
        if bad:
            findings.append(dict(phase=phase, fault=fault, severity="warning", value=v, threshold=threshold,
                                 evidence_frames=[int(f) for f in frames]))

    def need(fault: str, *borders: str) -> bool:
        miss = [n for n in borders if b.get(n) is None]
        if miss:
            skip(fault, "missing border " + ",".join(miss))
        elif ppm is None:
            skip(fault, "no px_per_m (no plate frame in the window)")
        return not miss and ppm is not None

    def found_in(s: int, e: int) -> list[int]:
        return [i for i in range(s, e + 1) if track.found[i]]

    def x(i: int) -> float:
        return sign * float(track.hub_x[i])

    def span(fault: str, s_b: str, e_b: str, s2: int) -> tuple[float, int, int] | None:
        """max of s2 * (x - x at the first found frame) over s_b..e_b in cm, its frame, the start frame."""
        if not need(fault, s_b, e_b):
            return None
        idx = found_in(b[s_b], b[e_b])
        if not idx:
            skip(fault, f"no plate frame in {s_b}..{e_b}")
            return None
        v, at = max((s2 * (x(i) - x(idx[0])), i) for i in idx)
        return 100 * v / ppm, at, idx[0]  # type: ignore[operator]

    # B3: forward travel from the start of the second pull (X1 ~ first_knee_max) to the peak height
    r = span("bar_away_second_pull", "first_knee_max", "bar_peak", 1)
    if r:
        judge("bar_away_second_pull", "second_pull", r[0], X2_MAX_CM, "cm", r[0] > X2_MAX_CM, [r[2], r[1]])
    # B4: back toward the lifter from the peak height to the catch
    r = span("big_loop", "bar_peak", "bar_lowest", -1)
    if r:
        judge("big_loop", "turnover+catch", r[0], XLOOP_MAX_CM, "cm", r[0] > XLOOP_MAX_CM, [r[2], r[1]])
    for fault, name, phase, thr, unit, f in (
            ("catch_jump", "catch_x_cm", "catch", XNET_MAX_CM, "cm", abs),
            ("pulled_too_high", "peak_height_pct", "turnover", PEAK_MAX_PCT, "%",
             lambda v: v + 100 * PLATE_RADIUS_M / height_m),
            ("deep_drop", "drop_under_cm", "catch", DROP_MAX_CM, "cm", lambda v: v)):
        m = ms[name]
        if m["value"] is None:
            skip(fault, f"{name} null: " + (",".join(m["missing"]) or "no px_per_m in the window"))
        else:
            v = f(m["value"])
            judge(fault, phase, v, thr, unit, v > thr, list(m["frames"]))
    # C2: a dip in the vertical bar speed between liftoff and the peak speed (before bar_peak)
    if need("two_peak_pull", "liftoff", "bar_peak"):
        s, e = b["liftoff"], b["bar_peak"]
        if not track.found[s:e + 1].all():
            skip("two_peak_pull", f"plate lost in liftoff..bar_peak ({int((~track.found[s:e + 1]).sum())} frames)")
        else:
            t = body.t[s:e + 1]
            up = smooth(-track.hub_y[s:e + 1].astype(float), t=t) / ppm  # type: ignore[operator]
            vy = np.gradient(up, t)
            k = int(np.argmax(vy))
            run_max, depth, at = -np.inf, 0.0, s
            for i in range(k + 1):
                run_max = max(run_max, vy[i])
                if run_max - vy[i] > depth:
                    depth, at = float(run_max - vy[i]), s + i
            judge("two_peak_pull", "first_pull..second_pull", depth, DIP_MIN_M_S, "m/s", depth > DIP_MIN_M_S,
                  [at, s + k])
    # A1 + A4 at liftoff: the S6-filled pose; a filled or hidden shoulder / hip is not used
    lo = b.get("liftoff")
    if lo is None:
        skip("bad_start_back_angle", "missing border liftoff")
        skip("shoulders_behind_bar", "missing border liftoff")
    else:
        why = [f"{n} {w}" for n, w in (("shoulder", body.shoulder_why[lo]), ("hip", body.hip_why[lo])) if w]
        sh, hp = body.shoulder[lo], body.hip[lo]
        if why or not np.isfinite([*sh, *hp]).all():
            skip("bad_start_back_angle", "at liftoff: " + (",".join(why) or "no pose"))
        else:
            deg = float(np.degrees(np.arctan2(abs(sh[0] - hp[0]), hp[1] - sh[1])))
            judge("bad_start_back_angle", "starting_position", deg, list(TRUNK_DEG), "deg",
                  not TRUNK_DEG[0] <= deg <= TRUNK_DEG[1], [lo])
        sw = body.shoulder_why[lo]
        if sw or not np.isfinite(sh).all():
            skip("shoulders_behind_bar", f"at liftoff: shoulder {sw or 'no pose'}")
        elif not track.found[lo]:
            skip("shoulders_behind_bar", "no plate frame at liftoff")
        elif ppm is None:
            skip("shoulders_behind_bar", "no px_per_m (no plate frame in the window)")
        else:
            d = 100 * sign * (float(sh[0]) - float(track.hub_x[lo])) / ppm
            judge("shoulders_behind_bar", "starting_position", d, SHOULDER_AHEAD_CM, "cm", d < SHOULDER_AHEAD_CM, [lo])
    # E3: hub SD over the S7 hold phase
    hold = _hold(rec)
    if hold is None:
        skip("unstable_overhead", "no hold phase")
    elif ppm is None:
        skip("unstable_overhead", "no px_per_m (no plate frame in the window)")
    else:
        idx = found_in(hold[0], hold[1] - 1)
        if len(idx) < 2:
            skip("unstable_overhead", "no plate frame in the hold")
        else:
            sd = 100 * max(float(np.std(track.hub_x[idx])), float(np.std(track.hub_y[idx]))) / ppm
            judge("unstable_overhead", "hold", sd, HOLD_SD_MAX_CM, "cm", sd > HOLD_SD_MAX_CM, [hold[0], hold[1] - 1])
    order = {f: k for k, f in enumerate(FAULTS)}
    checked.sort(key=lambda c: order[c["fault"]])
    skipped.sort(key=lambda c: order[c["fault"]])
    return findings, checked, skipped
