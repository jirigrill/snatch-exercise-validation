"""Frame-rate ladder: 120/60/30 fps versions of the 240 fps clips.

Each version keeps every 2nd/4th/8th frame of the original (display order,
starting at frame 0), so ladder frame k is original frame k * step and pose
output indices map back by multiplication.

iPhone 240 fps HEVC is coded in 4 temporal sub-layers (tid 0..3). Dropping
every NAL unit above a tid is a legal sub-bitstream that decodes without
touching any pixel. Where a sub-layer is every Nth frame (plus, at most,
extra frames after the last wanted one: the clip's final frame is often
coded in a low layer, and is then dropped), its packets are remuxed as is
(original timestamps). Dropping such a trailing frame is only safe if no
kept frame references it, so every copy is verified and falls back to the
lossless re-encode if any frame differs. Where it is not (the tid-0 layer gains a frame at
each CRA, so its step is uneven), the selected frames are re-encoded
losslessly instead. Either way the decoded pixels equal the
original's, checked frame by frame.
"""

import hashlib
import subprocess
from collections.abc import Sequence

import av
import numpy as np

from snatch.video import frames

STEPS = {120: 2, 60: 4, 30: 8}  # target fps -> keep every Nth 240 fps frame


def temporal_id(packet: bytes) -> int:
    """TemporalId of the first slice in a length-prefixed HEVC packet."""
    i = 0
    while i + 6 <= len(packet):
        size = int.from_bytes(packet[i:i + 4], "big")
        nal_type = (packet[i + 4] >> 1) & 0x3F
        if nal_type < 32:  # VCL (slice) NAL unit
            return (packet[i + 5] & 7) - 1
        i += 4 + size
    raise ValueError("packet has no slice NAL unit")


def layer_frames(tids: Sequence[int], pts: Sequence[int],
                 max_tid: int) -> np.ndarray:
    """Display-order indices of the frames in sub-layers <= max_tid.

    tids, pts: per packet, in decode order.
    """
    display = np.empty(len(pts), int)
    display[np.argsort(pts)] = np.arange(len(pts))
    return np.sort(display[np.asarray(tids) <= max_tid])


def find_layer(tids: Sequence[int], pts: Sequence[int], step: int) -> int | None:
    """Sub-layer holding every `step`-th frame, extras only at the end; or None."""
    want = np.arange(0, len(pts), step)
    for max_tid in range(max(tids, default=-1) + 1):
        # got is sorted and unique, so a matching prefix leaves extras only
        # after the last wanted frame
        if np.array_equal(layer_frames(tids, pts, max_tid)[:len(want)], want):
            return max_tid
    return None


def keep_pts(pts: Sequence[int], step: int) -> set[int]:
    """pts of every `step`-th frame in display order."""
    return set(sorted(pts)[::step])


def packet_layers(path: str) -> tuple[list[int], list[int]]:
    """(tid, pts) per video packet, decode order."""
    tids, pts = [], []
    with av.open(path) as f:
        for p in f.demux(f.streams.video[0]):
            if p.size:
                assert p.pts is not None
                tids.append(temporal_id(bytes(p)))
                pts.append(int(p.pts))
    return tids, pts


def remux_layer(src: str, dst: str, max_tid: int, keep: set[int]) -> None:
    """Copy packets of sub-layers <= max_tid with pts in keep; video only."""
    with av.open(src) as inp, av.open(dst, "w") as out:
        vin = inp.streams.video[0]
        vout = out.add_stream_from_template(vin)
        for p in inp.demux(vin):
            if p.size and p.pts in keep and temporal_id(bytes(p)) <= max_tid:
                p.stream = vout
                out.mux(p)


def encode_every(src: str, dst: str, step: int) -> None:
    """Every `step`-th frame, lossless HEVC, original timestamps and rotation."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-noautorotate", "-i", src, "-map", "0:v",
         "-vf", f"select=not(mod(n\\,{step}))", "-fps_mode", "passthrough",
         "-c:v", "libx265", "-preset", "ultrafast",
         "-x265-params", "lossless=1:log-level=error", "-tag:v", "hvc1", dst],
        check=True)


def build(src: str, dst: str, step: int,
          original: Sequence[str]) -> tuple[str, list[str]]:
    """Write the every-`step`-th-frame version of src.

    original: frame_hashes(src). Returns (method, frame hashes of dst); the
    caller still checks them with `verify` (a lossless re-encode is trusted
    but not assumed).
    """
    tids, pts = packet_layers(src)
    max_tid = find_layer(tids, pts, step)
    if max_tid is not None:
        remux_layer(src, dst, max_tid, keep_pts(pts, step))
        hashes = frame_hashes(dst)
        if verify(original, hashes, step):
            return f"sub-layer tid<={max_tid}, no re-encode", hashes
        method = "lossless re-encode (sub-layer decode differed)"
    else:
        method = "lossless re-encode (sub-layer step uneven)"
    encode_every(src, dst, step)
    return method, frame_hashes(dst)


def frame_hashes(path: str) -> list[str]:
    """MD5 of each decoded, rotated frame (same decoder as the pose run)."""
    return [hashlib.md5(f.tobytes()).hexdigest() for f in frames(path)]


def verify(original: Sequence[str], ladder: Sequence[str], step: int) -> bool:
    """Ladder frame k is pixel-identical to original frame k * step."""
    return list(ladder) == list(original[::step])
