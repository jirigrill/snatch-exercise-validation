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
import csv
import json
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from snatch import athlete_store
from snatch import fill as fl
from snatch import overlay as ov
from snatch import scale as sca
from snatch import skeleton as skel
from snatch.plate import ellipse_dist
from snatch import judge as jd
from snatch import phases as ph
from snatch.pose import HALPE26, SIDE_OF
from snatch.reps import Lift, height_above_floor
from snatch.stage import SKELETON, Stage
from snatch.stages import CALIBRATE, STAGES
from snatch.stages import judge as sj
from snatch.stages.attempts import key_frames

REPO = Path(__file__).resolve().parents[4]
S7_REFERENCE = REPO / "prototype/tests/data/s7_reference.json"  # S7 reference border frames + tolerances (+ "passing"); a change detector, not ground truth
WORST = 4  # frames in <overlay>_worst.jpg
BODY_PX_PER_M_CAL = 352.8  # body px/m of the T5 calibration session (docs/results/35-body-height.md); x S5's factor = this clip's
HOLDOUT_GATE_CM = 3.0  # S6 hide-a-seen-knee: median knee position error above this FAILs
HOLDOUT_TARGET_CM = 2.0
MIN_HOLDOUT_FRAMES = 40  # fewer candidate frames: reported, not gated
DIP_DEG = 3.0  # a knee re-bend: the angle drops and recovers by this much
SPEC_HIDDEN_DIST = 1.1  # spec (C-skeleton.md): hidden = inside the plate ellipse x 1.1; a literal, not fill.HIDDEN_DIST, so a drift fails S6
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
    want = {"factor", "method", "n_frames", "spread", "frames", "thigh_shank", "thigh_shank_cal",
            "thigh_factor", "shank_factor", "segment_frames", "segment_source"}
    assert set(sc) == want, f"scale.json fields {sorted(sc)}, expected {sorted(want)}"
    assert sc["method"] in ("standing", "visible_knee", "none"), f"method {sc['method']}"
    if scale_method:
        assert sc["method"] == scale_method, f"method {sc['method']}, expected {scale_method}"
    if sc["method"] == "none":
        assert sc["factor"] is None and sc["n_frames"] == 0, f"method none but factor {sc['factor']}, n_frames {sc['n_frames']}"
        assert (sc["thigh_factor"], sc["shank_factor"], sc["segment_frames"], sc["segment_source"]) == (None, None, 0, "none"), \
            f"method none but segment fields {sc['thigh_factor']}, {sc['shank_factor']}, {sc['segment_frames']}, {sc['segment_source']}"
        return "method none (factor null, 0 frames): no usable frames, run goes on; proportions, plate and T1 checks skipped"
    used = runs_to_frames(sc["frames"])
    assert sc["factor"] > 0 and len(used) == sc["n_frames"] > 0, f"factor {sc['factor']}, n_frames {sc['n_frames']}"
    rel = abs(sc["thigh_shank"] / sc["thigh_shank_cal"] - 1)
    assert rel <= 0.10, f"thigh/shank {sc['thigh_shank']} vs the skeleton's {sc['thigh_shank_cal']}: {rel:.1%} off"
    seg = sc["segment_source"] == "visible_knee"
    assert sc["segment_source"] in ("visible_knee", "factor_only") and seg == (sc["segment_frames"] > 0), \
        f"segment_source {sc['segment_source']} with {sc['segment_frames']} frames"
    assert sc["thigh_factor"] > 0 and sc["shank_factor"] > 0 and (seg or (sc["thigh_factor"], sc["shank_factor"]) == (1.0, 1.0)), \
        f"thigh_factor {sc['thigh_factor']}, shank_factor {sc['shank_factor']} from {sc['segment_frames']} frames"
    p = np.load(out / "plate.npz")
    ppm = p["px_per_m"][used][p["found"].astype(bool)[used]]
    assert len(ppm), "plate not found on any frame used"
    ratio = sc["factor"] / float(np.median(ppm))
    line = (f"{sc['method']}, factor {sc['factor']:.3f} on {sc['n_frames']} frames, spread {sc['spread']:.3f}, "
            f"thigh/shank {sc['thigh_shank']:.3f} vs cal {sc['thigh_shank_cal']:.3f} ({rel:.1%}), "
            f"factor / plate px/m {ratio:.4f}, thigh x{sc['thigh_factor']:.3f} shank x{sc['shank_factor']:.3f} "
            f"({sc['segment_source']}, {sc['segment_frames']} frames)")
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


def dips(a: np.ndarray, deg: float = DIP_DEG) -> int:
    """Knee dips in an angle series: a drop of >= deg from a local max that then recovers by >= deg."""
    a = a[~np.isnan(a)]
    if not len(a):
        return 0
    n, high, low, falling = 0, a[0], a[0], False
    for x in a[1:]:
        if falling:
            low = min(low, x)
            if x >= low + deg:
                n, falling, high = n + 1, False, x
        else:
            high = max(high, x)
            if x <= high - deg:
                falling, low = True, x
    return n


def check_fill(out: Path) -> str:
    pose = np.load(out / "pose.npz")
    raw = np.load(out / "raw_pose.npz")
    plate = dict(np.load(out / "plate.npz"))
    sc = json.loads((out / "scale.json").read_text())
    attempts = json.loads((out / "attempts.json").read_text())["attempts"]
    windows = [(int(a["window"][0]), int(a["window"][1])) for a in attempts]
    side = SIDE_OF[json.loads((out / "facing.json").read_text())["facing"]]
    sign = 1.0 if side == "r" else -1.0
    n = len(raw["t"])
    kp, filled, hidden = pose["keypoints"], pose["filled"], pose["hidden"]
    assert kp.shape == (n, 26, 2) and filled.shape == hidden.shape == (n, 26), \
        f"keypoints {kp.shape}, hidden {hidden.shape}, filled {filled.shape} for {n} frames"
    assert pose["scores"].shape == (n, 26) and np.array_equal(pose["t"], raw["t"]), "scores / t differ from raw_pose.npz"
    assert np.array_equal(pose["ranges"], raw["ranges"]), "ranges differ from raw_pose.npz"
    assert filled.dtype == hidden.dtype == bool, f"hidden {hidden.dtype}, filled {filled.dtype}"
    assert np.array_equal(np.isnan(kp), np.isnan(raw["keypoints"])), "NaN frames differ from raw_pose.npz"
    j = {m: HALPE26[f"{side}_{m}"] for m in ("hip", "knee", "ankle")}
    others = np.ones(26, bool)
    others[j["knee"]] = False
    assert np.array_equal(kp[:, others], raw["keypoints"][:, others], equal_nan=True), "a joint other than the near knee changed"
    assert not filled[:, others].any(), "something other than the near knee is filled"
    kept = ~filled[:, j["knee"]]
    assert np.array_equal(kp[kept, j["knee"]], raw["keypoints"][kept, j["knee"]], equal_nan=True), "the near knee changed on a frame not marked filled"
    hid = sca.covered(raw["keypoints"], plate, side, SPEC_HIDDEN_DIST)
    assert np.array_equal(hidden[:, list(j.values())], hid), "hidden is not the near hip/knee/ankle inside the plate outline"
    assert not hidden[:, [i for i in range(26) if i not in j.values()]].any(), "hidden outside the near hip, knee, ankle"
    fade = fl.fade_frames(raw["t"])
    near = np.convolve(hidden[:, j["knee"]].astype(float), np.ones(fade), mode="same") > 0  # hidden, grown by the cross-fade
    assert not (filled[:, j["knee"]] & ~near).any(), f"knee filled more than {fade // 2} frames from a hidden frame"
    if sc["method"] == "none":
        assert not filled.any(), "scale method none, yet something is filled"
    t = np.asarray(raw["t"], float)
    k = sca.smoothed(raw["keypoints"], t, windows, side)
    # worst: filled knee frames first (hybrid vs RTMPose's knee, biggest first), then hidden-not-filled, then the rest
    gap = np.hypot(*(kp[:, j["knee"]] - raw["keypoints"][:, j["knee"]]).T)
    rank = np.where(filled[:, j["knee"]], 2e6, np.where(hidden[:, list(j.values())].any(1), 1e6, 0.0)) + np.nan_to_num(gap)
    worst(out, "6_filled", rank, "filled frames first: hybrid knee farthest from RTMPose's (purple vs grey), then hidden "
          "joints that were not filled (ring), then the rest", ov.shown_frames(n, 0, None, 4, [pose], None))
    line = f"{int(filled[:, j['knee']].sum())} knee frames filled, {int(hidden[:, j['knee']].sum())} hidden"
    if sc["method"] == "none":
        return line + "; scale method none: nothing filled, hold-out skipped"
    return line + "; " + _holdout(out, raw, plate, sc, windows, side, sign, k) + "; " + _rebend(out, pose, raw, attempts, windows, side)


def _holdout(out: Path, raw, plate: dict, sc: dict, windows, side: str, sign: float, k: np.ndarray) -> str:
    """Hide a seen knee: rebuild it on frames where it is visible and compare, two folds by time."""
    sk = athlete_store.load(out.parent / "athletes", "verify", athlete_store.SKELETON)
    assert sk, "no skeleton.json in the root's athletes/verify"
    tab = skel.LengthTable.from_json(sk[side])
    j = {m: HALPE26[f"{side}_{m}"] for m in ("hip", "knee", "ankle")}
    hip, knee, ank = k[:, j["hip"]], k[:, j["knee"]], k[:, j["ankle"]]
    hid = sca.covered(raw["keypoints"], plate, side, SPEC_HIDDEN_DIST)
    inside = np.zeros(len(k), bool)
    for s, e in windows:
        inside[s:e] = True
    ang = skel.joint_angle(hip, knee, ank)
    scaled = tab.scaled(sc["factor"])
    with np.errstate(invalid="ignore"):
        _, ok_all = fl.rebuild(hip, ank, scaled, sc["thigh_factor"], sc["shank_factor"], sign)
        cand = (inside & (raw["scores"][:, j["knee"]] >= skel.MIN_SCORE) & ~hid.any(1) & (ang >= sca.SEG_MIN_DEG)
                & (ang < sca.SEG_MAX_DEG) & ok_all)
    idx = np.flatnonzero(cand)
    if len(idx) < MIN_HOLDOUT_FRAMES:
        return f"hold-out: too few frames ({len(idx)})"
    cov = sca.covered(raw["keypoints"], plate, side)
    cm_per_px = 100 / (BODY_PX_PER_M_CAL * sc["factor"])
    folds = []
    for fit, test in ((idx[:len(idx) // 2], idx[len(idx) // 2:]), (idx[len(idx) // 2:], idx[:len(idx) // 2])):
        tf, sf, used = sca.segment_factors(k, raw["scores"], windows, tab, side, cov, sc["factor"], fit)
        reb, ok = fl.rebuild(hip[test], ank[test], scaled, tf, sf, sign)
        pos = np.hypot(*(reb - knee[test]).T)[ok] * cm_per_px
        deg = np.abs(skel.joint_angle(hip[test], reb, ank[test]) - ang[test])[ok]
        folds.append((float(np.median(pos)), float(np.median(deg)), len(test), len(used), tf, sf))
    pos, deg = (float(np.mean([f[i] for f in folds])) for i in (0, 1))
    assert pos <= HOLDOUT_GATE_CM, f"hold-out knee position error {pos:.1f} cm > {HOLDOUT_GATE_CM} cm: {folds}"
    per = "; ".join(f"fold {i + 1}: {f[0]:.1f} cm {f[1]:.1f} deg on {f[2]} frames, fitted on {f[3]} x{f[4]:.3f}/x{f[5]:.3f}"
                    for i, f in enumerate(folds))
    return f"hold-out {pos:.1f} cm (target {HOLDOUT_TARGET_CM:.0f}, gate {HOLDOUT_GATE_CM:.0f}), {deg:.1f} deg, {len(idx)} frames ({per})"


def _rebend(out: Path, pose, raw, attempts: list[dict], windows, side: str) -> str:
    """Knee dips between each attempt's start and bar peak: the hybrid must not have more than RTMPose."""
    t = np.asarray(raw["t"], float)
    p = np.load(out / "plate.npz")
    rise = height_above_floor(p["hub_y"], p["found"].astype(bool), p["px_per_m"], p["t"])
    ang = {name: skel.sagittal_angles(sca.smoothed(kp, t, windows, side), side)["knee"]
           for name, kp in (("hybrid", pose["keypoints"]), ("rtmpose", raw["keypoints"]))}
    per: list[dict[str, int]] = []
    for a in attempts:
        peak = a["start"] + int(np.nanargmax(rise[a["start"]:a["end"]]))
        per.append({name: dips(ang[name][a["start"]:peak + 1]) for name in ang})
    for i, d in enumerate(per):
        assert d["hybrid"] <= d["rtmpose"], \
            f"re-bend, attempt {i + 1}: hybrid {d['hybrid']} knee dips >= {DIP_DEG:.0f} deg, RTMPose {d['rtmpose']}"
    return "re-bend dips (start to peak): " + ", ".join(
        f"a{i + 1} hybrid {d['hybrid']}, RTMPose {d['rtmpose']}" for i, d in enumerate(per))


def s7_errors(out: Path, ref: dict, clip: str) -> dict[str, dict[str, tuple[int | None, int | None, float | None, bool]]]:
    """{attempt: {border: (true frame, S7 frame, S7 - true in s or None, passes)}} for a clip in the reference.
    Passes: both null, or both frames within tolerance_s (time from frame_times.npy)."""
    rec = json.loads((out / "phases.json").read_text())
    t = np.load(out / "frame_times.npy")
    res: dict[str, dict[str, tuple[int | None, int | None, float | None, bool]]] = {}
    for r in rec["attempts"]:
        truth = ref["clips"][clip].get(str(r["attempt"]))
        if truth is None:
            continue
        row = {}
        for n in ph.BORDERS:
            tf = truth[n]["frame"]
            sf = r["borders"][n]["frame"] if r["borders"][n] else None
            if tf is None or sf is None:
                row[n] = (tf, sf, None, tf is None and sf is None)
            else:
                d = float(t[sf] - t[tf])
                row[n] = (tf, sf, d, abs(d) <= ref["tolerance_s"][n] + 1e-9)
        res[str(r["attempt"])] = row
    return res


def s7_regression(out: Path, clip: str, ref_path: Path = S7_REFERENCE) -> tuple[list[str], list[str], list[str]]:
    """(detail lines, regressions, improvements) of S7 vs the true frames; ([], [], []) for a clip not in the reference."""
    ref = json.loads(ref_path.read_text())
    if clip not in ref["clips"]:
        return [], [], []
    lines, bad, better = [], [], []
    for k, row in s7_errors(out, ref, clip).items():
        passing = ref.get("passing", {}).get(clip, {}).get(k, [])
        cells = []
        for n, (tf, sf, d, ok) in row.items():
            cells.append(f"{n} {'null' if sf is None else 'S7 ' + str(sf)} vs {'null' if tf is None else tf}"
                         + (f" {d:+.3f}s" if d is not None else "") + (" pass" if ok else " FAIL"))
            if n in passing and not ok:
                bad.append(f"{clip} a{k} {n}")
            if ok and n not in passing:
                better.append(f"{clip} a{k} {n}")
        lines.append(f"a{k} vs reference: " + "; ".join(cells) + f" ({sum(v[3] for v in row.values())}/{len(row)} pass)")
    return lines, bad, better


def check_phases(out: Path) -> str:
    rec = json.loads((out / "phases.json").read_text())
    attempts = json.loads((out / "attempts.json").read_text())["attempts"]
    pose = np.load(out / "pose.npz")
    assert [r["attempt"] for r in rec["attempts"]] == [a["attempt"] for a in attempts], "phases.json: not one record per attempt"
    assert rec["params"] == ph.PARAMS, "phases.json params are not the code's thresholds"
    clip = out.name.split("_")[0]  # T1 ...
    lines = []
    hub = np.full(len(pose["keypoints"]), np.nan)
    with (out / "angles.csv").open() as f:
        for row in csv.DictReader(f):
            hub[int(row["frame"])] = float(row["hub_y"])
    ppm = np.asarray(np.load(out / "plate.npz")["px_per_m"], float)
    for r, a in zip(rec["attempts"], attempts):
        k, (s, e) = r["attempt"], a["window"]
        assert r["window"] == [s, e], f"attempt {k}: window {r['window']} is not attempts.json's {[s, e]}"
        b = r["borders"]
        assert list(b) == list(ph.BORDERS), f"attempt {k}: borders {list(b)}"
        frames = [(n, b[n]["frame"]) for n in ph.BORDERS if b[n]]
        assert all(s <= f < e for _, f in frames), f"attempt {k}: a border outside the window {s}-{e}: {frames}"
        assert [f for _, f in frames] == sorted(f for _, f in frames), f"attempt {k}: borders out of order: {frames}"
        oh = r["bar_overhead"]
        if oh:
            assert s <= oh["start"] < oh["end"] <= e, f"attempt {k}: bar_overhead {oh} outside the window"
            assert all(f < oh["end"] for _, f in frames), f"attempt {k}: a border after bar_overhead end {oh['end']}"
        assert (oh is None) == (b["bar_lowest"] is None and b["standing"] is None), \
            f"attempt {k}: bar_overhead {oh}, bar_lowest {b['bar_lowest']}, standing {b['standing']} (null together)"
        assert [p["name"] for p in r["phases"]] == [n for n, *_ in ph.PHASES], f"attempt {k}: phase names"
        for p, (_, x, y) in zip(r["phases"], ph.PHASES):
            want_s = s if x is None else (b[x]["frame"] if b[x] else None)
            want_e = (oh["end"] if oh else None) if y is None else (b[y]["frame"] if b[y] else None)
            if y is None and oh and b["standing"]:  # hold end: recomputed from angles.csv hub_y + plate.npz px_per_m
                want_e = ph.hold_end(hub, ppm, b["standing"]["frame"], oh["end"])
            assert (p["start"], p["end"]) == (want_s, want_e), f"attempt {k}: phase {p['name']} {p['start']}-{p['end']}, borders say {want_s}-{want_e}"
        for n, f in frames:
            assert (out / "grabs" / f"a{k}_{n}.jpg").is_file(), f"attempt {k}: grabs/a{k}_{n}.jpg missing"
        assert len(list((out / "grabs").glob(f"a{k}_*.jpg"))) == len(frames), f"attempt {k}: grabs without a border"
        if clip in ("T3", "T7"):
            assert oh is None, f"attempt {k}: {clip} never goes overhead, bar_overhead {oh}"
        elif clip in ("T1", "T2", "T6", "T8"):
            assert oh, f"attempt {k}: {clip} goes overhead, bar_overhead null"
            for n in ("liftoff", "full_extension", "bar_peak", "bar_lowest", "standing"):
                assert b[n], f"attempt {k}: {clip} border {n} is null"
        lines.append(f"a{k} " + " ".join(f"{n}={b[n]['frame'] if b[n] else 'null'}" for n in ph.BORDERS)
                     + (f" overhead {oh['start']}-{oh['end']} hold_end={r['phases'][-1]['end']}" if oh else " no overhead"))
    rows = [ln for ln in (out / "angles.csv").read_text().splitlines()[1:]]
    posed = int((~np.isnan(pose["keypoints"]).all((1, 2))).sum())
    assert len(rows) == posed == sum(a["window"][1] - a["window"][0] for a in attempts), \
        f"angles.csv {len(rows)} rows, {posed} posed frames"
    ref_lines, bad, better = s7_regression(out, clip)
    lines += ref_lines
    for b in better:
        lines.append(f"improved: {b}, update passing in s7_reference.json")
    assert not bad, f"S7 moved off the reference frames (agreed per s7_reference.json 'passing', not now): {bad}; " + "; ".join(ref_lines)
    return "\n    ".join(lines)


def check_judgement(out: Path) -> str:
    rec = json.loads((out / "judgement.json").read_text())
    phases = json.loads((out / "phases.json").read_text())["attempts"]
    assert [r["attempt"] for r in rec["attempts"]] == [p["attempt"] for p in phases], "judgement.json: not one record per attempt"
    assert rec["params"] == jd.PARAMS, "judgement.json params are not the code's thresholds"
    lines, worst_frames = [], set()
    for j, p in zip(rec["attempts"], phases):
        k, (s, e) = j["attempt"], p["window"]
        c = j["checks"]
        assert list(c) == list(jd.CHECKS), f"attempt {k}: checks {list(c)}"
        res = {n: v["result"] for n, v in c.items()}
        assert set(res.values()) <= {"pass", "fail", "unsure", "skipped"}, f"attempt {k}: results {res}"
        fails = [n for n in jd.CHECKS if res[n] == "fail"]
        unsure = [n for n in jd.CHECKS if res[n] == "unsure"]
        want = ("failed", fails[0]) if fails else ("unknown", "low_confidence") if unsure else ("completed", None)
        assert (j["lift_result"], j["reason"]) == want, f"attempt {k}: {j['lift_result']} {j['reason']}, checks say {want}: {res}"
        assert (res["no_overhead"] == "fail") == (p["bar_overhead"] is None), f"attempt {k}: no_overhead {res['no_overhead']} vs bar_overhead {p['bar_overhead']}"
        assert j["performed_type"] in (*jd.TYPES, "unknown") and j["intended_source"] in ("param", "labels", "inferred")
        ev = j["evidence_frames"]
        assert (ev is None) == (j["reason"] is None), f"attempt {k}: evidence_frames {ev} with reason {j['reason']}"
        if ev is not None:
            assert ev == c[j["reason"]]["frames"] and s <= ev[0] <= ev[1] <= e, f"attempt {k}: evidence_frames {ev} outside the window {s}-{e}"
        for n, v in c.items():
            if v["frames"] is not None:
                assert s <= v["frames"][0] <= v["frames"][1] <= e, f"attempt {k}: {n} frames {v['frames']} outside {s}-{e}"
            if v.get("worst") is not None:
                assert s <= v["worst"] < e, f"attempt {k}: {n} worst {v['worst']} outside {s}-{e}"
                if v["result"] in ("fail", "unsure"):
                    worst_frames.add(v["worst"])
        lines.append(f"a{k} {j['performed_type']} (intended {j['intended_type']}, {j['intended_source']}): "
                     f"{j['lift_result']} {j['reason'] or ''} | " + " ".join(f"{n}={res[n]}" for n in jd.CHECKS))
    pose = np.load(out / "pose.npz")
    shown = ov.shown_frames(len(pose["keypoints"]), 0, None, 4, [{"keypoints": pose["keypoints"]}], None,
                            sorted(sj.worst_frames(rec["attempts"])))
    picks = sorted(f for f in worst_frames if f in set(shown.tolist()))[:WORST]
    write_worst(out, "8_judgement", picks, "S8: the worst frame of each failed / unsure check (drawn ones)", shown)
    return "\n    ".join(lines)


CHECKS = {"S-1": check_probe, "S1": check_person, "S4": check_pose, "S2": check_plate, "S3": check_attempts, "S5": check_scale, "S6": check_fill, "S7": check_phases, "S8": check_judgement}
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
        missing = [str(p) for p in paths if p is None or not (any(f.is_file() and f.stat().st_size for f in p.rglob("*")) if p.is_dir()
                                                              else p.is_file() and p.stat().st_size)]
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
