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


def load_models(pose_device: str = "mps") -> tuple[YOLOX, RTMPose]:
    cfg = Body.MODE["performance"]
    det = YOLOX(cfg["det"], model_input_size=cfg["det_input_size"],
                backend="onnxruntime", device="cpu")
    pose = RTMPose(cfg["pose"], model_input_size=cfg["pose_input_size"],
                   backend="onnxruntime", device=pose_device)
    return det, pose


def run(images: Iterable[np.ndarray], n_frames: int, pose_device: str = "mps",
        det_boxes: np.ndarray | None = None, progress=None
        ) -> dict[str, np.ndarray]:
    """Detect (unless det_boxes are given), pick the lifter, track, pose."""
    det, pose = load_models(pose_device)
    kps = np.full((n_frames, 17, 2), np.nan, np.float32)
    scores = np.zeros((n_frames, 17), np.float32)
    det_bbox = np.full((n_frames, 4), np.nan, np.float32)
    pose_bbox = np.full((n_frames, 4), np.nan, np.float32)
    n_people = np.zeros(n_frames, np.int16)
    prev = None
    prev_kps = prev_scores = None
    for i, img in enumerate(images):
        if i >= n_frames:
            break
        if det_boxes is None:
            boxes = np.asarray(det(img)).reshape(-1, 4)
            n_people[i] = len(boxes)
            box = pick_lifter(boxes, prev)
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
    return {"keypoints": kps, "scores": scores, "bbox": det_bbox,
            "pose_bbox": pose_bbox, "n_people": n_people}
