import numpy as np
import pytest

from snatch.studies import height as H
F, CY = 1500.0, 960.0  # synthetic pinhole: focal px, principal row


def proj_y(height_m: float, z: float, hc: float) -> float:
    """Image row of a point height_m above the floor at depth z (level camera)."""
    return CY + F * (hc - height_m) / z


def test_midline_ratio_matches_depths():
    zn, zf = 3.3, 4.7  # centre 4.0
    rn, rf = F * 0.225 / zn, F * 0.225 / zf
    assert H.midline_ratio(rn, rf) == pytest.approx(zn / 4.0)


def test_protocol_ratio():
    assert H.protocol_ratio(4.0, 0.7) == pytest.approx(0.825)


def test_floor_from_plate_recovers_midline_floor():
    hc, zn, zc = 0.95, 3.3, 4.0
    ppm_n = F / zn
    hub = proj_y(0.225, zn, hc)
    got = H.floor_from_plate(hub, ppm_n, zn / zc, CY)
    assert got == pytest.approx(proj_y(0.0, zc, hc))


def test_floor_from_sole_recovers_midline_floor():
    hc, zc, d, half_shoe, ha = 0.95, 4.0, 0.12, 0.05, 0.10
    px_mid = F / zc
    sole = proj_y(0.0, zc - d - half_shoe, hc)
    a_near, a_far = proj_y(ha, zc - d, hc), proj_y(ha, zc + d, hc)
    got = H.floor_from_sole(sole, a_near, a_far, px_mid, zc, hc, ha, half_shoe)
    assert got == pytest.approx(proj_y(0.0, zc, hc), abs=1.0)  # < 1 px (linearised)


def test_head_top_finds_blob_top():
    img = np.full((400, 300, 3), 200, np.uint8)
    bg = img.copy()
    img[100:250, 120:180] = 30  # head from row 100
    kps = np.zeros((17, 2))
    kps[0] = (175, 160)  # nose
    kps[1] = kps[2] = (165, 150)  # eyes
    kps[3] = kps[4] = (140, 155)  # ears
    top = H.head_top(img, bg, kps, px_per_m=400)
    assert top is not None and top[1] == pytest.approx(100, abs=1)
