"""Quick frame-rate estimate (#30): subsample the 240 fps results to 120/60/30.

usage: uv run python scripts/studies/fps_estimate.py
reads  out/<clip>/raw_pose.npz, out/<clip>/plate.npz, out/<clip>/phases_v2.json
writes out/fps_estimate.md, out/fps_estimate.json

Every 2nd/4th/8th frame of raw_pose.npz and plate.npz stands in for a run at
120/60/30 fps (the ladder files are those frames, pixel for pixel, #14).
Every start offset is used (2/4/8 per rate); offset 0 is the ladder file.
Smoothing (same window in seconds), phases v2 and the markers are re-run at
the lower rate and compared with 240 fps, rep by rep. Rep-to-rep spread is
the SD across the 6 reps at 240 fps. Approximation only: the plate Viterbi
and the pose crop tracking ran at 240 fps; #15 gives the exact answer.
"""

import json
import math
from dataclasses import asdict
from pathlib import Path

import numpy as np

from snatch.angles import JOINTS, mid_y, sagittal_angles
from snatch.studies.markers import bar_markers, group_verdict, verdict
from snatch.phases import Rep, find_reps_v2
from snatch.signals import smooth, smooth_keypoints
from snatch.spread import PHASES

CLIPS = ["20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg", "20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg", "20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg", "20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg"]
STEPS = {240: 1, 120: 2, 60: 4, 30: 8}
BAR = {"turnover_s": ("D4 turnover (to lowest bar velocity)", "ms", 1000),
       "turnover_to_bar_catch_s": ("D4 turnover (to bar catch), alt.", "ms", 1000),
       "peak_v_m_s": ("C1 peak bar velocity", "m/s", 1),
       "x1_cm": ("B2 X1", "cm", 1), "x2_cm": ("B3 X2", "cm", 1),
       "xloop_cm": ("B4 Xloop", "cm", 1), "xnet_cm": ("B5 Xnet", "cm", 1),
       "drop_cm": ("B8 drop", "cm", 1)}
GROUPS = {"phase marks": [f"E:{p}" for p in PHASES],
          "turnover (D4)": ["turnover_s", "turnover_to_bar_catch_s"],
          "peak bar velocity (C1)": ["peak_v_m_s"],
          "bar displacements (B2–B5, B8)": ["x1_cm", "x2_cm", "xloop_cm", "xnet_cm", "drop_cm"],
          "joint angles at phases": [f"{j}@{p}" for j in JOINTS for p in PHASES]}
MATCH_S = 0.5  # a rep at the lower rate is the 240 fps rep within this of its overhead start


def run(raw, plate, step: int, off: int) -> tuple[list[dict[str, float]], list[Rep]]:
    """v2 pipeline on frames off, off+step, ...; times in ms of the 240 fps clock."""
    fps = float(raw["fps"]) / step
    kps = raw["keypoints"][off::step]
    found = plate["found"][off::step]
    hub_x = smooth(plate["hub_x"][off::step], fps)
    hub_y = smooth(plate["hub_y"][off::step], fps)
    ppm = float(np.nanmedian(plate["px_per_m"][off::step][found]))
    ks = smooth_keypoints(kps, fps)
    ang = sagittal_angles(ks, "r")
    reps = find_reps_v2(hub_y=hub_y, nose_y=mid_y(ks, "nose"), hip_y=mid_y(ks, "hip"),
                        knee=ang["knee"], fps=fps, knee_y=mid_y(ks, "knee"))
    out = []
    for r in reps:
        row = {"overhead_start_ms": (r.overhead_start * step + off) / 240 * 1000}
        for p in PHASES:
            f = getattr(r, p)
            row[f"E:{p}"] = math.nan if f is None else (f * step + off) / 240 * 1000
            for j in JOINTS:
                row[f"{j}@{p}"] = math.nan if f is None else float(ang[j][f])
        row |= {k: v for k, v in asdict(bar_markers(hub_x, hub_y, ppm, fps, r)).items()
                if k in BAR}
        for k, (_, _, scale) in BAR.items():
            row[k] *= scale
        out.append(row)
    return out, reps


def label(key: str) -> tuple[str, str]:
    if key in BAR:
        return BAR[key][0], BAR[key][1]
    if key.startswith("E:"):
        return key[2:], "ms"
    return key.replace("@", " at "), "°"


ref: list[dict[str, float]] = []  # one per rep, 240 fps
deltas: dict[int, dict[str, list[float]]] = {fps: {} for fps in STEPS if fps != 240}
deltas0: dict[int, dict[str, list[float]]] = {fps: {} for fps in STEPS if fps != 240}
keys: list[str] = []
for clip in CLIPS:
    raw, plate = np.load(f"out/{clip}/raw_pose.npz"), np.load(f"out/{clip}/plate.npz")
    base, reps240 = run(raw, plate, 1, 0)
    frozen = json.loads(Path(f"out/{clip}/phases_v2.json").read_text())["reps"]
    assert [asdict(r) for r in reps240] == [{k: r[k] for k in asdict(reps240[0])}
                                           for r in frozen], f"{clip}: 240 fps differs"
    ref += base
    keys = [k for k in base[0] if k != "overhead_start_ms"]
    for fps, step in STEPS.items():
        if fps == 240:
            continue
        for off in range(step):
            rows, _ = run(raw, plate, step, off)
            for b in base:
                gap = [abs(r["overhead_start_ms"] - b["overhead_start_ms"]) for r in rows]
                m = rows[int(np.argmin(gap))] if gap and min(gap) <= MATCH_S * 1000 else None
                for k in keys:
                    if math.isnan(b[k]):
                        continue  # not detected at 240 fps either: not the lower rate's miss
                    # round off float noise from per-frame timestamps (#44): times lie on the
                    # 1/240 s grid, and a median of two grid values can be an exact .5 tie
                    d = round(m[k] - b[k], 9) if m else math.nan
                    deltas[fps].setdefault(k, []).append(d)
                    if off == 0:
                        deltas0[fps].setdefault(k, []).append(d)

spread = {k: float(np.nanstd([r[k] - (r["overhead_start_ms"] if k.startswith("E:") else 0)
                              for r in ref], ddof=1)) for k in keys}


def detected(xs: list[float]) -> np.ndarray:
    return np.abs([x for x in xs if not math.isnan(x)])


def worst(xs: list[float]) -> float:
    """Largest |Δ| over the reps that were detected."""
    d = detected(xs)
    return float(d.max()) if d.size else math.nan


def f(x: float, unit: str) -> str:
    if math.isnan(x):
        return "—"
    return f"{x:.0f}" if unit == "ms" else f"{x:.2f}" if unit == "m/s" else f"{x:.1f}"


lines = ["# Frame-rate estimate (#30): difference from 240 fps vs rep-to-rep spread", "",
         f"{len(ref)} reps from {', '.join(CLIPS)}. Δ = lower rate − 240 fps, same rep. "
         "SD = rep-to-rep SD at 240 fps (phase marks: of the event's time after the "
         "rep's overhead start). Bias = mean Δ; median and max |Δ| over all reps "
         "and start offsets, detected reps only; offset 0 = the ladder file. "
         "ratio = max |Δ| / SD. A rep not detected at all makes the marker "
         "unusable (snatch.studies.markers.verdict). Group verdict = most common marker "
         "verdict (plurality).", ""]
summary: dict[int, dict[str, str]] = {}
data: dict = {"spread": spread, "rates": {}}
for fps in deltas:
    lines += [f"## {fps} fps ({240 // fps} offsets × {len(ref)} reps)", "",
              "| marker | unit | SD 240 | bias | median \\|Δ\\| | max \\|Δ\\| | max \\|Δ\\| off 0 "
              "| ratio | verdict |", "|---|---|---|---|---|---|---|---|---|"]
    verdicts = {}
    for k in keys:
        name, unit = label(k)
        d = deltas[fps][k]
        w, missing = worst(d), sum(math.isnan(x) for x in d)
        verdicts[k] = verdict(math.nan if missing else w, spread[k])
        ratio = w / spread[k] if spread[k] else math.nan
        lines.append(f"| {name} | {unit} | {f(spread[k], unit)} | "
                     f"{f(float(np.nanmean(d)), unit)} | "
                     f"{f(float(np.median(detected(d))), unit)} | "
                     f"{f(w, unit)}{f' ({missing} missing)' if missing else ''} | "
                     f"{f(worst(deltas0[fps][k]), unit)} | {ratio:.2f} | {verdicts[k]} |")
    summary[fps] = {g: group_verdict([verdicts[k] for k in ks]) for g, ks in GROUPS.items()}
    data["rates"][fps] = {"deltas": deltas[fps], "verdicts": verdicts, "groups": summary[fps]}
    lines += [""]
lines += ["## Verdict per rate and group", "",
          "| group | " + " | ".join(f"{fps} fps" for fps in summary) + " |",
          "|---|" + "---|" * len(summary)]
lines += [f"| {g} | " + " | ".join(summary[fps][g] for fps in summary) + " |" for g in GROUPS]
Path("out/fps_estimate.md").write_text("\n".join(lines) + "\n")
Path("out/fps_estimate.json").write_text(json.dumps(
    data, indent=1).replace("NaN", "null") + "\n")
print("\n".join(lines))
