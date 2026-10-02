"""Length of the standing hold (noise-floor sample), from the plate hub.

usage: uv run python scripts/measure_hold.py out/4579
reads  out/<clip>/plate.npz, out/<clip>/raw_pose.npz
writes out/<clip>/hold.json

Hold = longest run of frames with the hub found, above the knees (bar off
the floor, at the hips) and its smoothed height staying within a 2 cm band
(px from the plate's own scale). Horizontal sway is allowed: it is part of
standing still. A speed threshold does not work here: the hub's frame-to-
frame jitter alone crosses the 50 px/s used for liftoff.
"""

import json
import sys
from pathlib import Path

import numpy as np

from snatch.angles import mid_y, sagittal_angles
from snatch.plate import longest_steady_run
from snatch.signals import smooth, smooth_keypoints

SIDE = "r"  # as in analyze.py
BAND_M = 0.02
SENSITIVITY_M = (0.01, 0.02, 0.03)

out = Path(sys.argv[1])
plate, raw = np.load(out / "plate.npz"), np.load(out / "raw_pose.npz")
fps = float(plate["fps"])
kps = raw["keypoints"]
kps_s = smooth_keypoints(kps, fps)
hx, hy = smooth(plate["hub_x"], fps), smooth(plate["hub_y"], fps)
where = plate["found"] & (hy < mid_y(kps_s, "knee"))
scale = float(np.nanmedian(plate["px_per_m"][where]))
runs = {b: longest_steady_run(hy, b * scale, where=where)
        for b in sorted({BAND_M, *SENSITIVITY_M})}
start, end = runs[BAND_M]


knee = sagittal_angles(kps_s, SIDE)["knee"][start:end]
seg = slice(start, end)
res = {
    "frames": end - start, "seconds": round((end - start) / fps, 3),
    "first_frame": start, "last_frame": end - 1,
    "t_start_s": round(start / fps, 3), "t_end_s": round((end - 1) / fps, 3),
    "band_m": BAND_M, "band_px": round(BAND_M * scale, 1),
    "frames_by_band_m": {b: runs[b][1] - runs[b][0] for b in SENSITIVITY_M},
    "hub_raw_sd_px": [round(float(np.nanstd(plate["hub_x"][seg])), 2),
                      round(float(np.nanstd(plate["hub_y"][seg])), 2)],
    "hub_minus_hip_y_px": round(float(np.mean(hy[seg] - mid_y(kps_s, "hip")[seg])), 1),
    "knee_deg_range": [round(float(knee.min()), 1), round(float(knee.max()), 1)],
    "hub_x_range_px": round(float(np.ptp(hx[seg])), 1),
    "px_per_m": round(float(np.nanmean(plate["px_per_m"][seg])), 1),
}
(out / "hold.json").write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
