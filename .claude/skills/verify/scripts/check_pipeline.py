"""Check one pipeline.py run in out/<clip> against snatch.stages.STAGES (run_clip.sh).

usage: uv run python check_pipeline.py <out dir> first|rerun [--calibrate <skeleton.json>] [--stop <stage>] [--reused S,S] [--attempts N] [--scale-method M]

--calibrate: the run was pipeline.py --calibrate (snatch.stages.CALIBRATE),
and C3 wrote the skeleton.json given.
--stop: the clip stops at this stage by design (run_clip.sh's expected stops):
the stages up to it in the usual states, it `failed`, the status not ok.
--reused: on the first run these stages come from stage_cache.py (same key = same
outputs), so they are `skipped`; their content checks run all the same.
--attempts: S3 must find exactly this many attempts (run_clip.sh's expected_attempts).
--scale-method: the method S5 must report (run_clip.sh's expected_scale): standing, visible_knee or none.

Every run: status ok, the stages in pipeline order, each in the state the run
expects, and every output of a stage that ran or was kept non-empty. Then each
stage's content check below, if it has one. A new stage: add it to STAGES and,
when there is something to check beyond its files existing, a function here.

A content check also writes overlays/<overlay>.worst: the WORST frames that score
worst on the stage's own measure (line 1, frame numbers; S3: its key frames, all of them), what that is (line 2),
and the video frame of each in the overlay mp4 (line 3: the overlay draws only some frames; the frames on line 1
are always among them). run_clip.sh turns it into <overlay>_worst.jpg, so the review sees the frames where
the stage is most likely wrong, not only evenly spaced ones.
"""

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from snatch import overlay as ov
from snatch import skeleton as skel
from snatch.plate import ellipse_dist
from snatch.pose import HALPE26, SIDE_OF
from snatch.reps import Lift, height_above_floor
from snatch.stage import SKELETON, Stage
from snatch.stages import CALIBRATE, STAGES
from snatch.stages.attempts import key_frames

WORST = 4  # frames in <overlay>_worst.jpg
WORST_GAP = 24  # at least this many frames apart (0.1 s at 240 fps), so not 4 neighbours


def expected(stage: Stage, run: str, reused: frozenset[str] = frozenset()) -> str:
    return "done" if stage.always or (run == "first" and stage.name not in reused) else "skipped"


def worst(out: Path, overlay: str, badness: np.ndarray, what: str, shown: np.ndarray) -> None:
    """Write overlays/<overlay>.worst: the WORST highest-badness frames among those in `shown` (the clip
    frames the overlay draws; NaN = never), WORST_GAP apart, and (line 3) each one's index in the overlay mp4."""
    badness = np.where(np.isin(np.arange(len(badness)), shown), badness, np.nan)
    picked: list[int] = []
    for i in np.argsort(-np.nan_to_num(badness, nan=-np.inf)):
        if len(picked) == WORST or not np.isfinite(badness[i]):
            break
        if all(abs(int(i) - p) >= WORST_GAP for p in picked):
            picked.append(int(i))
    write_worst(out, overlay, picked, what, shown)


def write_worst(out: Path, overlay: str, frames: Sequence[int], what: str, shown: np.ndarray) -> None:
    """Write overlays/<overlay>.worst for explicit frames, all of which must be in `shown`."""
    if frames:
        picks = np.array(sorted(frames))
        j = np.searchsorted(shown, picks)
        assert np.array_equal(shown[np.clip(j, 0, len(shown) - 1)], picks), f"frames {picks} not all drawn"
        (out / "overlays" / f"{overlay}.worst").write_text(
            " ".join(map(str, picks)) + f"\n{what}\n" + " ".join(map(str, j)) + "\n")


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
    missed = np.full(len(t), np.nan)
    runs_at = np.arange(0, len(t), int(p["det_every"]))
    missed[runs_at[~p["detected"][runs_at].astype(bool)]] = 1.0
    worst(out, "1_person", missed, "detector runs that missed the lifter (red box)",
          ov.shown_frames(len(t), 0, None, 4, [], None))
    return f"lifter on {found}/{runs} detector runs"


def check_pose(out: Path) -> str:
    p = np.load(out / "raw_pose.npz")
    t = np.load(out / "frame_times.npy")
    assert p["keypoints"].shape == (len(t), 26, 2), f"keypoints {p['keypoints'].shape} for {len(t)} frames"
    assert np.array_equal(p["t"], t), "raw_pose.npz t is not frame_times.npy"
    assert not (out / "raw_pose_partial.npz").exists(), "raw_pose_partial.npz left behind"
    posed_mask = ~np.isnan(p["keypoints"]).all((1, 2))
    posed = int(posed_mask.sum())
    if (out / "attempts.json").exists():  # analyze: exactly the windows of S3
        windows = [a["window"] for a in json.loads((out / "attempts.json").read_text())["attempts"]]
        want = np.zeros(len(t), bool)
        for s, e in windows:
            want[s:e] = True
        assert np.array_equal(posed_mask, want), (f"posed {posed} frames, the attempt windows hold "
                                                  f"{int(want.sum())} (or other frames)")
        assert np.array_equal(p["ranges"], windows), "raw_pose.npz ranges are not the attempt windows"
        scope = "attempt windows"
    else:  # calibrate: every frame
        assert posed == len(t), f"posed {posed} of {len(t)} frames (whole clip)"
        scope = "whole clip"
    face = json.loads((out / "facing.json").read_text())["facing"]
    m = re.search(r"_(left|right)_", str(p["clip"]))
    assert m is None or m.group(1) == face, f"facing {face}, the filename says {m.group(1) if m else ''}"
    ankle = float(np.median(p["scores"][posed_mask][:, 15:17].max(1)))
    knee = HALPE26[f"{ {'right': 'r', 'left': 'l'}[face]}_knee"]
    bad = np.where(posed_mask, 1 - p["scores"][:, knee], np.nan)
    worst(out, "4_pose", bad, "lowest near-knee score (knee hidden or misplaced)",
          ov.shown_frames(len(t), 0, None, 4, [p], None))
    return f"{posed} frames posed ({scope}), facing {face}, median best ankle score {ankle:.2f}"


def check_attempts(out: Path, want: int | None = None) -> str:
    a = json.loads((out / "attempts.json").read_text())
    n = len(np.load(out / "frame_times.npy"))
    knee, radius = a["params"]["knee_height_m"], a["params"]["plate_radius_m"]
    p = np.load(out / "plate.npz")
    rise = height_above_floor(p["hub_y"], p["found"].astype(bool), p["px_per_m"], p["t"])
    assert want is None or len(a["attempts"]) == want, f"{len(a['attempts'])} attempts, expected {want}"
    for x in a["attempts"]:
        s, e = x["window"]
        assert 0 <= s <= x["start"] < x["end"] <= e <= n, f"attempt {x['attempt']}: window {s}-{e}, frames {x['start']}-{x['end']} outside 0-{n}"
        assert x["peak_m"] >= knee - 1e-9, f"attempt {x['attempt']}: peak {x['peak_m']} m below knee height {knee} m"
        assert x["plate_found"] >= 0.9, f"attempt {x['attempt']}: plate found on {x['plate_found']:.0%}"
    lifts = [Lift(x["start"], x["end"], x["peak_m"]) for x in a["attempts"]]
    others = [Lift(x["start"], x["end"], x["peak_m"]) for x in a["not_a_pull"]]
    keys = key_frames(rise, lifts, others)
    write_worst(out, "3_attempts", keys,
                f"attempt key frames: liftoff and back on the floor (hub ~{radius:.2f} m = plate radius: on the floor), "
                f"peak (must clear the knee gate {knee:.2f} m), highest not_a_pull",
                ov.shown_frames(n, 0, None, 4, [], p, extra=keys))
    spans = ", ".join(f"f{x['start']}-{x['end']} peak {x['peak_m']:.2f} m" for x in a["attempts"])
    return f"{len(a['attempts'])} attempts ({spans}), {len(a['not_a_pull'])} not_a_pull, knee {knee:.2f} m, plate radius {radius:.3f} m"


def check_calibrate(out: Path, skeleton: Path) -> str:
    face = json.loads((out / "facing.json").read_text())["facing"]
    side = {"right": "r", "left": "l"}[face]
    e = json.loads(skeleton.read_text()).get(side)
    assert e is not None, f"{skeleton} has no {side} side (facing {face})"
    assert e["clip"] == str(np.load(out / "raw_pose.npz")["clip"]), f"{side} side fitted on {e['clip']}"
    th, sh = np.asarray(e["thigh"]), np.asarray(e["shank"])
    assert len(th) == len(sh) == len(e["edges"]) - 1 and not np.isnan(th).any() and not np.isnan(sh).any(), \
        "length table has gaps"
    assert e["bins_measured"] >= 3, f"{e['bins_measured']} bins measured"
    assert th.min() + sh.min() < e["d_ref"] < th.max() + sh.max() + 10, \
        f"standing hip-ankle {e['d_ref']:.0f} px does not fit thigh + shank"
    c = json.loads((out / "calibration.json").read_text())
    assert c["side"] == side, f"calibration.json is for side {c['side']}"
    assert not {"knee_err_px", "rebuilt_frames"} & set(e), "self-test values in skeleton.json"
    err = c["knee_err_px"]
    assert err["median"] < 10, f"rebuilt knee median {err['median']} px off the visible knee"
    raw = np.load(out / "raw_pose.npz")
    _, _, k, rebuilt = skel.fit(raw["keypoints"], raw["scores"], raw["t"], face)
    knee = HALPE26[f"{side}_knee"]
    with_knee = k.copy()
    with_knee[:, knee] = np.where(np.isnan(rebuilt), k[:, knee], rebuilt)
    worst(out, "calibration_overlay", np.hypot(*(rebuilt - k[:, knee]).T),
          "rebuilt knee farthest from RTMPose's (magenta off green)",
          ov.shown_frames(len(k), 0, None, 4, [{"keypoints": k}, {"keypoints": with_knee}], None))
    return (f"{side} side, d_ref {e['d_ref']:.0f} px, thigh {th.min():.0f}-{th.max():.0f} px, "
            f"shank {sh.min():.0f}-{sh.max():.0f} px, {e['bins_measured']}/{len(th)} bins measured "
            f"(r {e['r_range'][0]}-{e['r_range'][1]}), knee rebuilt on {c['rebuilt_frames']}/{c['frames']} bent-leg frames: "
            f"median {err['median']} / p90 {err['p90']} / max {err['max']} px off the visible knee")


def check_plate(out: Path) -> str:
    p = np.load(out / "plate.npz")
    t = np.load(out / "frame_times.npy")
    n = len(t)
    found, ppm = p["found"].astype(bool), p["px_per_m"]
    assert found.shape == (n,) and ppm.shape == (n,), f"found {found.shape}, px_per_m {ppm.shape} for {n} frames"
    assert np.array_equal(p["t"], t), "plate.npz t is not frame_times.npy"
    rows = len((out / "plate.csv").read_text().strip().splitlines()) - 1
    assert rows == n, f"plate.csv has {rows} data rows for {n} frames"
    s, e = (int(x) for x in p["moving"])
    assert 0 <= s < e <= n, f"moving span {s}-{e} outside 0-{n}"
    mf = float(found[s:e].mean())
    assert mf >= 0.9, f"plate found on {mf:.0%} of the moving span {s}-{e}"
    spread, share = float(p["ppm_spread"]), float(p["hough_share"])
    assert spread <= 0.10, f"px_per_m spread {spread:.3f} > 0.10"
    assert share >= 0.5, f"hough_share {share:.2f} < 0.5"
    jumps = len(p["jumps"])
    assert bool(p["passed"]), f"sanity check not passed: {p['status']}"
    bad = np.full(n, np.nan)
    med = np.nanmedian(ppm[s:e])
    bad[s:e] = np.where(found[s:e], np.abs(ppm[s:e] / med - 1), 1.0)
    worst(out, "2_plate", bad, "px_per_m farthest from its median (plate size off), 1.0 = plate not found in the moving span",
          ov.shown_frames(n, 0, None, 4, [], p))
    return (f"found {found.mean():.0%} ({mf:.0%} of the moving span {s}-{e}), ppm_spread {spread:.3f}, "
            f"hough_share {share:.2f}, {jumps} jumps, passed {bool(p['passed'])}")


def runs_to_frames(runs: list[list[int]]) -> np.ndarray:
    return np.concatenate([np.arange(a, b) for a, b in runs]) if runs else np.zeros(0, int)


def _session(name: str) -> str:
    """The date token after the T id: `T2_20261007_...` -> `20261007`."""
    parts = name.split("_")
    return parts[1] if len(parts) > 1 else ""


def check_scale(out: Path, scale_method: str | None = None) -> str:
    sc = json.loads((out / "scale.json").read_text())
    want = {"factor", "method", "n_frames", "spread", "frames", "thigh_shank", "thigh_shank_cal"}
    assert set(sc) == want, f"scale.json fields {sorted(sc)}, expected {sorted(want)}"
    assert sc["method"] in ("standing", "visible_knee", "none"), f"method {sc['method']}"
    if scale_method:
        assert sc["method"] == scale_method, f"method {sc['method']}, expected {scale_method}"
    if sc["method"] == "none":
        assert sc["factor"] is None and sc["n_frames"] == 0, f"method none but factor {sc['factor']}, n_frames {sc['n_frames']}"
        return "method none (factor null, 0 frames): no usable frames, run goes on; proportions, plate and T1 checks skipped"
    used = runs_to_frames(sc["frames"])
    assert sc["factor"] > 0 and len(used) == sc["n_frames"] > 0, f"factor {sc['factor']}, n_frames {sc['n_frames']}"
    rel = abs(sc["thigh_shank"] / sc["thigh_shank_cal"] - 1)
    assert rel <= 0.10, f"thigh/shank {sc['thigh_shank']} vs the skeleton's {sc['thigh_shank_cal']}: {rel:.1%} off"
    p = np.load(out / "plate.npz")
    ppm = p["px_per_m"][used][p["found"].astype(bool)[used]]
    assert len(ppm), "plate not found on any frame used"
    ratio = sc["factor"] / float(np.median(ppm))
    line = (f"{sc['method']}, factor {sc['factor']:.3f} on {sc['n_frames']} frames, spread {sc['spread']:.3f}, "
            f"thigh/shank {sc['thigh_shank']:.3f} vs cal {sc['thigh_shank_cal']:.3f} ({rel:.1%}), "
            f"factor / plate px/m {ratio:.4f}")
    # recompute from the raw keypoints and the plate, as the stage does (snatch.scale.covered)
    raw = np.load(out / "raw_pose.npz")
    side = SIDE_OF[json.loads((out / "facing.json").read_text())["facing"]]
    joints = ("hip", "knee", "ankle") if sc["method"] == "visible_knee" else ("hip", "ankle")
    found = p["found"].astype(bool)
    for j in joints:
        pt = raw["keypoints"][:, HALPE26[f"{side}_{j}"]]
        with np.errstate(invalid="ignore"):
            d = ellipse_dist(pt[:, 0], pt[:, 1], p["hub_x"], p["hub_y"], p["a"], p["b"], p["angle"])
        cov = found & (d < 1)
        assert not cov[used].any(), f"near {j} inside the plate outline on {int(cov[used].sum())} frames used (first f{int(used[cov[used]][0])})"
    line += f", near {'/'.join(joints)} off the plate on every frame used"
    if sc["method"] == "standing":
        knee = float(np.median(skel.sagittal_angles(raw["keypoints"], side)["knee"][used]))
        assert knee >= skel.STAND_DEG, f"median raw near-knee angle {knee:.1f} deg on the frames used, below {skel.STAND_DEG:.0f}"
        line += f", median raw knee {knee:.1f} deg"
        for a in json.loads((out / "attempts.json").read_text())["attempts"]:
            s, e = a["window"]
            assert ((used >= s) & (used < e)).any(), f"attempt {a['attempt']}: no standing window in frames {s}-{e}"
        line += ", a window in each attempt"
    t1 = [d for d in out.parent.glob("T1_*") if (d / "scale.json").is_file()]
    if t1 and not out.name.startswith("T1_"):
        r1 = json.loads((t1[0] / "scale.json").read_text())
        u1 = runs_to_frames(r1["frames"])
        p1 = np.load(t1[0] / "plate.npz")
        ref = r1["factor"] / float(np.median(p1["px_per_m"][u1][p1["found"].astype(bool)[u1]]))
        dev = ratio / ref - 1
        same = _session(out.name) == _session(t1[0].name)
        if same:
            assert abs(dev) <= 0.05, f"factor / plate px/m {ratio:.4f} is {dev:+.1%} from T1's {ref:.4f} (limit 5%)"
            line += f", vs T1's {ref:.4f}: {dev:+.1%}"
        else:
            line += f", vs T1's {ref:.4f}: {dev:+.1%} (other session, reported only)"
    # no worst-frames sheet: 5_scale is a jpg, worst() and run_clip.sh's sheets need an mp4 overlay
    return line


CHECKS = {"S-1": check_probe, "S1": check_person, "S4": check_pose, "S2": check_plate, "S3": check_attempts, "S5": check_scale}
# Files a stage still writes when it stops the run (checked on a --stop run; no content check).
STOP_FILES = {"S2": ("plate_check.jpg", "overlays/2_plate.mp4"),
              "S3": ("attempts.json", "overlays/3_attempts.mp4")}


def main(out: Path, run: str, skeleton: Path | None = None, stop: str | None = None,
         reused: frozenset[str] = frozenset(), attempts: int | None = None, scale_method: str | None = None) -> int:
    stages = CALIBRATE if skeleton else STAGES
    if stop:
        stages = stages[:[s.name for s in stages].index(stop) + 1]
    checks = CHECKS | {"S3": lambda o: check_attempts(o, attempts), "S5": lambda o: check_scale(o, scale_method)} | ({"C3": lambda o: check_calibrate(o, skeleton)} if skeleton else {})
    status = json.loads((out / "pipeline_status.json").read_text())
    got = {name: s["state"] for name, s in status["stages"].items()}
    want = {s.name: expected(s, run, reused) for s in stages} | ({stop: "failed"} if stop else {})
    errors = []
    if stop and status["status"] == "ok":
        errors.append(f"status ok, expected a stop at {stop}")
    elif not stop and status["status"] != "ok":
        errors.append(f"status {status['status']}: {status.get('reason')}")
    if list(got) != list(want):
        errors.append(f"stage order {list(got)}, expected {list(want)}")
    elif got != want:
        errors.append(f"states {got}, expected {want}")
    print(f"{run}: {' '.join(f'{k}={v}' for k, v in got.items())}")
    for stage in (s for s in stages if s.name != stop):
        paths = [skeleton if o == SKELETON else out / o for o in stage.outputs]
        missing = [str(p) for p in paths if p is None or not p.is_file() or p.stat().st_size == 0]
        if missing:
            errors.append(f"{stage.name}: missing {missing}")
        elif run == "first" and stage.name in checks:
            try:
                print(f"  {stage.name}: {checks[stage.name](out)}")
            except AssertionError as e:
                errors.append(f"{stage.name}: {e}")
    for o in STOP_FILES.get(stop or "", ()):
        if not (out / o).is_file() or (out / o).stat().st_size == 0:
            errors.append(f"{stop}: stopped but {o} is missing or empty")
    if stop and not errors:
        print(f"  {stop}: stopped as expected: {status.get('reason')}")
    for e in errors:
        print(f"  ERROR {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("run", choices=("first", "rerun"))
    ap.add_argument("--calibrate", type=Path, metavar="SKELETON_JSON")
    ap.add_argument("--stop", choices=[s.name for s in STAGES + CALIBRATE])
    ap.add_argument("--attempts", type=int, help="expected number of S3 attempts")
    ap.add_argument("--scale-method", choices=("standing", "visible_knee", "none"), help="the method S5 must report")
    ap.add_argument("--reused", default="", help="comma-separated stages restored by stage_cache.py")
    a = ap.parse_args()
    raise SystemExit(main(a.out, a.run, a.calibrate, a.stop,
                     frozenset(filter(None, a.reused.split(","))), a.attempts, a.scale_method))
