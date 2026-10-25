"""S9 bar-path metrics of one attempt (rules in .scratch/plan/D-judge.md, "S9 findings").

Pure: the plate hub track, the S7 borders, the facing and the athlete height in, the 6 metrics out. x is signed by
facing (+ = away from the lifter, i.e. forward), heights are up. cm via the plate scale px_per_m (median over the
attempt window's found frames, as S7). Each metric: {value, value_px, unit, frames [start, end] (the found
frames the hub is read at: nearest to each border within the span), at (the arrow tip), missing (borders, or
plate@<border> when the span has no found plate frame)}; x metrics are from the hub x at the start border. No thresholds: `findings` stays empty until plan item "S9 rules".
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
