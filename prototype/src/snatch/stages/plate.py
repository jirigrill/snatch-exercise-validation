"""S3: track the near plate in every frame (snatch.plate), check the track, draw it.

Outputs
- plate.npz: the per-frame arrays of plate.detect (`found`, hub_x/hub_y = the bar axis in rotated frame px,
  a/b/angle = outline, px_per_m, seed*, ellipse_fit) plus `t` (S-1 frame times), fps, width, height, clip,
  plate_diameter_m, model, travel_m (vertical hub travel), jumps (frame numbers where the track restarted
  away from the previous position), and the check: `passed` (found in >= 90 % of all frames, hub travels
  >= 0.4 m, no jumps; the reasons are in `status`), `hough_share` (fraction of frames whose outline was
  seeded by a Hough circle, not by gap interpolation), `moving` ([start, end) frames where the hub is
  >= 0.1 m above its lowest point), `moving_found` (found fraction inside it), `ppm_spread`
  ((p95 - p5) / median of px_per_m over found frames: the plate keeps its size, so a big spread means the
  tracker followed something else).
- plate.csv: the same per-frame fields, one row per frame.
- bar_path.png: left, the hub path over the first frame (colour = time); right, hub y and x over time.
- plate_check.jpg: zoomed crops around the plate at ~18 frames (evenly spaced, highest and lowest hub, up
  to 2 not found). Green ring = outline fitted as a circle/ellipse, yellow = the Hough circle itself (fit
  failed), red dot = hub. Check that the ring sits on the rim.
- overlays/3_plate.mp4: ring + hub dot + the hub path of the last 0.5 s. Green = the check passed, orange =
  `passed` is False.

Stops (outputs are still written, no meta, so the stage reruns)
- exit 6 `bar_only`: Hough found a plate-sized circle in under half the frames. A bar-only clip has no plate.
- exit 4 `plate_track_failed`: found in under 90 % of the moving span, or px_per_m spread above 10 %.
"""

import csv
import json
from collections.abc import Mapping
from pathlib import Path

import cv2
import matplotlib
import numpy as np

from snatch import overlay, plate
from snatch.stage import CLIP, Context, Stage, StageStop
from snatch.video import ClipInfo, frames, probe

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OVERLAY = "overlays/3_plate.mp4"
DEFAULT_RADIUS = (65.0, 260.0)  # px: v3 clips (camera far) ~95, v1 clips ~170
BAR_ONLY_EXIT = 6
TRACK_FAILED_EXIT = 4
MIN_HOUGH_SHARE = 0.5  # below: no plate in the clip (bar-only T5 0.11, plate clips >= 0.97)
MIN_MOVING_FOUND = 0.90  # found fraction required while the bar is off the floor
MAX_PPM_SPREAD = 0.10  # plate clips 0.035-0.096
MOVING_LIFT_M = 0.1  # the hub this far above the floor level counts as moving
MIN_FOUND = 0.9  # sanity check (`passed`): found in this share of all frames
MIN_TRAVEL_M = 0.4  # sanity check: every lift takes the hub at least to the hips
JUMP_SLACK_PX = 15  # a step this much beyond max speed * dt is a jump

Arrays = Mapping[str, np.ndarray]


def check(res: Arrays, t: np.ndarray, width: int, clip: str, radius: tuple[float, float]
          ) -> tuple[bool, list[str], StageStop | None, dict]:
    """Decide from the arrays alone: (passed, sanity reasons, stop or None, stats).

    stats: travel_m, jumps, hough_share, moving (start, end), moving_found, ppm_spread.
    """
    found = np.asarray(res["found"], bool)
    n = len(found)
    idx = np.flatnonzero(found)
    ppm = np.asarray(res["px_per_m"])[idx]
    median_ppm = float(np.median(ppm)) if len(idx) else float("nan")
    travel_m, jumps = 0.0, np.empty(0, int)
    moving, moving_found, ppm_spread = (0, 0), 0.0, float("nan")
    if len(idx):
        hub_x, hub_y = np.asarray(res["hub_x"]), np.asarray(res["hub_y"])
        travel_m = float(np.ptp(hub_y[found]) / median_ppm)
        max_speed = plate.MAX_SPEED_PX_S * width / 1080
        step = np.hypot(np.diff(hub_x[idx]), np.diff(hub_y[idx]))
        jumps = idx[1:][step > max_speed * np.diff(t[idx]) + JUMP_SLACK_PX]
        ppm_spread = float((np.percentile(ppm, 95) - np.percentile(ppm, 5)) / median_ppm)
        lifted = idx[(hub_y[found].max() - hub_y[idx]) / median_ppm >= MOVING_LIFT_M]
        if len(lifted):
            moving = (int(lifted[0]), int(lifted[-1]) + 1)
            moving_found = float(found[moving[0]:moving[1]].mean())
    hough_share = float((np.asarray(res["seed"]) == plate.SEED_HOUGH).mean()) if n else 0.0

    reasons = []
    if found.mean() < MIN_FOUND:
        reasons.append(f"found in only {found.mean():.0%} of frames")
    if travel_m < MIN_TRAVEL_M:
        reasons.append(f"hub travels only {travel_m:.2f} m")
    if len(jumps):
        reasons.append(f"{len(jumps)} jumps (frames {', '.join(map(str, jumps[:12]))})")
    stop = None
    if hough_share < MIN_HOUGH_SHARE:
        stop = StageStop(BAR_ONLY_EXIT, "bar_only",
                         f"No plate in {clip}: Hough found a plate-sized circle in only {hough_share:.0%} of "
                         f"frames. A bar-only clip goes to pipeline.py --calibrate <clip> --athlete <id>; "
                         f"with plates, check --radius (now {radius[0]:.0f}:{radius[1]:.0f} px).")
    elif not moving_found >= MIN_MOVING_FOUND or not ppm_spread <= MAX_PPM_SPREAD:
        stop = StageStop(TRACK_FAILED_EXIT, "plate_track_failed",
                         f"Plate track unusable in {clip}: found in {moving_found:.0%} of the moving frames "
                         f"(need {MIN_MOVING_FOUND:.0%}), px_per_m spread {ppm_spread:.3f} "
                         f"(limit {MAX_PPM_SPREAD}).")
    stats = dict(travel_m=travel_m, jumps=jumps, hough_share=hough_share, moving=moving,
                 moving_found=moving_found, ppm_spread=ppm_spread)
    return not reasons, reasons, stop, stats


def write_csv(path: Path, res: Arrays, t: np.ndarray) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", *plate.FIELDS])
        for i in range(len(t)):
            w.writerow([i, f"{t[i]:.5f}"] + [
                int(res[k][i]) if res[k].dtype == bool else
                ("" if np.isnan(res[k][i]) else f"{res[k][i]:.2f}")
                for k in plate.FIELDS])


def write_check_image(path: Path, clip: str, info: ClipInfo, res: Arrays) -> np.ndarray | None:
    """Zoomed tiles at full resolution, so a fit a few px off the rim shows. Returns frame 0."""
    found = np.asarray(res["found"], bool)
    idx = np.flatnonzero(found)
    picks: set[int] = set()
    if len(idx):
        picks = {int(idx[k]) for k in np.linspace(0, len(idx) - 1, 14).round().astype(int)}
        picks |= {int(idx[np.nanargmin(res["hub_y"][idx])]), int(idx[np.nanargmax(res["hub_y"][idx])])}
    missing = np.flatnonzero(~found)
    if len(missing):
        picks |= {int(missing[k]) for k in
                  np.linspace(0, len(missing) - 1, min(2, len(missing))).round().astype(int)}
    half = int(1.45 * float(res["r0"]))
    tile = 360
    tiles: dict[int, np.ndarray] = {}
    background = None
    for i, img in enumerate(frames(clip, info)):
        if i == 0:
            background = img.copy()
        if i not in picks:
            if i > max(picks, default=0):
                break
            continue
        o = img.copy()
        if found[i]:
            cx, cy, a, b, ang = (res[k][i] for k in ("hub_x", "hub_y", "a", "b", "angle"))
            col = (0, 255, 0) if res["ellipse_fit"][i] else (0, 255, 255)
            cv2.ellipse(o, ((cx, cy), (2 * a, 2 * b), ang), col, 2)
            cv2.circle(o, (int(cx), int(cy)), 4, (0, 0, 255), -1)
            label = f"f{i} a{a:.0f} b{b:.0f}"
        else:  # centre on the nearest found frame's hub
            k = int(idx[np.argmin(np.abs(idx - i))]) if len(idx) else 0
            cx, cy = (res["hub_x"][k], res["hub_y"][k]) if len(idx) else (info.width / 2, info.height / 2)
            label = f"f{i} NOT FOUND"
        x0, y0 = int(cx) - half, int(cy) - half
        crop = cv2.copyMakeBorder(o, half, half, half, half, cv2.BORDER_CONSTANT)[
            y0 + half:y0 + 3 * half, x0 + half:x0 + 3 * half]
        crop = cv2.resize(crop, (tile, tile))
        for th, c in ((5, (0, 0, 0)), (2, (255, 255, 255))):
            cv2.putText(crop, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, th)
        tiles[i] = crop
    row = [tiles[i] for i in sorted(tiles)] or [np.zeros((tile, tile, 3), np.uint8)]
    while len(row) % 6:
        row.append(np.zeros((tile, tile, 3), np.uint8))
    cv2.imwrite(str(path), np.vstack([np.hstack(row[k:k + 6]) for k in range(0, len(row), 6)]),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
    return background


def write_bar_path(path: Path, clip: str, info: ClipInfo, res: Arrays, t: np.ndarray,
                   background: np.ndarray | None) -> None:
    found = np.asarray(res["found"], bool)
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(14, 9), gridspec_kw={"width_ratios": [1, 1.6]})
    if background is not None:
        ax0.imshow(background[..., ::-1], alpha=0.5)
    sc = ax0.scatter(res["hub_x"], res["hub_y"], c=t, s=1, cmap="viridis")
    ax0.set_xlim(0, info.width)
    ax0.set_ylim(info.height, 0)
    ax0.set_title("hub path (rotated frame px), colour = time")
    fig.colorbar(sc, ax=ax0, label="t (s)", shrink=0.6)
    ax1.plot(t, res["hub_y"], lw=0.8, label="hub y")
    ax1.plot(t, res["hub_x"], lw=0.8, label="hub x")
    ax1.invert_yaxis()
    ax1.set_xlabel("time (s)")
    ax1.set_ylabel("px")
    ax1.legend()
    ax1.set_title(f"found {found.mean():.1%} of frames")
    fig.suptitle(f"{Path(clip).stem} — near plate hub")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def run(ctx: Context, tmp: Path) -> None:
    clip = json.loads(ctx.path("clip.json").read_text())
    t = np.load(ctx.path("frame_times.npy"))
    info = probe(str(ctx.clip))
    if info.n_frames != len(t):
        raise ValueError(f"{info.n_frames} frames decode, frame_times.npy has {len(t)}")
    lo, hi = ctx.params.get("radius") or DEFAULT_RADIUS
    path = str(ctx.clip)
    res = plate.detect(lambda: frames(path, info), t, r_min=float(lo), r_max=float(hi),
                       max_speed_px_s=plate.MAX_SPEED_PX_S * info.width / 1080, model="circle",
                       progress=lambda s, i: print(f"S3 {s} {i}/{info.n_frames}", flush=True)
                       if i % 500 == 0 else None)
    passed, reasons, stop, stats = check(res, t, info.width, ctx.clip.name, (lo, hi))
    status = "ok" if not reasons else "check: " + "; ".join(reasons)
    meta = dict(fps=clip["fps"], t=t, width=info.width, height=info.height, clip=ctx.clip.name,
                plate_diameter_m=plate.PLATE_DIAMETER_M, status=status, model="circle",
                passed=passed, **stats)
    arrays: dict[str, np.ndarray] = dict(res) | {k: np.asarray(v) for k, v in meta.items()}
    np.savez_compressed(tmp / "plate.npz", allow_pickle=False, **arrays)
    write_csv(tmp / "plate.csv", res, t)
    background = write_check_image(tmp / "plate_check.jpg", path, info, res)
    write_bar_path(tmp / "bar_path.png", path, info, res, t, background)
    if np.asarray(res["found"]).any():
        (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
        overlay.render(path, str(tmp / OVERLAY), plate=arrays, step=4, zoom=True,
                       notes=("ring, hub, 0.5 s trail", "green: ok", "orange: check"))
    print(f"S3 {status}; hough_share {stats['hough_share']:.2f} moving_found {stats['moving_found']:.2f} "
          f"ppm_spread {stats['ppm_spread']:.3f}", flush=True)
    if stop:
        raise stop


STAGE = Stage("S3", (CLIP, "clip.json", "frame_times.npy"),
              ("plate.npz", "plate.csv", "bar_path.png", "plate_check.jpg", OVERLAY), run, params=("radius",))
