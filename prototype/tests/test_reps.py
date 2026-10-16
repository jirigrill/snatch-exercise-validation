import json
from pathlib import Path

import numpy as np
import pytest

from snatch import athlete_store
from snatch.reps import find_attempts
from snatch.stage import Context, run_stages
from snatch.stages import attempts as s3

FPS = 100.0
KNEE_M, RADIUS_M = 0.5, 0.225  # a plate rolled 0.2 m up has its hub at 0.425 m: below the knee


def _t(n: int) -> np.ndarray:
    return np.arange(n) / FPS


def _lift(h: np.ndarray, start: int, up: int, top: float, hold: int, down: int) -> None:
    """Hub rises linearly to `top` m, holds, falls back to the floor."""
    h[start:start + up] = np.linspace(0, top, up)
    h[start + up:start + up + hold] = top
    h[start + up + hold:start + up + hold + down] = np.linspace(top, 0, down)


def _bounce_after_a_drop(h: np.ndarray) -> tuple[list, list]:
    _lift(h, 100, 50, 1.5, 50, 20)  # dropped, back on the floor at 220
    _lift(h, 230, 5, 0.15, 0, 5)  # bounce 10 frames later: the bar rested in between
    return [(100, 220)], [(230, 240)]


def _nudge(h: np.ndarray) -> tuple[list, list]:
    _lift(h, 100, 20, 0.2, 10, 20)  # bar rolled, never pulled
    return [], [(102, 148)]


def _no_rest_between(h: np.ndarray) -> tuple[list, list]:
    _lift(h, 100, 50, 1.0, 0, 0)
    h[150:170] = np.linspace(1.0, 0.06, 20)
    h[170:200] = 0.06  # the bar dips to 6 cm, above rest_m, and goes up again: one pull
    h[200:250] = np.linspace(0.06, 1.2, 50)
    h[250:300] = 1.2
    h[300:320] = np.linspace(1.2, 0, 20)
    return [(101, 320)], []


@pytest.mark.parametrize("case", [_bounce_after_a_drop, _nudge, _no_rest_between])
def test_find_attempts_edge_cases(case) -> None:
    """R3: a bounce after a drop, a nudge below knee height, and two rises with no rest between (no test clip has them)."""
    h = np.zeros(500)
    want_attempts, want_other = case(h)
    attempts, other = find_attempts(h, KNEE_M, RADIUS_M)
    assert [(a.start, a.end) for a in attempts] == want_attempts
    assert [(o.start, o.end) for o in other] == want_other
    assert all(a.peak_m >= KNEE_M for a in attempts) and all(o.peak_m < KNEE_M for o in other)


def test_s3_stops_with_exit_4_when_the_plate_is_lost_inside_an_attempt(tmp_path: Path, monkeypatch) -> None:
    """R1: plate found in under 90 % of an attempt (spec: re-checked after S3): exit 4 plate_track_failed."""
    monkeypatch.setattr(s3.overlay, "render", lambda *a, **k: None)
    n = 600
    h = np.zeros(n)
    _lift(h, 100, 50, 1.0, 50, 20)
    found = np.ones(n, bool)
    found[120:160] = False  # lost for a third of the attempt
    out = tmp_path / "out"
    out.mkdir()
    np.savez(out / "plate.npz", hub_y=1000 - 100 * h, found=found, px_per_m=np.full(n, 100.0))
    np.save(out / "frame_times.npy", _t(n))
    (out / "clip.json").write_text("{}")
    (tmp_path / "c.MOV").write_bytes(b"")
    athlete_store.save(tmp_path / "athletes", "a", athlete_store.ATHLETE, {"knee_height_m": KNEE_M})
    ctx = Context(tmp_path / "c.MOV", out, {"athlete": "a"}, tmp_path / "athletes")
    assert run_stages([s3.STAGE], ctx, log=lambda _: None) == 4
    data = json.loads((out / "attempts.json").read_text())
    assert data["attempts"][0]["plate_found"] < 0.9
