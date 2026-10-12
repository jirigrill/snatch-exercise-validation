"""Find the lifter in every frame: person boxes from a YOLOX-x detector.

The detector is ~95% of the pose pipeline's run time (330 ms/frame on the CPU;
it fails on onnxruntime's CoreML provider) and rarely changes, so it runs once
per clip, on its own (scripts/extract_person.py), and the pose step reads the
boxes it saved. At 240 fps the lifter moves a few pixels in a few frames, so
the detector runs only every Nth frame and the boxes in between are
interpolated (N = 24 differs from a run on every frame by ~1.5 px median at the
joints, see docs/pipeline.html).
"""

from collections.abc import Callable, Iterable

import numpy as np
from rtmlib import YOLOX
from rtmlib.tools.solution.body import Body

DETECTOR_NAME = "yolox_x_8xb8-300e_humanart"
DEFAULT_DET_EVERY = 24


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


def sparse_detections(boxes: np.ndarray, every: int) -> np.ndarray:
    """Keep every `every`-th detector box; NaN elsewhere (tracked frames)."""
    out = np.full_like(boxes, np.nan)
    out[::every] = boxes[::every]
    return out


def load_detector() -> YOLOX:
    cfg = Body.MODE["performance"]
    return YOLOX(cfg["det"], model_input_size=cfg["det_input_size"],
                 backend="onnxruntime", device="cpu")


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


def gaps(detected: np.ndarray, every: int) -> np.ndarray:
    """True where the box is interpolated across a missed detection.

    The detector runs on every `every`-th frame; a frame is a gap when the
    run nearest to it found no lifter.
    """
    n = len(detected)
    last_run = (n - 1) // every * every
    nearest = np.minimum((np.arange(n) + every // 2) // every * every, last_run)
    return ~detected[nearest]


def detect(images: Iterable[np.ndarray], n_frames: int, every: int, det,
           progress: Callable[[int], None] | None = None) -> dict[str, np.ndarray]:
    """Person boxes for every frame: detect every `every`-th frame, interpolate the rest.

    bbox      (n_frames, 4) lifter box, interpolated between detections
    detected  (n_frames,)   True where the detector ran and found the lifter
    n_people  (n_frames,)   people the detector saw (0 where it did not run)
    """
    boxes, n_people = detect_boxes(images, n_frames, every, det, progress)
    return {"bbox": interpolate_boxes(boxes), "detected": ~np.isnan(boxes).any(1),
            "n_people": n_people}
