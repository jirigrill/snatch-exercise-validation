import numpy as np

from snatch.studies import views
def test_ellipse_dist_inside_and_rotated():
    # minor axis horizontal (a=50 along x), major vertical (b=100)
    """R3: the hidden-joint mask of a rotated plate ellipse (moves with S6)."""
    assert views.ellipse_dist(140, 0, 100, 0, 50, 100, 0) < 1
    assert views.ellipse_dist(160, 0, 100, 0, 50, 100, 0) > 1
    assert np.isclose(views.ellipse_dist(100, 100, 100, 0, 50, 100, 0), 1)
    # same ellipse described with the a axis vertical
    assert np.isclose(views.ellipse_dist(150, 0, 100, 0, 100, 50, 90), 1)
