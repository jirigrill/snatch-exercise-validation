"""Spread of joint angles across reps at the same lift phase."""

import math

import numpy as np

from snatch.phases import Rep

PHASES = ("setup", "transition", "catch", "lockout")

Values = dict[str, dict[str, list[float]]]  # joint -> phase -> one per rep


def phase_values(angles: dict[str, np.ndarray], reps: list[Rep]) -> Values:
    def at(series: np.ndarray, frame: int | None) -> float:
        return math.nan if frame is None else float(series[frame])

    return {joint: {ph: [at(series, getattr(r, ph)) for r in reps]
                    for ph in PHASES}
            for joint, series in angles.items()}


def spread_table(values: Values) -> dict[str, dict[str, float]]:
    """Sample SD (ddof=1) across reps; NaN if fewer than 2 reps have a value."""
    def sd(xs: list[float]) -> float:
        xs = [x for x in xs if not math.isnan(x)]
        return float(np.std(xs, ddof=1)) if len(xs) >= 2 else math.nan

    return {joint: {ph: sd(xs) for ph, xs in by_phase.items()}
            for joint, by_phase in values.items()}
