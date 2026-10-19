import json
from pathlib import Path

import numpy as np
import pytest

from snatch import athlete_store
from snatch import scale as sc
from snatch.pose import HALPE26
from snatch.skeleton import LengthTable, two_circle_knee
from snatch.stage import Context, StageStop
from snatch.stages import scale as stage

FPS, N, D_REF = 60, 120, 300.0
TAB = LengthTable(np.linspace(0.4, 1.05, 13), np.full(12, 150.0), np.full(12, 155.0), D_REF)


def _clip(bent: bool, thigh: float = 150.0, score: float = 0.9, scale: float = 1.0):
    """One 2 s attempt window, near side "r". Standing: straight leg, still hip. Bent: knee from two circles."""
    k = np.full((N, 26, 2), np.nan)
    hip, ank = np.zeros((N, 2)), np.zeros((N, 2))
    ank[:, 1] = (230 + 40 * np.sin(np.arange(N) / 10)) * scale if bent else 310 * scale
    knee, _ = two_circle_knee(hip, ank, thigh * scale, 155 * scale)
    if not bent:
        knee = np.stack([np.zeros(N), np.full(N, thigh * scale)], 1)
    for name, p in (("hip", hip), ("knee", knee), ("ankle", ank)):
        k[:, HALPE26[f"r_{name}"]] = p
    k[:, HALPE26["nose"]] = [0.0, -600.0]
    s = np.zeros((N, 26))
    s[:, :] = score
    return k, s, np.arange(N) / FPS


def test_visible_knee_skips_joints_on_the_plate() -> None:
    """R5 (#71): the first visible_knee run took the plate hub for the ankle on T2 (score >= 0.6);
    frames whose ankle is inside the plate outline must not be used, and the rest still give
    the factor (bent-leg clip at 1.2x the calibration's size)."""
    k, s, t = _clip(bent=True, scale=1.2)
    plate = {"found": np.ones(N, bool), "hub_x": np.zeros(N), "hub_y": k[:, HALPE26["r_ankle"], 1],
             "a": np.full(N, 40.0), "b": np.full(N, 40.0), "angle": np.zeros(N)}
    plate["found"][N // 2:] = False  # the ankle sits on the hub for the first half only
    res = sc.estimate(sc.smoothed(k, t, [(0, N)], "r"), s, t, [(0, N)], TAB, "r", sc.covered(k, plate, "r"))
    assert res.method == "visible_knee" and res.factor == pytest.approx(1.2, abs=0.02)
    assert (res.frames >= N // 2).all() and len(res.frames) == N // 2


def test_cannot_scale_exits_5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1: thigh / shank > 10 % off the skeleton's (another person) stops with exit 5 and still
    writes scale.json."""
    k, s, t = _clip(bent=True, thigh=210.0)
    out = tmp_path / "out"
    out.mkdir()
    np.savez(out / "raw_pose.npz", keypoints=k, scores=s, t=t)
    np.savez(out / "plate.npz", found=np.zeros(N, bool), hub_x=np.zeros(N), hub_y=np.zeros(N),
             a=np.ones(N), b=np.ones(N), angle=np.zeros(N))
    (out / "facing.json").write_text(json.dumps({"facing": "right"}))
    (out / "attempts.json").write_text(json.dumps({"attempts": [{"window": [0, N]}]}))
    athletes = tmp_path / "athletes"
    athlete_store.save(athletes, "a", athlete_store.SKELETON, {"r": TAB.to_json()})
    monkeypatch.setattr(stage, "write_overlay", lambda *a: None)
    ctx = Context(tmp_path / "clip.MOV", out, {"athlete": "a"}, athletes)
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    with pytest.raises(StageStop) as stop:
        stage.run(ctx, tmp)
    assert stop.value.code == 5 and stop.value.status == "cannot_scale"
    assert "another person" in stop.value.reason
    assert (tmp / "scale.json").is_file()
