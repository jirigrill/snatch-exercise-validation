import math

import numpy as np
import pytest

from snatch.phases import Rep
from snatch.spread import PHASES, phase_values, spread_table


def _reps():
    return [Rep(setup=0, transition=1, catch=2, lockout=3, overhead_start=2,
                overhead_end=4),
            Rep(setup=5, transition=None, catch=7, lockout=8, overhead_start=7,
                overhead_end=9)]


def test_phase_values_samples_each_joint_at_each_phase_frame():
    angles = {"knee": np.arange(10, dtype=float) * 10}
    vals = phase_values(angles, _reps())
    assert vals["knee"]["setup"] == [0.0, 50.0]
    assert vals["knee"]["catch"] == [20.0, 70.0]
    assert vals["knee"]["transition"][0] == 10.0
    assert math.isnan(vals["knee"]["transition"][1])  # not detected


def test_spread_is_sample_sd_and_skips_missing_reps():
    angles = {"knee": np.arange(10, dtype=float) * 10}
    table = spread_table(phase_values(angles, _reps()))
    # two values 0 and 50: sample SD = 50 / sqrt(2)
    assert table["knee"]["setup"] == pytest.approx(50 / math.sqrt(2))
    # only one detected transition: SD undefined
    assert math.isnan(table["knee"]["transition"])


def test_phases_order():
    assert PHASES == ("setup", "transition", "catch", "lockout")
