"""Run RTMPose-x (body7 halpe26, 384x288) on the lifter's box in every frame, via rtmlib.

The person boxes come from snatch.person (S1, saved once per clip). The pose
model runs on CoreML. Output keypoints are Halpe-26 (COCO-17 first, then head,
neck, hip, toes and heels), image pixels of the rotated (portrait) frame.
"""

from collections.abc import Iterable

import numpy as np
from rtmlib import RTMPose
from rtmlib.tools.solution.body_with_feet import BodyWithFeet

MODEL_NAME = "rtmpose-x_simcc-body7_pt-body7-halpe26_700e-384x288"
HALPE26 = {
    "nose": 0, "l_eye": 1, "r_eye": 2, "l_ear": 3, "r_ear": 4,
    "l_shoulder": 5, "r_shoulder": 6, "l_elbow": 7, "r_elbow": 8,
    "l_wrist": 9, "r_wrist": 10, "l_hip": 11, "r_hip": 12,
    "l_knee": 13, "r_knee": 14, "l_ankle": 15, "r_ankle": 16,
    "head": 17, "neck": 18, "hip": 19,
    "l_big_toe": 20, "r_big_toe": 21, "l_small_toe": 22, "r_small_toe": 23,
    "l_heel": 24, "r_heel": 25,
}
N_KEYPOINTS = len(HALPE26)


def track_box(det: np.ndarray | None, prev_kps: np.ndarray | None,
              prev_scores: np.ndarray | None, pad: float = 0.1,
              min_score: float = 0.3) -> np.ndarray | None:
    """Union of the detector box and last frame's confident keypoint extent.

    YOLOX cuts the box off at the plate when the plates hide the lower legs,
    and RTMPose then guesses the legs. At 240 fps the previous frame's pose is
    a close prior, so its extent (padded by `pad` of its size) keeps the legs
    in the crop. Without a detection (sparse detector runs) the padded
    keypoint extent alone is the crop.
    """
    if prev_kps is None or prev_scores is None:
        return det
    pts = prev_kps[prev_scores >= min_score]
    if len(pts) == 0:
        return det
    lo, hi = pts.min(0), pts.max(0)
    margin = (hi - lo) * pad
    lo, hi = lo - margin, hi + margin
    if det is None:
        return np.array([lo[0], lo[1], hi[0], hi[1]])
    return np.array([min(det[0], lo[0]), min(det[1], lo[1]),
                     max(det[2], hi[0]), max(det[3], hi[1])])


def load_model(pose_device: str = "mps") -> RTMPose:
    cfg = BodyWithFeet.MODE["performance"]
    return RTMPose(cfg["pose"], model_input_size=cfg["pose_input_size"],
                   backend="onnxruntime", device=pose_device)


def resume_state(part: dict[str, np.ndarray], done: int):
    """(prev box, prev keypoints, prev scores) to continue after `done` frames."""
    if done == 0:
        return None, None, None
    seen = ~np.isnan(part["bbox"][:done]).any(1)
    prev = part["bbox"][:done][seen][-1] if seen.any() else None
    return prev, part["keypoints"][done - 1], part["scores"][done - 1]


def range_mask(n_frames: int, ranges: list[tuple[int, int]] | None) -> np.ndarray:
    """True for frames to process: inside any [start, end) range, or all if None."""
    if ranges is None:
        return np.ones(n_frames, bool)
    mask = np.zeros(n_frames, bool)
    for start, end in ranges:
        if not 0 <= start < end <= n_frames:
            raise ValueError(f"range {start}:{end} outside 0:{n_frames}")
        mask[start:end] = True
    return mask


def run(images: Iterable[np.ndarray], n_frames: int, boxes: np.ndarray,
        pose_device: str = "mps", progress=None,
        resume: dict[str, np.ndarray] | None = None, done: int = 0,
        checkpoint=None, checkpoint_every: int = 500,
        ranges: list[tuple[int, int]] | None = None, restart_gap: int = 1,
        ) -> dict[str, np.ndarray]:
    """Pose the lifter in every frame, given its box per frame (snatch.person).

    boxes: (n_frames, 4) lifter box per frame; a NaN row means no box, and the
    crop is then the previous frame's padded keypoint extent (`track_box`).
    resume/done: continue from a partial result holding `done` finished frames.
    checkpoint(result, frames_done) is called every `checkpoint_every` frames.
    ranges: only pose frames inside these [start, end) ranges (per-rep runs);
    output stays indexed by clip frame, NaN outside. The previous pose is
    forgotten (crop = the box alone, as at frame 0) when more than
    `restart_gap` frames passed since the last posed one: between rep ranges it
    is too old to follow. A sparse pass (every Nth frame) sets restart_gap=N so
    the previous pose is still used.
    """
    if len(boxes) != n_frames:
        raise ValueError(f"{len(boxes)} boxes for {n_frames} frames")
    active = range_mask(n_frames, ranges)
    model = load_model(pose_device)
    kps = np.full((n_frames, N_KEYPOINTS, 2), np.nan, np.float32)
    scores = np.zeros((n_frames, N_KEYPOINTS), np.float32)
    det_bbox = np.full((n_frames, 4), np.nan, np.float32)
    pose_bbox = np.full((n_frames, 4), np.nan, np.float32)
    n_people = np.zeros(n_frames, np.int16)
    out = {"keypoints": kps, "scores": scores, "bbox": det_bbox,
           "pose_bbox": pose_bbox, "n_people": n_people}
    prev_kps = prev_scores = None
    if resume is not None:
        for k, v in out.items():
            v[:done] = resume[k][:done]
        _, prev_kps, prev_scores = resume_state(out, done)
    last = int(np.flatnonzero(active)[-1]) + 1 if active.any() else 0
    last_posed = done - 1 if done else -1
    for i, img in enumerate(images):
        if i >= last:
            break
        if i < done or not active[i]:
            continue
        if last_posed >= 0 and i - last_posed > restart_gap:
            prev_kps = prev_scores = None
        last_posed = i
        box = None if np.isnan(boxes[i]).any() else boxes[i]
        crop = track_box(box, prev_kps, prev_scores)
        if crop is not None:
            k, s = model(img, bboxes=[crop])
            kps[i], scores[i], pose_bbox[i] = k[0], s[0], crop
            prev_kps, prev_scores = k[0], s[0]
        if box is not None:
            det_bbox[i] = box
        if progress:
            progress(i)
        if checkpoint and (i + 1) % checkpoint_every == 0:
            checkpoint(out, i + 1)
    return out


SIDE_OF = {"right": "r", "left": "l"}  # camera on the lifter's right sees the right leg


def facing_votes(kps: np.ndarray, scores: np.ndarray, min_score: float = 0.3) -> tuple[int, int]:
    """(right, left): foot-frames whose heel -> toe x points to image +x / -x.

    Both feet vote, each in the frames where its heel and big toe are confident.
    Needs Halpe-26 feet, (0, 0) without them.
    """
    if kps.shape[1] < N_KEYPOINTS:
        return 0, 0
    right = left = 0
    for side in ("l", "r"):
        toe, heel = HALPE26[f"{side}_big_toe"], HALPE26[f"{side}_heel"]
        seen = (scores[:, toe] >= min_score) & (scores[:, heel] >= min_score)
        dx = kps[seen, toe, 0] - kps[seen, heel, 0]
        right += int((dx > 0).sum())
        left += int((dx < 0).sum())
    return right, left


def facing(kps: np.ndarray, scores: np.ndarray, min_score: float = 0.3,
           majority: float = 2 / 3) -> str | None:
    """"right" or "left": the way the toes point (facing_votes), or None without a `majority`."""
    right, left = facing_votes(kps, scores, min_score)
    if not right + left:
        return None
    if right >= majority * (right + left):
        return "right"
    if left >= majority * (right + left):
        return "left"
    return None


def near_side(scores: np.ndarray) -> str:
    """"l" or "r": the leg whose keypoints score higher on average (the one the camera sees)."""
    legs = leg_scores(scores)
    return "r" if legs["r"] >= legs["l"] else "l"


def leg_scores(scores: np.ndarray) -> dict[str, float]:
    """Mean keypoint score of each leg (Halpe-26: hip down to the foot)."""
    return {s: round(float(np.nanmean(scores[:, _leg(s)])), 3) for s in ("l", "r")}


def _leg(side: str) -> list[int]:
    parts = ("hip", "knee", "ankle", "big_toe", "small_toe", "heel")
    return [HALPE26[f"{side}_{p}"] for p in parts]
