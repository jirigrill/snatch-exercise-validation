import numpy as np
import pytest

from snatch import pose
from snatch.pose import range_mask, resume_state, track_box


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


def test_track_box_without_a_detection_uses_last_frames_keypoints():
    prev_kps = np.array([[150.0, 120.0], [200.0, 600.0]])
    prev_scores = np.array([0.9, 0.8])
    out = track_box(None, prev_kps, prev_scores, pad=0.1, min_score=0.3)
    assert out == pytest.approx([145.0, 72.0, 205.0, 648.0])


def test_resume_state_takes_last_seen_box_and_last_frames_keypoints():
    bbox = np.full((5, 4), np.nan)
    bbox[1] = [1, 2, 3, 4]
    kps = np.arange(5 * 2 * 2, dtype=float).reshape(5, 2, 2)
    scores = np.arange(10, dtype=float).reshape(5, 2)
    prev, pk, ps = resume_state({"bbox": bbox, "keypoints": kps, "scores": scores}, 3)
    assert prev == pytest.approx([1, 2, 3, 4])
    assert pk == pytest.approx(kps[2]) and ps == pytest.approx(scores[2])


def test_resume_state_from_scratch_is_empty():
    assert resume_state({}, 0) == (None, None, None)


def test_range_mask_marks_half_open_ranges():
    assert np.flatnonzero(range_mask(10, [(1, 3), (6, 8)])).tolist() == [1, 2, 6, 7]
    assert range_mask(4, None).all()


def test_range_mask_rejects_ranges_outside_the_clip():
    with pytest.raises(ValueError):
        range_mask(10, [(5, 11)])


def _fake_model(calls):
    def fake_pose(img, bboxes):
        calls.append((int(img[0, 0, 0]), bboxes[0].tolist()))
        return np.full((1, 17, 2), 50.0), np.ones((1, 17))  # far outside the box: tracking shows
    return fake_pose


def _images(n):
    return (np.full((2, 2, 3), i, np.uint8) for i in range(n))


def test_run_with_ranges_poses_only_inside_and_restarts_tracking(monkeypatch):
    calls = []
    monkeypatch.setattr(pose, "load_model", lambda device: _fake_model(calls))
    boxes = np.tile([0.0, 0.0, 10.0, 10.0], (10, 1))
    out = pose.run(_images(10), 10, boxes, ranges=[(2, 4), (7, 9)])
    assert [f for f, _ in calls] == [2, 3, 7, 8]
    posed = ~np.isnan(out["keypoints"][:, 0, 0])
    assert np.flatnonzero(posed).tolist() == [2, 3, 7, 8]
    # first frame of each range: the box alone; second: the box merged with the pose
    assert calls[0][1] == calls[2][1] == [0.0, 0.0, 10.0, 10.0]
    assert calls[1][1] != calls[0][1] and calls[3][1] == calls[1][1]


def test_sparse_run_with_restart_gap_keeps_following_the_previous_pose(monkeypatch):
    calls = []
    monkeypatch.setattr(pose, "load_model", lambda device: _fake_model(calls))
    boxes = np.tile([0.0, 0.0, 10.0, 10.0], (24, 1))
    sparse = [(i, i + 1) for i in range(0, 24, 8)]
    pose.run(_images(24), 24, boxes, ranges=sparse, restart_gap=8)
    assert calls[0][1] == [0.0, 0.0, 10.0, 10.0]
    assert calls[1][1] != calls[0][1] and calls[2][1] == calls[1][1]  # not reset at each sample
    calls.clear()
    pose.run(_images(24), 24, boxes, ranges=sparse)  # default: restart at each sample
    assert all(c[1] == [0.0, 0.0, 10.0, 10.0] for c in calls)


def test_run_without_a_box_follows_the_previous_keypoints(monkeypatch):
    calls = []
    monkeypatch.setattr(pose, "load_model", lambda device: _fake_model(calls))
    boxes = np.full((4, 4), np.nan)
    boxes[0] = [0.0, 0.0, 10.0, 10.0]
    out = pose.run(_images(4), 4, boxes)
    assert [f for f, _ in calls] == [0, 1, 2, 3]
    assert np.isnan(out["bbox"][1]).all() and not np.isnan(out["bbox"][0]).any()
    assert calls[1][1] == calls[2][1] != calls[0][1]


def test_run_rejects_boxes_of_the_wrong_length():
    with pytest.raises(ValueError):
        pose.run(_images(3), 3, np.zeros((2, 4)))
