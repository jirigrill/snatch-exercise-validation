"""Run RTMPose-x (body7, 384x288) with a YOLOX-x person detector via rtmlib.

The detector runs on CPU (YOLOX-x fails on onnxruntime's CoreML provider);
the pose model runs on CoreML. Output keypoints are COCO-17, image pixels of
the rotated (portrait) frame.
"""

from collections.abc import Iterable

import numpy as np
from rtmlib import RTMPose, YOLOX
from rtmlib.tools.solution.body import Body

MODEL_NAME = "rtmpose-x_simcc-body7_pt-body7_700e-384x288"


def iou(a: np.ndarray, b: np.ndarray) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])  # noqa: E731
    union = area(a) + area(b) - inter
    return float(inter / union) if union > 0 else 0.0


def pick_lifter(boxes: np.ndarray, prev: np.ndarray | None) -> np.ndarray | None:
    """Follow the previous box by IoU; otherwise take the largest box."""
    if len(boxes) == 0:
        return None
    if prev is not None:
        overlaps = [iou(b, prev) for b in boxes]
        if max(overlaps) > 0.1:
            return boxes[int(np.argmax(overlaps))]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return boxes[int(np.argmax(areas))]


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


def sparse_detections(boxes: np.ndarray, every: int) -> np.ndarray:
    """Keep every `every`-th detector box; NaN elsewhere (tracked frames)."""
    out = np.full_like(boxes, np.nan)
    out[::every] = boxes[::every]
    return out


def load_detector() -> YOLOX:
    cfg = Body.MODE["performance"]
    return YOLOX(cfg["det"], model_input_size=cfg["det_input_size"],
                 backend="onnxruntime", device="cpu")


def load_models(pose_device: str = "mps") -> tuple[YOLOX, RTMPose]:
    cfg = Body.MODE["performance"]
    pose = RTMPose(cfg["pose"], model_input_size=cfg["pose_input_size"],
                   backend="onnxruntime", device=pose_device)
    return load_detector(), pose


def detect_boxes(images: Iterable[np.ndarray], n_frames: int, every: int, det,
                 progress=None) -> tuple[np.ndarray, np.ndarray]:
    """Lifter box on every `every`-th frame (NaN elsewhere) and people counts.

    Detection only, no pose: the first pass of a run that fills the frames in
    between with `interpolate_boxes`. The lifter is followed from detection to
    detection like in `run` (overlap with the previous box, else the largest).
    """
    boxes = np.full((n_frames, 4), np.nan, np.float32)
    n_people = np.zeros(n_frames, np.int16)
    prev = None
    for i, img in enumerate(images):
        if i >= n_frames:
            break
        if i % every:
            continue
        found = np.asarray(det(img)).reshape(-1, 4)
        n_people[i] = len(found)
        box = pick_lifter(found, prev)
        if box is not None:
            boxes[i], prev = box, box
        if progress:
            progress(i)
    return boxes, n_people


def interpolate_boxes(boxes: np.ndarray) -> np.ndarray:
    """Fill NaN rows by a straight line between the nearest boxes on both sides.

    Before the first and after the last box the nearest one is kept. All NaN
    stays NaN. At 240 fps a lifter moves a few pixels in a few frames, so the
    estimate is close to what the detector would return.
    """
    seen = np.flatnonzero(~np.isnan(boxes).any(1))
    if not len(seen):
        return boxes.copy()
    t = np.arange(len(boxes))
    return np.stack([np.interp(t, seen, boxes[seen, c]) for c in range(4)], 1).astype(boxes.dtype)


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


def run(images: Iterable[np.ndarray], n_frames: int, pose_device: str = "mps",
        det_boxes: np.ndarray | None = None, progress=None,
        resume: dict[str, np.ndarray] | None = None, done: int = 0,
        checkpoint=None, checkpoint_every: int = 500,
        ranges: list[tuple[int, int]] | None = None, restart_gap: int = 1,
        det_every: int = 1) -> dict[str, np.ndarray]:
    """Detect (unless det_boxes are given), pick the lifter, track, pose.

    resume/done: continue from a partial result holding `done` finished frames.
    checkpoint(result, frames_done) is called every `checkpoint_every` frames.
    ranges: only pose frames inside these [start, end) ranges (per-rep runs);
    output stays indexed by clip frame, NaN outside. Tracking restarts (as at
    frame 0) when more than `restart_gap` frames passed since the last posed
    one: between rep ranges the previous pose is too old to follow. A sparse
    pass (every Nth frame) sets restart_gap=N so it keeps following the
    lifter's box; restarting each sample picks the largest box, which can be
    someone else (20261005_9).
    det_every: run the person detector only every Nth posed frame (and whenever
    tracking restarts); in between, the crop is the previous frame's padded
    keypoint extent (`track_box` without a detection). The detector is ~95% of
    the run time. `bbox` is NaN and `n_people` 0 on frames without a detection.
    """
    active = range_mask(n_frames, ranges)
    det, pose = load_models(pose_device)
    kps = np.full((n_frames, 17, 2), np.nan, np.float32)
    scores = np.zeros((n_frames, 17), np.float32)
    det_bbox = np.full((n_frames, 4), np.nan, np.float32)
    pose_bbox = np.full((n_frames, 4), np.nan, np.float32)
    n_people = np.zeros(n_frames, np.int16)
    out = {"keypoints": kps, "scores": scores, "bbox": det_bbox,
           "pose_bbox": pose_bbox, "n_people": n_people}
    prev = prev_kps = prev_scores = None
    if resume is not None:
        for k, v in out.items():
            v[:done] = resume[k][:done]
        prev, prev_kps, prev_scores = resume_state(out, done)
    last = int(np.flatnonzero(active)[-1]) + 1 if active.any() else 0
    last_posed = done - 1 if done else -1
    last_det = -det_every  # frame of the last detector run
    for i, img in enumerate(images):
        if i >= last:
            break
        if i < done or not active[i]:
            continue
        if last_posed >= 0 and i - last_posed > restart_gap:
            prev = prev_kps = prev_scores = None
        last_posed = i
        if det_boxes is None:
            if prev_kps is None or i - last_det >= det_every:
                boxes = np.asarray(det(img)).reshape(-1, 4)
                n_people[i] = len(boxes)
                box = pick_lifter(boxes, prev)
                last_det = i
            else:
                box = None  # follow the previous keypoints
        else:
            box = None if np.isnan(det_boxes[i]).any() else det_boxes[i]
        crop = track_box(box, prev_kps, prev_scores)
        if crop is not None:
            k, s = pose(img, bboxes=[crop])
            kps[i], scores[i], pose_bbox[i] = k[0], s[0], crop
            prev_kps, prev_scores = k[0], s[0]
        if box is not None:
            det_bbox[i], prev = box, box
        if progress:
            progress(i)
        if checkpoint and (i + 1) % checkpoint_every == 0:
            checkpoint(out, i + 1)
    return out
