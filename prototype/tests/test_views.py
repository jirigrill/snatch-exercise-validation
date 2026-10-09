import numpy as np

from snatch.studies import views
def test_view_angle_from_axis_ratio():
    assert np.isclose(views.view_angle_deg(100, 100), 0)
    assert np.isclose(views.view_angle_deg(100 * np.cos(np.radians(45)), 100), 45)
    assert np.isclose(views.view_angle_deg(100, 50), 60)  # order of axes free


def test_ellipse_dist_inside_and_rotated():
    # minor axis horizontal (a=50 along x), major vertical (b=100)
    assert views.ellipse_dist(140, 0, 100, 0, 50, 100, 0) < 1
    assert views.ellipse_dist(160, 0, 100, 0, 50, 100, 0) > 1
    assert np.isclose(views.ellipse_dist(100, 100, 100, 0, 50, 100, 0), 1)
    # same ellipse described with the a axis vertical
    assert np.isclose(views.ellipse_dist(150, 0, 100, 0, 100, 50, 90), 1)


def test_rectify_stretches_minor_axis_only():
    c = np.cos(np.radians(30))
    dx, dy = views.rectify(10 * c, 20, 100 * c, 100, 0)
    assert np.allclose([dx, dy], [10, 20])
    dx, dy = views.rectify(10 * c, 20, 100, 100 * c, 90)  # axes swapped
    assert np.allclose([dx, dy], [10, 20])
    dx, dy = views.rectify(10, 20, 100, 100, 0)  # side-on: unchanged
    assert np.allclose([dx, dy], [10, 20])


def test_swap_frames():
    near_s = np.zeros((3, 2))
    far_s = np.tile([30.0, 0.0], (3, 1))
    near_raw = np.array([[2.0, 0], [28.0, 0], [28.0, 0]])
    far_s[2] = [5.0, 0]  # tracks too close: not counted
    assert views.swap_frames(near_raw, near_s, far_s,
                             10).tolist() == [False, True, False]


def test_near_plate_mask():
    hub = np.array([[0.0, 0], [100.0, 0]])
    nw, fw = np.tile([20.0, 0], (2, 1)), np.tile([90.0, 0], (2, 1))
    assert views.near_plate_mask(hub, nw, fw).tolist() == [True, False]


def test_jitter_and_rest_mask():
    raw = np.array([[1.0, 0], [-1.0, 0], [np.nan, 0]])
    assert np.isclose(views.jitter_px(raw, np.zeros((3, 2))), 1)
    y = np.r_[np.full(50, 500.0), np.linspace(500, 100, 50)]
    m = views.rest_mask(y, np.ones(100, bool), 240)
    assert m[:45].all() and not m[60:].any()
