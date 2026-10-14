import numpy as np
import pytest

from snatch import person
from snatch.person import pick_lifter


def test_pick_lifter_prefers_the_box_overlapping_the_previous_one():
    """R3: with another person in frame the lifter is the box overlapping the last one (test clips have one person)."""
    boxes = np.array([[0, 0, 100, 100], [500, 500, 900, 900]], float)
    prev = np.array([10, 10, 110, 110], float)
    assert pick_lifter(boxes, prev) == pytest.approx(boxes[0])
    assert pick_lifter(boxes, None) == pytest.approx(boxes[1])


def test_interpolate_boxes_without_any_box_stays_nan():
    """R3: a clip where the detector never finds anyone stays NaN, no crash."""
    assert np.isnan(person.interpolate_boxes(np.full((3, 4), np.nan, np.float32))).all()


def test_gaps_mark_frames_interpolated_across_a_missed_detection():
    """R3: frames bridged across a missed detection are marked (no test clip misses one)."""
    detected = np.zeros(100, bool)
    detected[[0, 24, 72, 96]] = True  # the run at 48 missed; 97-99 follow the last run
    gap = person.gaps(detected, every=24)
    assert np.flatnonzero(gap).tolist() == list(range(36, 60))
    assert person.gaps(np.zeros(5, bool), every=24).all()
