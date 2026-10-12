"""Sagittal-plane joint angles from 2D COCO-17 or Halpe-26 keypoints.

Conventions (degrees):
- hip, knee, elbow: interior angle at the joint; 180 = fully extended.
  hip = shoulder-hip-knee, knee = hip-knee-ankle, elbow = shoulder-elbow-wrist.
- trunk: hip->shoulder segment from image vertical; 0 = upright, positive =
  leaning toward the lifter's front: image +x for `facing="right"` (camera on
  the lifter's right), image -x for `facing="left"`. Assumes the phone was
  held level.
"""

import numpy as np

COCO = {
    "nose": 0, "l_eye": 1, "r_eye": 2, "l_ear": 3, "r_ear": 4,
    "l_shoulder": 5, "r_shoulder": 6, "l_elbow": 7, "r_elbow": 8,
    "l_wrist": 9, "r_wrist": 10, "l_hip": 11, "r_hip": 12,
    "l_knee": 13, "r_knee": 14, "l_ankle": 15, "r_ankle": 16,
}

HALPE26 = {
    **COCO, "head": 17, "neck": 18, "hip": 19,
    "l_big_toe": 20, "r_big_toe": 21, "l_small_toe": 22, "r_small_toe": 23,
    "l_heel": 24, "r_heel": 25,
}

JOINTS = ("hip", "knee", "elbow", "trunk")


def keypoint_map(kps: np.ndarray) -> dict[str, int]:
    """HALPE26 for 26-keypoint poses, else COCO (the committed 17-keypoint runs)."""
    return HALPE26 if kps.shape[1] >= len(HALPE26) else COCO


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Interior angle at b between b->a and b->c, per row. NaN in, NaN out."""
    u, v = np.asarray(a, float) - b, np.asarray(c, float) - b
    cross = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    dot = (u * v).sum(axis=1)
    return np.degrees(np.abs(np.arctan2(cross, dot)))


def trunk_from_vertical(hip: np.ndarray, shoulder: np.ndarray) -> np.ndarray:
    d = np.asarray(shoulder, float) - hip
    return np.degrees(np.arctan2(d[:, 0], -d[:, 1]))


def sagittal_angles(kps: np.ndarray, side: str = "r",
                    facing: str = "right") -> dict[str, np.ndarray]:
    """kps: (n_frames, 17 or 26, 2) -> {joint: (n_frames,) degrees}."""
    names = keypoint_map(kps)
    mirror = np.array([-1.0 if facing == "left" else 1.0, 1.0])
    p = {n: np.asarray(kps[:, names[f"{side}_{n}"]], float) * mirror
         for n in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")}
    return {
        "hip": joint_angle(p["shoulder"], p["hip"], p["knee"]),
        "knee": joint_angle(p["hip"], p["knee"], p["ankle"]),
        "elbow": joint_angle(p["shoulder"], p["elbow"], p["wrist"]),
        "trunk": trunk_from_vertical(p["hip"], p["shoulder"]),
    }


def mid_y(kps: np.ndarray, part: str) -> np.ndarray:
    """Image height of a keypoint, averaged over left and right if paired."""
    names = keypoint_map(kps)
    if part in names:
        return kps[:, names[part], 1]
    return kps[:, [names[f"l_{part}"], names[f"r_{part}"]], 1].mean(1)
