import numpy as np
import pytest

from snatch import pose
from snatch.pose import range_mask, resume_state, track_box
from snatch.stage import StageStop
from snatch.stages.pose import check_facing


def test_track_box_extends_a_truncated_detection_to_last_frames_keypoints():
    """R3: a box cut off above the knees (plate in front) grows to last frame's confident keypoints only."""
    det = np.array([100.0, 100.0, 300.0, 400.0])  # cut off above the knees
    prev_kps = np.array([[150.0, 120.0], [200.0, 600.0]])  # ankle at y=600
    prev_scores = np.array([0.9, 0.8])
    out = track_box(det, prev_kps, prev_scores, pad=0.1, min_score=0.3)
    # keypoint extent 150..200 x 120..600, padded by 10% of its size
    assert out == pytest.approx([100.0, 72.0, 300.0, 648.0])
    low = track_box(det, np.array([[150.0, 120.0], [900.0, 900.0]]), np.array([0.9, 0.1]), pad=0.0, min_score=0.3)
    assert low == pytest.approx(det)



def test_track_box_with_only_a_detection_or_only_keypoints():
    """R3: first frame (no previous pose) uses the detection; a missed detection uses last frame's keypoints."""
    det = np.array([1.0, 2.0, 3.0, 4.0])
    assert track_box(det, None, None) == pytest.approx(det)
    out = track_box(None, np.array([[150.0, 120.0], [200.0, 600.0]]), np.array([0.9, 0.8]), pad=0.1, min_score=0.3)
    assert out == pytest.approx([145.0, 72.0, 205.0, 648.0])



def test_resume_state_takes_last_seen_box_and_last_frames_keypoints():
    """R3: a resumed pose run continues from the last box and keypoints (no clip is interrupted)."""
    bbox = np.full((5, 4), np.nan)
    bbox[1] = [1, 2, 3, 4]
    kps = np.arange(5 * 2 * 2, dtype=float).reshape(5, 2, 2)
    scores = np.arange(10, dtype=float).reshape(5, 2)
    prev, pk, ps = resume_state({"bbox": bbox, "keypoints": kps, "scores": scores}, 3)
    assert prev == pytest.approx([1, 2, 3, 4])
    assert pk == pytest.approx(kps[2]) and ps == pytest.approx(scores[2])


def test_range_mask_rejects_ranges_outside_the_clip():
    """R3: attempt windows outside the clip are rejected (S5a will pass them)."""
    with pytest.raises(ValueError):
        range_mask(10, [(5, 11)])


def _fake_model(calls):
    def fake_pose(img, bboxes):
        calls.append((int(img[0, 0, 0]), bboxes[0].tolist()))
        return np.full((1, 26, 2), 50.0), np.ones((1, 26))  # far outside the box: tracking shows
    return fake_pose


def _images(n):
    return (np.full((2, 2, 3), i, np.uint8) for i in range(n))


def test_run_with_ranges_poses_only_inside_and_restarts_tracking(monkeypatch):
    """R3: posing only attempt windows restarts tracking per window (S5a; no clip drives ranges yet)."""
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


def test_run_without_a_box_follows_the_previous_keypoints(monkeypatch):
    """R3: frames without a person box follow the previous pose."""
    calls = []
    monkeypatch.setattr(pose, "load_model", lambda device: _fake_model(calls))
    boxes = np.full((4, 4), np.nan)
    boxes[0] = [0.0, 0.0, 10.0, 10.0]
    out = pose.run(_images(4), 4, boxes)
    assert [f for f, _ in calls] == [0, 1, 2, 3]
    assert np.isnan(out["bbox"][1]).all() and not np.isnan(out["bbox"][0]).any()
    assert calls[1][1] == calls[2][1] != calls[0][1]


def _feet(dxs, score=0.9):
    n = len(dxs)
    kps = np.zeros((n, 26, 2), np.float32)
    scores = np.full((n, 26), score, np.float32)
    kps[:, 25, 0] = 100
    kps[:, 21, 0] = 100 + np.asarray(dxs, np.float32)
    return kps, scores


def test_facing_split_is_none():
    """R1: a split facing vote gives no facing (S2 then exits 8)."""
    assert pose.facing(*_feet([30] * 5 + [-30] * 5)) is None


def test_facing_without_feet_or_confidence_is_none():
    """R1: no confident feet gives no facing (S2 then exits 8)."""
    assert pose.facing(np.zeros((3, 17, 2)), np.ones((3, 17))) is None
    assert pose.facing(*_feet([30] * 5, score=0.1)) is None


def test_near_side_takes_higher_scoring_leg():
    """R3: the near side is the leg with the higher scores."""
    scores = np.full((4, 26), 0.5, np.float32)
    scores[:, [12, 14, 16, 21, 23, 25]] = 0.9
    assert pose.near_side(scores) == "r"
    scores[:, [12, 14, 16, 21, 23, 25]] = 0.1
    assert pose.near_side(scores) == "l"


def test_s2_stops_with_exit_8_on_ambiguous_facing_or_a_disagreeing_near_side():
    """R1: ambiguous facing or a near side that disagrees: exit 8."""
    with pytest.raises(StageStop) as stop:
        check_facing(*_feet([30] * 5 + [-30] * 5))
    assert stop.value.code == 8
    kps, scores = _feet([30] * 10)
    assert check_facing(kps, scores)["facing"] == "right"
    scores[:, [11, 13, 15, 20, 22, 24]] = 0.95  # left leg scores higher, toes point right
    with pytest.raises(StageStop, match="mirrored") as stop:
        check_facing(kps, scores)
    assert stop.value.code == 8
