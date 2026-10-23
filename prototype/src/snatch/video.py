"""Decode iPhone clips with the display-matrix rotation applied.

ffmpeg applies the rotation tag by default (autorotate), so frames come out
portrait. We read the probed size after rotation and stream raw BGR frames.

Frame times: the 2026-10-05 clips are tagged 240 fps but average ~200 fps
(two frames dropped about every 12, likely flicker reduction under 100 Hz
lights), so frame / fps is not the time there. `timestamps` gives each
frame's real time; per-frame arrays keep it as `t` (`frame_times` reads it).
"""

import json
import subprocess
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClipInfo:
    width: int  # after rotation
    height: int  # after rotation
    fps: float
    n_frames: int
    rotation: int  # display-matrix rotation tag, degrees


def rotated_size(width: int, height: int, rotation: int) -> tuple[int, int]:
    """Frame size once a display-matrix rotation is applied."""
    if rotation % 180 == 0:
        return width, height
    if rotation % 90 == 0:
        return height, width
    raise ValueError(f"unsupported rotation {rotation}")


def decoded_pts(pts: np.ndarray) -> np.ndarray:
    """Sorted packet times of the frames the decoder outputs.

    A `-c copy` cut starts at the keyframe before `-ss` and keeps the frames
    before the cut point as packets with negative times; the edit list makes
    the decoder skip them. They are not frames of the clip.
    """
    pts = np.sort(np.asarray(pts, float))
    return pts[pts >= 0]


def packet_times(path: str) -> np.ndarray:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "packet=pts_time", "-of", "csv=p=0", path],
        check=True, capture_output=True, text=True,
    ).stdout
    return decoded_pts(np.array([float(x.strip(",")) for x in out.split() if x.strip(",") != "N/A"]))


def probe(path: str) -> ClipInfo:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-of", "json", path],
        check=True, capture_output=True, text=True,
    ).stdout
    s = json.loads(out)["streams"][0]
    rotation = 0
    for sd in s.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    num, den = s["r_frame_rate"].split("/")
    w, h = rotated_size(int(s["width"]), int(s["height"]), rotation)
    return ClipInfo(w, h, int(num) / int(den), len(packet_times(path)), rotation)


def frames(path: str, info: ClipInfo | None = None, stop: int | None = None) -> Iterator[np.ndarray]:
    """Yield rotated BGR frames (H x W x 3, uint8), the first `stop` only when given.

    `stop` saves decoding frames nobody reads. A caller that breaks early without it is
    fine too: ffmpeg is killed before the pipe closes, so it never writes into a closed
    pipe (its "Broken pipe" error).
    """
    info = info or probe(path)
    limit = ["-frames:v", str(stop)] if stop is not None else []
    proc = subprocess.Popen(
        # passthrough: one output frame per coded frame, never duplicated to a
        # constant rate (the 120 fps ladder files keep a 240 fps rate tag)
        ["ffmpeg", "-v", "error", "-i", path, "-fps_mode", "passthrough", *limit,
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        stdout=subprocess.PIPE,
    )
    size = info.width * info.height * 3
    assert proc.stdout is not None
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, np.uint8).reshape(info.height, info.width, 3)
    finally:
        proc.kill()  # before closing the pipe: a consumer that stops early must not make ffmpeg write into a closed pipe (Broken pipe)
        proc.stdout.close()
        proc.wait()


def timestamps(path: str, rate: float | None = None) -> np.ndarray:
    """Time of every frame in seconds from the first, in output order of `frames`.

    Read from the packet headers, without decoding (~0.1 s per clip). Snapped
    to the tagged rate's grid (`rate`, default the probed fps): each gap
    between frames is rounded to whole frame periods (at least one). The stored
    times jitter by a tick (0.4 ms at 240 fps), and so a clip with no dropped
    frames gets exactly arange(n) / fps.
    """
    rate = rate or probe(path).fps
    t = packet_times(path)
    periods = np.maximum(np.round(np.diff(t) * rate), 1)
    return np.r_[0, np.cumsum(periods)] / rate


def frame_times(arrays: Mapping, n: int | None = None) -> np.ndarray:
    """`t` of a per-frame npz, or arange(n) / fps for files saved before it existed."""
    if "t" in arrays:
        return np.asarray(arrays["t"], float)
    return np.arange(n if n is not None else len(arrays["keypoints"])) / float(arrays["fps"])


def mean_rate(t: np.ndarray) -> float:
    """Frames per second on average (the rate for windows given in frames)."""
    return round((len(t) - 1) / float(t[-1] - t[0]), 6)  # 240.0, not 240.00000000000003
