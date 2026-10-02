import numpy as np
import pytest

from snatch.angles import (
    COCO, joint_angle, mid_y, sagittal_angles, trunk_from_vertical,
)


def test_joint_angle_straight_limb_is_180():
    a, b, c = np.array([[0, 0]]), np.array([[0, 1]]), np.array([[0, 2]])
    assert joint_angle(a, b, c) == pytest.approx([180.0])


def test_joint_angle_right_angle_is_90():
    a, b, c = np.array([[0, 0]]), np.array([[0, 1]]), np.array([[1, 1]])
    assert joint_angle(a, b, c) == pytest.approx([90.0])


def test_joint_angle_is_vectorised_and_nan_safe():
    a = np.array([[0, 0], [np.nan, 0]])
    b = np.array([[0, 1], [0, 1]])
    c = np.array([[1, 1], [0, 2]])
    out = joint_angle(a, b, c)
    assert out[0] == pytest.approx(90.0)
    assert np.isnan(out[1])


def test_trunk_upright_is_0_and_forward_lean_is_positive():
    # image coordinates: y grows downward; camera on the lifter's right,
    # so the lifter faces image-right (+x).
    hip = np.array([[100, 200], [100, 200], [100, 200]])
    shoulder = np.array([[100, 100], [200, 100], [0, 100]])
    out = trunk_from_vertical(hip, shoulder)
    assert out == pytest.approx([0.0, 45.0, -45.0])


def _pose(**points):
    kps = np.full((1, 17, 2), np.nan)
    for name, xy in points.items():
        kps[0, COCO[name]] = xy
    return kps


def test_sagittal_angles_use_the_near_right_side():
    # standing straight, arms overhead
    kps = _pose(r_wrist=(100, -100), r_elbow=(100, 0), r_shoulder=(100, 100),
                r_hip=(100, 300), r_knee=(100, 500), r_ankle=(100, 700))
    out = sagittal_angles(kps)
    for joint in ("hip", "knee", "elbow"):
        assert out[joint] == pytest.approx([180.0])
    assert out["trunk"] == pytest.approx([0.0])


def test_sagittal_angles_deep_squat():
    kps = _pose(r_shoulder=(100, 100), r_hip=(100, 300), r_knee=(300, 300),
                r_ankle=(300, 500), r_elbow=(100, 0), r_wrist=(100, -100))
    out = sagittal_angles(kps)
    assert out["hip"] == pytest.approx([90.0])
    assert out["knee"] == pytest.approx([90.0])


def test_mid_y_averages_left_and_right_heights():
    kps = _pose(l_wrist=(0, 100), r_wrist=(0, 300), nose=(0, 50))
    assert mid_y(kps, "wrist") == pytest.approx([200.0])
    assert mid_y(kps, "nose") == pytest.approx([50.0])
