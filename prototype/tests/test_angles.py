import numpy as np
import pytest

from snatch.angles import (
    COCO, HALPE26, joint_angle, sagittal_angles,
)


def _halpe(**points):
    kps = np.full((1, 26, 2), np.nan)
    for name, xy in points.items():
        kps[0, HALPE26[name]] = xy
    return kps


LEANING = dict(r_shoulder=(160, 100), r_hip=(100, 300), r_knee=(250, 450),
               r_ankle=(200, 650), r_elbow=(220, 0), r_wrist=(200, -100))


def test_mirrored_skeleton_gives_same_angles_when_facing_left():
    """R3: a left-facing lifter gives the same angles as the mirrored right-facing one."""
    right = _halpe(**LEANING)
    left = right.copy()
    left[..., 0] = 1000 - left[..., 0]
    a, b = sagittal_angles(right, facing="right"), sagittal_angles(left, facing="left")
    assert a["trunk"][0] > 0
    for joint in ("hip", "knee", "elbow", "trunk"):
        assert b[joint] == pytest.approx(a[joint])


def test_joint_angle_is_vectorised_and_nan_safe():
    """R3: missing keypoints give NaN angles, not an error."""
    a = np.array([[0, 0], [np.nan, 0]])
    b = np.array([[0, 1], [0, 1]])
    c = np.array([[1, 1], [0, 2]])
    out = joint_angle(a, b, c)
    assert out[0] == pytest.approx(90.0)
    assert np.isnan(out[1])


def _pose(**points):
    kps = np.full((1, 17, 2), np.nan)
    for name, xy in points.items():
        kps[0, COCO[name]] = xy
    return kps
