"""Check one pipeline.py run in out/<clip> against snatch.stages.STAGES (run_clip.sh).

usage: uv run python check_pipeline.py <out dir> first|rerun

Every run: status ok, the stages in pipeline order, each in the state the run
expects, and every output of a stage that ran or was kept non-empty. Then each
stage's content check below, if it has one. A new stage: add it to STAGES and,
when there is something to check beyond its files existing, a function here.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

from snatch.stage import Stage
from snatch.stages import STAGES


def expected(stage: Stage, run: str) -> str:
    return "done" if stage.always or run == "first" else "skipped"


def check_probe(out: Path) -> str:
    clip = json.loads((out / "clip.json").read_text())
    t = np.load(out / "frame_times.npy")
    assert clip["n_frames"] == len(t), f"clip.json n_frames {clip['n_frames']}, frame_times {len(t)}"
    assert t[0] == 0 and np.all(np.diff(t) > 0), "frame times not from 0 and increasing"
    return f"{len(t)} frames, {clip['fps']:.1f} fps, warnings {clip['warnings']}"


def check_person(out: Path) -> str:
    p = np.load(out / "person.npz")
    t = np.load(out / "frame_times.npy")
    assert p["bbox"].shape == (len(t), 4), f"bbox {p['bbox'].shape} for {len(t)} frames"
    assert np.array_equal(p["t"], t), "person.npz t is not frame_times.npy"
    runs = len(range(0, len(t), int(p["det_every"])))
    found = int(p["detected"].sum())
    assert found >= 0.9 * runs, f"lifter found on {found} of {runs} detector runs"
    assert not np.isnan(p["bbox"]).any(), "frames without a box"
    return f"lifter on {found}/{runs} detector runs"


def check_pose(out: Path) -> str:
    p = np.load(out / "raw_pose.npz")
    t = np.load(out / "frame_times.npy")
    assert p["keypoints"].shape == (len(t), 26, 2), f"keypoints {p['keypoints'].shape} for {len(t)} frames"
    assert np.array_equal(p["t"], t), "raw_pose.npz t is not frame_times.npy"
    assert not (out / "raw_pose_partial.npz").exists(), "raw_pose_partial.npz left behind"
    posed = int((~np.isnan(p["keypoints"]).all((1, 2))).sum())
    assert posed == len(t), f"posed {posed} of {len(t)} frames (whole clip)"
    face = json.loads((out / "facing.json").read_text())["facing"]
    m = re.search(r"_(left|right)_", str(p["clip"]))
    assert m is None or m.group(1) == face, f"facing {face}, the filename says {m.group(1) if m else ''}"
    ankle = float(np.median(p["scores"][:, 15:17].max(1)))
    return f"{posed} frames posed, facing {face}, median best ankle score {ankle:.2f}"


CHECKS = {"S-1": check_probe, "S1": check_person, "S2": check_pose}


def main(out: Path, run: str) -> int:
    status = json.loads((out / "pipeline_status.json").read_text())
    got = {name: s["state"] for name, s in status["stages"].items()}
    want = {s.name: expected(s, run) for s in STAGES}
    errors = []
    if status["status"] != "ok":
        errors.append(f"status {status['status']}: {status.get('reason')}")
    if list(got) != list(want):
        errors.append(f"stage order {list(got)}, expected {list(want)}")
    elif got != want:
        errors.append(f"states {got}, expected {want}")
    print(f"{run}: {' '.join(f'{k}={v}' for k, v in got.items())}")
    for stage in STAGES:
        missing = [o for o in stage.outputs if not (out / o).is_file() or (out / o).stat().st_size == 0]
        if missing:
            errors.append(f"{stage.name}: missing {missing}")
        elif run == "first" and stage.name in CHECKS:
            try:
                print(f"  {stage.name}: {CHECKS[stage.name](out)}")
            except AssertionError as e:
                errors.append(f"{stage.name}: {e}")
    for e in errors:
        print(f"  ERROR {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2]))
