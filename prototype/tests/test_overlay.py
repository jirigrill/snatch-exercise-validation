import numpy as np

from snatch import overlay


def _run(posed):
    k = np.full((len(posed), 17, 2), np.nan, np.float32)
    k[np.asarray(posed, bool)] = 1.0
    return {"keypoints": k}


def test_shown_frames_are_those_posed_in_every_run_in_range_and_every_nth():
    a, b = _run([1, 1, 1, 1, 1, 1, 0, 0]), _run([0, 1, 1, 1, 1, 1, 1, 0])
    assert overlay.shown_frames(8, 0, None, 1, [a, b], None).tolist() == [1, 2, 3, 4, 5]
    assert overlay.shown_frames(8, 2, 5, 1, [a, b], None).tolist() == [2, 3, 4]
    assert overlay.shown_frames(8, 0, None, 2, [a, b], None).tolist() == [1, 3, 5]


def test_shown_frames_without_poses_follow_the_plate_found_or_all():
    plate = {"found": np.array([0, 1, 1, 0], bool)}
    assert overlay.shown_frames(4, 0, None, 1, [], plate).tolist() == [1, 2]
    assert overlay.shown_frames(4, 0, None, 1, [], None).tolist() == [0, 1, 2, 3]


def test_zoom_window_surrounds_the_points_ignoring_nan_and_stays_in_the_frame():
    pts = np.array([[100.0, 200.0], [300.0, 400.0], [np.nan, np.nan]])
    assert overlay.zoom_window(pts, 1000, 1000, margin=50) == (50, 150, 350, 450)
    assert overlay.zoom_window(pts, 320, 430, margin=50) == (50, 150, 320, 430)
    assert overlay.zoom_window(np.full((2, 2), np.nan), 640, 480) == (0, 0, 640, 480)
