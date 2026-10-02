import numpy as np
import pytest

from snatch.pose import pick_lifter, track_box


def test_track_box_extends_a_truncated_detection_to_last_frames_keypoints():
    det = np.array([100.0, 100.0, 300.0, 400.0])  # cut off above the knees
    prev_kps = np.array([[150.0, 120.0], [200.0, 600.0]])  # ankle at y=600
    prev_scores = np.array([0.9, 0.8])
    out = track_box(det, prev_kps, prev_scores, pad=0.1, min_score=0.3)
    # keypoint extent 150..200 x 120..600, padded by 10% of its size
    assert out == pytest.approx([100.0, 72.0, 300.0, 648.0])


def test_track_box_ignores_low_confidence_keypoints():
    det = np.array([100.0, 100.0, 300.0, 400.0])
    prev_kps = np.array([[150.0, 120.0], [900.0, 900.0]])
    prev_scores = np.array([0.9, 0.1])
    out = track_box(det, prev_kps, prev_scores, pad=0.0, min_score=0.3)
    assert out == pytest.approx(det)


def test_track_box_without_previous_frame_is_the_detection():
    det = np.array([1.0, 2.0, 3.0, 4.0])
    assert track_box(det, None, None) == pytest.approx(det)


def test_pick_lifter_prefers_the_box_overlapping_the_previous_one():
    boxes = np.array([[0, 0, 100, 100], [500, 500, 900, 900]], float)
    prev = np.array([10, 10, 110, 110], float)
    assert pick_lifter(boxes, prev) == pytest.approx(boxes[0])
    assert pick_lifter(boxes, None) == pytest.approx(boxes[1])
