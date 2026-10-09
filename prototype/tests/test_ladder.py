import numpy as np
import pytest

from snatch.studies.ladder import find_layer, keep_pts, layer_frames, temporal_id


def _nal(nal_type: int, tid: int, payload: bytes = b"\x80\x00") -> bytes:
    """Length-prefixed HEVC NAL unit (as stored in MOV/MP4 packets)."""
    body = bytes([nal_type << 1, tid + 1]) + payload
    return len(body).to_bytes(4, "big") + body


def test_temporal_id_reads_the_first_slice_not_the_sei():
    packet = _nal(39, 0) + _nal(1, 2)  # prefix SEI (tid 0), then a slice
    assert temporal_id(packet) == 2


def test_temporal_id_without_a_slice_is_an_error():
    with pytest.raises(ValueError):
        temporal_id(_nal(39, 0))


def _iphone_gop(n: int, cra_at: int | None = None):
    """Decode-order tids and pts of a 4-layer, 240 fps stream (8-frame GOP).

    Display frame k has tid 0 if k % 8 == 0, 1 if k % 4 == 0, 2 if even,
    else 3. With cra_at, the tid-0 grid shifts by 4 frames from there on, as
    in the iPhone clips (an extra tid-0 frame at each CRA).
    """
    def tid(k: int) -> int:
        k = k - cra_at if cra_at is not None and k >= cra_at else k
        return 0 if k % 8 == 0 else 1 if k % 4 == 0 else 2 if k % 2 == 0 else 3

    order = np.random.default_rng(0).permutation(n)  # decode order != display
    return [tid(int(k)) for k in order], [int(k) * 10 for k in order]


def test_layer_frames_are_in_display_order():
    tids, pts = _iphone_gop(32)
    assert layer_frames(tids, pts, max_tid=1).tolist() == [0, 4, 8, 12, 16, 20, 24, 28]


def test_find_layer_picks_the_sublayer_that_is_every_nth_frame():
    tids, pts = _iphone_gop(64)
    assert find_layer(tids, pts, step=2) == 2
    assert find_layer(tids, pts, step=4) == 1
    assert find_layer(tids, pts, step=8) == 0


def test_find_layer_rejects_a_sublayer_with_an_uneven_step():
    tids, pts = _iphone_gop(64, cra_at=36)
    assert find_layer(tids, pts, step=4) == 1
    assert find_layer(tids, pts, step=8) is None


def test_find_layer_allows_extra_frames_after_the_last_wanted_one():
    # the clip's last frame is coded in a low layer (here: frame 65 of 66)
    tids, pts = _iphone_gop(66)
    tids = [0 if p == 650 else t for t, p in zip(tids, pts)]
    assert find_layer(tids, pts, step=4) == 1
    want = keep_pts(pts, step=4)
    assert sorted(want) == [k * 10 for k in range(0, 66, 4)]
