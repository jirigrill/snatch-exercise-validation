import numpy as np
import pytest

from snatch import person
from snatch.person import pick_lifter, sparse_detections


def test_pick_lifter_prefers_the_box_overlapping_the_previous_one():
    boxes = np.array([[0, 0, 100, 100], [500, 500, 900, 900]], float)
    prev = np.array([10, 10, 110, 110], float)
    assert pick_lifter(boxes, prev) == pytest.approx(boxes[0])
    assert pick_lifter(boxes, None) == pytest.approx(boxes[1])


def test_sparse_detection_mask_keeps_every_nth_box():
    boxes = np.arange(40, dtype=float).reshape(10, 4)
    out = sparse_detections(boxes, every=4)
    kept = ~np.isnan(out).any(1)
    assert np.flatnonzero(kept).tolist() == [0, 4, 8]
    assert out[4] == pytest.approx(boxes[4])


def test_interpolate_boxes_draws_a_line_between_detections_and_holds_the_ends():
    boxes = np.full((9, 4), np.nan, np.float32)
    boxes[2] = [0, 0, 10, 10]
    boxes[6] = [4, 8, 14, 18]
    out = person.interpolate_boxes(boxes)
    assert out[2].tolist() == [0, 0, 10, 10] and out[6].tolist() == [4, 8, 14, 18]
    assert out[4].tolist() == [2, 4, 12, 14]  # halfway
    assert out[0].tolist() == out[2].tolist() and out[8].tolist() == out[6].tolist()


def test_interpolate_boxes_without_any_box_stays_nan():
    assert np.isnan(person.interpolate_boxes(np.full((3, 4), np.nan, np.float32))).all()


def test_detect_boxes_runs_the_detector_every_nth_frame_and_follows_the_lifter():
    lifter = np.array([100.0, 100.0, 200.0, 200.0])
    bystander = np.array([300.0, 0.0, 500.0, 400.0])
    calls = []

    def det(img):
        i = int(img[0, 0, 0])
        calls.append(i)
        return np.array([lifter] if i < 4 else [lifter, bystander])

    images = (np.full((2, 2, 3), i, np.uint8) for i in range(10))
    boxes, n_people = person.detect_boxes(images, 10, 4, det)
    assert calls == [0, 4, 8]
    assert n_people.tolist() == [1, 0, 0, 0, 2, 0, 0, 0, 2, 0]
    assert boxes[4].tolist() == boxes[8].tolist() == lifter.tolist()  # not the larger bystander
    assert np.isnan(boxes[1]).all()



def test_detect_returns_interpolated_boxes_and_marks_the_detected_frames():
    lifter = np.array([100.0, 100.0, 200.0, 200.0])

    def det(img):
        i = int(img[0, 0, 0])
        return np.array([lifter + i])  # the box moves 1 px per frame

    images = (np.full((2, 2, 3), i, np.uint8) for i in range(9))
    out = person.detect(images, 9, 4, det)
    assert out["detected"].tolist() == [True, False, False, False, True, False, False, False, True]
    assert out["bbox"][2].tolist() == pytest.approx((lifter + 2).tolist())  # on the line
    assert out["n_people"].tolist() == [1, 0, 0, 0, 1, 0, 0, 0, 1]


def test_gaps_mark_frames_interpolated_across_a_missed_detection():
    detected = np.zeros(100, bool)
    detected[[0, 24, 72, 96]] = True  # the run at 48 missed; 97-99 follow the last run
    gap = person.gaps(detected, every=24)
    assert np.flatnonzero(gap).tolist() == list(range(36, 60))
    assert person.gaps(np.zeros(5, bool), every=24).all()
