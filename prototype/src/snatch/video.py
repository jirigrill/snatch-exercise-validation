"""Decode iPhone clips with the display-matrix rotation applied.

ffmpeg applies the rotation tag by default (autorotate), so frames come out
portrait. We read the probed size after rotation and stream raw BGR frames.
"""

import json
import subprocess
from collections.abc import Iterator
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
    return ClipInfo(w, h, int(num) / int(den), int(s["nb_frames"]), rotation)


def frames(path: str, info: ClipInfo | None = None) -> Iterator[np.ndarray]:
    """Yield rotated BGR frames (H x W x 3, uint8)."""
    info = info or probe(path)
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
         "-pix_fmt", "bgr24", "-"],
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
        proc.stdout.close()
        proc.kill()
        proc.wait()
