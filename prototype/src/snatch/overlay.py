"""Draw pipeline results on the video: person boxes, pose skeletons, plate outline.

One renderer for every step of the pipeline, so a layer looks the same in
every stage's overlay (the colors below). Each layer is optional:

- person: lifter box per frame (light blue); thick = the detector ran there,
          thin = interpolated, red = interpolated across a missed detection
- poses:  one or two raw_pose runs. One run: left side red, right side green,
          centre (head, neck, mid hip) white. Two runs: green = first, magenta =
          second, the left side darker; only frames posed in both are shown, each
          labelled with the largest joint distance between the runs, red border
          above `flag_px`. Grey = a joint scored under FADE_SCORE.
- plate:  plate outline (ellipse) and hub, plus a trail of the hub over the last
          TRAIL_S seconds of found frames. Orange; green when the plate dict has
          passed=True (S2's sanity check), orange also when passed=False.
- boxes:  also draw the crop given to the pose model (yellow)
- dim, frame_labels: S3's attempts: frames in `dim` are darkened, `frame_labels(i)` adds label lines
- extra: frames drawn in addition to every `step`-th one (the worst/key frames of a stage's review),
          when they pass the same range and posed/found filter
"""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import cv2
import numpy as np

from snatch.person import gaps
from snatch.pose import HALPE26
from snatch.video import frames, probe

EDGES = [("shoulder", "elbow"), ("elbow", "wrist"), ("shoulder", "hip"), ("hip", "knee"),
         ("knee", "ankle")]
FOOT_EDGES = [("ankle", "heel"), ("heel", "big_toe"), ("big_toe", "small_toe"),
              ("ankle", "big_toe")]
# BGR
LEFT_COLOR, RIGHT_COLOR, CENTRE_COLOR = (0, 0, 255), (0, 220, 0), (255, 255, 255)  # one run
POSE_COLORS = ((0, 255, 0), (255, 0, 255))  # two runs: green, magenta; left side darker
PERSON_COLOR = (255, 200, 0)  # BGR: light blue
CROP_COLOR = (0, 255, 255)  # BGR: yellow
PLATE_COLOR = (0, 140, 255)  # BGR: orange
PLATE_OK_COLOR = (0, 220, 0)  # BGR: green, plate track that passed S2's check
TRAIL_S = 0.5  # seconds of hub path drawn behind the hub
GAP_COLOR = (0, 0, 255)  # BGR: red
FADED_COLOR = (150, 150, 150)  # BGR: grey, a joint under FADE_SCORE
FADE_SCORE = 0.3
DIM_FACTOR = 0.35  # brightness of a dimmed frame

Arrays = Mapping[str, np.ndarray]


def shown_frames(n_frames: int, start: int, end: int | None, step: int,
                 poses: Sequence[Arrays], plate: Arrays | None,
                 extra: Sequence[int] = ()) -> np.ndarray:
    """Frames to draw: in [start, end), posed in every run, plate found, every `step`-th plus `extra`."""
    mask = np.zeros(n_frames, bool)
    mask[start:end] = True
    for p in poses:
        mask &= ~np.isnan(p["keypoints"]).all((1, 2))
    if plate is not None and not poses:
        mask &= np.asarray(plate["found"], bool)
    keep = np.zeros(n_frames, bool)
    keep[np.flatnonzero(mask)[::step]] = True
    for i in extra:
        keep[i] = mask[i]
    return np.flatnonzero(keep)


def zoom_window(points: np.ndarray, width: int, height: int, margin: int = 150
                ) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) around all (x, y) points, NaN ignored, kept inside the frame."""
    pts = points[~np.isnan(points).any(1)]
    if not len(pts):
        return 0, 0, width, height
    (x0, y0), (x1, y1) = pts.min(0) - margin, pts.max(0) + margin
    return max(0, int(x0)), max(0, int(y0)), min(width, int(x1)), min(height, int(y1))


def _text(img: np.ndarray, s: str, line: int) -> None:
    """Outlined label, `line` 0, 1, 2 ... from the top left of the (cropped) image."""
    y = 32 + 40 * line
    cv2.putText(img, s, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5)
    cv2.putText(img, s, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)


def _box(img: np.ndarray, b: np.ndarray, color: tuple[int, int, int], thick: int) -> None:
    if not np.isnan(b).any():
        cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), color, thick)


def _skeleton(img: np.ndarray, k: np.ndarray, colors: tuple[tuple[int, int, int], ...],
              scores: np.ndarray | None = None) -> None:
    """Joints and bones in colors (left, right, centre); under FADE_SCORE thin and grey."""
    low = scores < FADE_SCORE if scores is not None else np.zeros(len(k), bool)
    side_color = {"l": colors[0], "r": colors[1]}
    for side in ("l", "r"):
        for a, b in EDGES + FOOT_EDGES:
            ia, ib = HALPE26[f"{side}_{a}"], HALPE26[f"{side}_{b}"]
            pa, pb = k[ia], k[ib]
            if not (np.isnan(pa).any() or np.isnan(pb).any()):
                faded = low[ia] or low[ib]
                cv2.line(img, tuple(map(int, pa)), tuple(map(int, pb)),
                         FADED_COLOR if faded else side_color[side], 2 if faded else 4)
    point_color = {i: side_color[name[0]] if name[1] == "_" else colors[2] for name, i in HALPE26.items()}
    for i, (p, faded) in enumerate(zip(k, low)):
        if not np.isnan(p).any():
            cv2.circle(img, tuple(map(int, p)), 4 if faded else 6, FADED_COLOR if faded else point_color[i], -1)


def hub_trail(plate: Arrays, i: int) -> np.ndarray:
    """(k, 2) int hub positions of the found frames in the TRAIL_S seconds up to frame i."""
    found = np.asarray(plate["found"], bool)
    t = np.asarray(plate["t"])
    idx = np.flatnonzero(found[:i + 1] & (t[:i + 1] > t[i] - TRAIL_S))
    return np.column_stack([plate["hub_x"][idx], plate["hub_y"][idx]]).astype(int)


def pose_colors(n_runs: int) -> list[tuple[tuple[int, int, int], ...]]:
    """(left, right, centre) per run: red/green/white for one run, the run color (left darker) for two."""
    if n_runs == 1:
        return [(LEFT_COLOR, RIGHT_COLOR, CENTRE_COLOR)]
    return [((b // 2, g // 2, r // 2), (b, g, r), (b, g, r)) for b, g, r in POSE_COLORS[:n_runs]]


def _points(i: np.ndarray, person: Arrays | None, poses: Sequence[Arrays],
            plate: Arrays | None, boxes: bool) -> np.ndarray:
    """Every (x, y) that gets drawn on frames `i`, for the zoom window."""
    parts = []
    if person is not None:
        parts.append(person["bbox"][i].reshape(-1, 2))
    for p in poses:
        parts.append(p["keypoints"][i].reshape(-1, 2))
        if boxes:
            parts += [p["bbox"][i].reshape(-1, 2), p["pose_bbox"][i].reshape(-1, 2)]
    if plate is not None:
        r = np.fmax(plate["a"][i], plate["b"][i])
        for dx, dy in ((-1, -1), (1, 1)):
            parts.append(np.column_stack([plate["hub_x"][i] + dx * r, plate["hub_y"][i] + dy * r]))
    return np.concatenate(parts) if parts else np.empty((0, 2))


def render(clip: str, out_path: str, *, person: Arrays | None = None,
           poses: Sequence[Arrays] = (), plate: Arrays | None = None, boxes: bool = False,
           start: int = 0, end: int | None = None, step: int = 1, fps: float = 30.0,
           scale: float = 0.5, zoom: bool = False, flag_px: float = 10.0,
           notes: Sequence[str] = (), dim: np.ndarray | None = None,
           frame_labels: Callable[[int], Sequence[str]] | None = None,
           extra: Sequence[int] = ()) -> dict[str, int]:
    """Write the overlay video; returns {"frames": written, "flagged": above flag_px}.

    notes: extra label lines on every frame (e.g. facing and the color legend).
    dim: per-frame bool, True = darken the frame; frame_labels(i): extra label lines on frame i.
    extra: frames always drawn besides every `step`-th (see shown_frames).
    """
    info = probe(clip)
    show = shown_frames(info.n_frames, start, end, step, poses, plate, extra)
    if not len(show):
        raise ValueError("no frame to draw: nothing is posed / found in the range")
    dist = (np.linalg.norm(poses[0]["keypoints"] - poses[1]["keypoints"], axis=-1)
            if len(poses) > 1 else None)
    x0, y0, x1, y1 = (zoom_window(_points(show, person, poses, plate, boxes),
                                  info.width, info.height) if zoom
                      else (0, 0, info.width, info.height))
    size = (max(1, int((x1 - x0) * scale)), max(1, int((y1 - y0) * scale)))
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter.fourcc(*"mp4v"), fps, size)
    gap_mask = (gaps(person["detected"], int(person["det_every"]))
                if person is not None and "det_every" in person else None)
    want, flagged, written = set(show.tolist()), 0, 0
    for i, img in enumerate(frames(clip, info)):
        if i > show[-1]:
            break
        if i not in want:
            continue
        img = (img * DIM_FACTOR).astype(np.uint8) if dim is not None and dim[i] else img.copy()
        labels = [f"f{i}", *notes, *(frame_labels(i) if frame_labels else ())]
        if person is not None:
            seen = bool(person["detected"][i]) if "detected" in person else True
            gap = gap_mask is not None and bool(gap_mask[i])
            _box(img, person["bbox"][i], GAP_COLOR if gap else PERSON_COLOR, 6 if seen else 2)
            labels.append("person: detected" if seen else "person: missed" if gap else "person: interpolated")
        if plate is not None and bool(plate["found"][i]):
            c = (int(plate["hub_x"][i]), int(plate["hub_y"][i]))
            color = PLATE_OK_COLOR if "passed" in plate and bool(plate["passed"]) else PLATE_COLOR
            cv2.ellipse(img, c, (int(plate["a"][i]), int(plate["b"][i])),
                        float(plate["angle"][i]), 0, 360, color, 4)
            if "t" in plate:
                cv2.polylines(img, [hub_trail(plate, i).reshape(-1, 1, 2)], False, color, 3)
            cv2.circle(img, c, 8, (0, 0, 255), -1)
        for p, colors in zip(poses, pose_colors(len(poses))):
            if boxes:
                _box(img, p["pose_bbox"][i], CROP_COLOR, 2)
            _skeleton(img, p["keypoints"][i], colors, p["scores"][i] if "scores" in p else None)
        worst = None
        if dist is not None:
            worst = float(np.nanmax(dist[i]))
            labels.append(f"max diff {worst:.1f} px")
        img = cv2.resize(img[y0:y1, x0:x1], size, interpolation=cv2.INTER_AREA)
        for line, s in enumerate(labels):
            _text(img, s, line)
        if worst is not None and worst > flag_px:
            flagged += 1
            cv2.rectangle(img, (0, 0), (img.shape[1] - 1, img.shape[0] - 1), (0, 0, 255), 8)
        writer.write(img)
        written += 1
    writer.release()
    return {"frames": written, "flagged": flagged}
