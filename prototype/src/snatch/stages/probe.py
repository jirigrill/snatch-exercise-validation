"""S-1: probe the clip, check it is usable, and write its frame times.

Hard checks stop with exit 3 (status bad_clip). Warnings go into clip.json and
never stop the run.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from snatch.stage import CLIP, Context, Stage, StageStop
from snatch.video import decoded_pts, rotated_size

BAD_CLIP_EXIT = 3
MIN_DURATION_S = 2.0
MAX_RATE_OFF = 0.05
MIN_FPS = 120.0
GAP_PERIODS = 1.5
BRIGHTNESS = (40.0, 220.0)
SHEET_FRAMES = 6
SHEET_HEIGHT = 480
SHEET = "overlays/0_clip_sheet.jpg"
LOAD_TOKEN = re.compile(r"_(\d+(?:-\d+)?)kg_")
FPS_TOKEN = re.compile(r"_(\d+)fps(?:[_.]|$)")
RateSource = Literal["filename", "camera", "none"]


def load_from(flag: float | None, filename: str) -> tuple[float | None, str]:
    if flag is not None:
        return float(flag), "flag"
    m = LOAD_TOKEN.search(filename)
    if m:
        return float(m.group(1).replace("-", ".")), "filename"
    return None, "none"


def rate_reference(filename: str, r_frame_rate: float, format_tags: dict) -> tuple[float | None, RateSource]:
    """The recorded rate to check the timestamps against, and where it came from.

    A `-c copy` remux rewrites r_frame_rate from the new timestamps, and the
    clips carry no codec-level timing, so the stream tag only counts on a
    camera original: Apple tags present and no ffmpeg muxer. The `_<n>fps`
    filename token wins, since the 120 fps ladder files keep a 240 tag.
    """
    m = FPS_TOKEN.search(filename)
    if m:
        return float(m.group(1)), "filename"
    remuxed = str(format_tags.get("encoder", "")).startswith("Lavf")
    if "com.apple.quicktime.make" in format_tags and not remuxed:
        return r_frame_rate, "camera"
    return None, "none"


def measured_fps(t: np.ndarray) -> float:
    """Frames over duration, the last frame held one median period, as ffprobe's avg_frame_rate."""
    d = np.diff(t)
    return len(t) / float(t[-1] - t[0] + np.median(d)) if len(d) and np.all(d > 0) else 0.0


def check_times(t: np.ndarray, reference: float | None) -> tuple[list[str], list[str]]:
    if len(t) < 2:
        return ["no frames"], []
    d = np.diff(t)
    if np.any(d <= 0):
        return ["timestamps broken (not strictly increasing; re-encoded/exported?), use the original file"], []
    errors = []
    duration = float(t[-1] - t[0]) + float(np.median(d))
    if duration < MIN_DURATION_S:
        errors.append(f"duration {duration:.2f} s is under {MIN_DURATION_S:.0f} s")
    rate = 1.0 / float(np.median(d))
    warnings = []
    if reference is None:
        warnings.append(f"cannot verify frame rate (median {rate:.1f} fps): no _<n>fps filename token "
                        "and not a camera original")
    elif abs(rate - reference) > MAX_RATE_OFF * reference:
        errors.append(f"timestamps broken (median rate {rate:.1f} fps vs tag {reference:.1f}; "
                      "re-encoded/exported?), use the original file")
    fps = measured_fps(t)
    if fps < MIN_FPS:
        warnings.append(f"fps {fps:.1f} is under {MIN_FPS:.0f}")
    n_gaps = int(np.sum(d > GAP_PERIODS * np.median(d)))
    if n_gaps:
        warnings.append(f"{n_gaps} frame-time gaps")
    return errors, warnings


def check_brightness(mean: float) -> list[str]:
    lo, hi = BRIGHTNESS
    return [] if lo <= mean <= hi else [f"mean brightness {mean:.0f} is outside {lo:.0f} to {hi:.0f}"]


def _ffprobe(path: Path) -> tuple[dict, dict, np.ndarray]:
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-show_entries", "packet=pts_time:format_tags", "-of", "json", str(path)],
        capture_output=True, text=True)
    if run.returncode != 0:
        raise StageStop(BAD_CLIP_EXIT, "bad_clip", f"unreadable: {run.stderr.strip()[:200]}")
    data = json.loads(run.stdout)
    if not data.get("streams"):
        raise StageStop(BAD_CLIP_EXIT, "bad_clip", "unreadable: no video stream")
    pts = [float(p["pts_time"]) for p in data.get("packets", []) if "pts_time" in p]
    tags = data.get("format", {}).get("tags", {})
    return data["streams"][0], tags, decoded_pts(np.array(pts))


def _rate(s: str) -> float:
    num, den = s.split("/")
    return int(num) / int(den) if int(den) else 0.0


def _frame_at(path: Path, t: float, size: tuple[int, int]) -> np.ndarray | None:
    w, h = size
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    if len(out) < w * h * 3:
        return None
    return np.frombuffer(out[:w * h * 3], np.uint8).reshape(h, w, 3)


def contact_sheet(frames: list[np.ndarray], times: list[float]) -> np.ndarray:
    tiles = []
    for f, t in zip(frames, times):
        scale = SHEET_HEIGHT / f.shape[0]
        tile = cv2.resize(f, (round(f.shape[1] * scale), SHEET_HEIGHT))
        cv2.putText(tile, f"{t:.2f} s", (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2)
        tiles.append(tile)
    rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
    width = max(r.shape[1] for r in rows)
    return np.vstack([np.pad(r, ((0, 0), (0, width - r.shape[1]), (0, 0))) for r in rows])


def run(ctx: Context, tmp: Path) -> None:
    stream, format_tags, pts = _ffprobe(ctx.clip)
    rotation = next((int(sd["rotation"]) for sd in stream.get("side_data_list", [])
                     if "rotation" in sd), 0)
    w, h = rotated_size(int(stream["width"]), int(stream["height"]), rotation)
    reference, reference_source = rate_reference(ctx.clip.name, _rate(stream["r_frame_rate"]), format_tags)
    errors, warnings = check_times(pts, reference)

    frames, times = [], []
    if len(pts) >= 2:
        span = pts[-1] - pts[0]
        for t in np.linspace(0, span, SHEET_FRAMES + 2)[1:-1]:
            frame = _frame_at(ctx.clip, float(t), (w, h))
            if frame is not None:
                frames.append(frame)
                times.append(float(t))
    if frames:
        warnings += check_brightness(float(np.mean([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean()
                                                    for f in frames])))
        sheet = tmp / SHEET
        sheet.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(sheet), contact_sheet(frames, times))
    elif not errors:
        errors.append("unreadable: no frame decodes")
    if errors:
        raise StageStop(BAD_CLIP_EXIT, "bad_clip", "; ".join(errors))

    np.save(tmp / "frame_times.npy", pts - pts[0])
    load_kg, load_source = load_from(ctx.params.get("load"), ctx.clip.name)
    clip = {
        "fps": round(measured_fps(pts), 6), "fps_reference": reference,
        "fps_reference_source": reference_source, "n_frames": len(pts), "size": [w, h], "rotation": rotation,
        "times_file": "frame_times.npy", "load_kg": load_kg, "load_source": load_source,
        "warnings": warnings,
    }
    (tmp / "clip.json").write_text(json.dumps(clip, indent=2) + "\n")


STAGE = Stage("S-1", (CLIP,), ("clip.json", "frame_times.npy", SHEET), run, params=("load",))
