"""Plausibility check of v2 phase marks against published snatch phase cues (#13).

usage: uv run python scripts/check_phases_literature.py
writes out/review13/literature_check.md

Cues (Harbili 2012: phases from change in direction of knee angle and bar height;
knee flexes ~7-12 deg in the transition; bar ~0.50 m at end of first pull, ~0.89 m
end of second pull. Biomechanical analysis of successful/unsuccessful snatches:
first pull 0.42 s, second pull 0.31 s, turnover 0.28 s, catch 0.24 s. ISBS knee-trunk:
pull = vbar >= 0.03 m/s up to max vbar). Bar height here = hub rise from the hub's
height at setup.
"""

from pathlib import Path

import numpy as np

from snatch.angles import mid_y, sagittal_angles
from snatch.phases import find_reps_v2
from snatch.signals import smooth, smooth_keypoints

rows = ["| rep | first pull s | transition→catch s | hub rise at transition (m) | "
        "knee max before → at transition (°, dip) | max bar speed frame vs transition |", "|---|---|---|---|---|---|"]
for clip in ["20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg", "20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg", "20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg", "20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg"]:
    raw, plate = np.load(f"out/{clip}/raw_pose.npz"), np.load(f"out/{clip}/plate.npz")
    fps = float(raw["fps"])
    ks = smooth_keypoints(raw["keypoints"], fps)
    knee = sagittal_angles(ks, "r")["knee"]
    hy = smooth(plate["hub_y"], fps)
    ppm = np.nanmedian(plate["px_per_m"][plate["found"]])
    vy = -np.gradient(hy) * fps / ppm  # m/s upward
    reps = find_reps_v2(hub_y=hy, nose_y=mid_y(ks, "nose"), hip_y=mid_y(ks, "hip"),
                        knee=knee, fps=fps, knee_y=mid_y(ks, "knee"))
    for k, r in enumerate(reps):
        s, t, c = r.setup, r.transition, r.catch
        assert t is not None and c is not None
        rise = (hy[s] - hy[t]) / ppm
        kmax = float(np.nanmax(knee[s:t]))
        vmax = s + int(np.nanargmax(vy[s:c]))
        rows.append(f"| {clip} r{k + 1} | {(t - s) / fps:.2f} | {(c - t) / fps:.2f} | "
                    f"{rise:.2f} | {kmax:.0f} → {knee[t]:.0f} (−{kmax - knee[t]:.0f}) | "
                    f"{(vmax - t) / fps * 1000:+.0f} ms |")
Path("out/review13/literature_check.md").write_text("\n".join(rows) + "\n")
print("\n".join(rows))
