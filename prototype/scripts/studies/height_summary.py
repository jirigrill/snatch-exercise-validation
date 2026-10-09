"""Pool body-height estimates (out/<clip>/height.json from body_height.py) across clips (#22).

usage: uv run python scripts/studies/height_summary.py --scale-clips out/<a>,out/<b>,... out/<clip> [...]
           [--shoe-cm 2.5] [--k 0.825]
reads  out/<clip>/height.json
writes nothing; prints markdown tables and the pooled estimate

Scale at the bar centre (body midline), per plated clip, two ways:
  S_lock = k_far * near-plate px/m at lockout (circle-equivalent radius sqrt(a*b))
  S_rest = k_far * near-plate px/m with the bar resting on the floor (plate.npz)
  (k_floor, the floor-line depth check: (midline floor row - cy) / (resting
  plate's bottom row - cy), cy = image centre; printed, not used.)
The two disagree by ~1.5% (the plate reads ~2% nearer at lockout); the
estimate uses their mean and reports both.
Direct height: head top to the midline floor (from the near sole), "hips"
frames only. Clips without their own plate scale (bar only) use the session
scale: the median over --scale-clips (same tripod spot as the bar-only clips).
Eye-based (lockout frames, plated clips): near-eye keypoint to the midline
floor + head top above the eye (median of the session's direct frames). The
ear is not used overhead: the upper arm covers it and its keypoint is guessed.
"""

import json
import sys
from pathlib import Path

import numpy as np

args = sys.argv[1:]


def option(flag: str, default: str | None = None) -> str | None:
    if flag not in args:
        return default
    i = args.index(flag)
    v = args[i + 1]
    del args[i:i + 2]
    return v


shoe = float(option("--shoe-cm", "2.5") or 2.5)
k_fix = option("--k")  # depth ratio for every plated clip instead of its far plate (sensitivity)
scale_clips = [Path(p).name for p in (option("--scale-clips", "") or "").split(",") if p]
data = {Path(p).name: json.loads((Path(p) / "height.json").read_text()) for p in args}
for p in scale_clips:
    if p not in data:
        data[p] = json.loads((Path("out") / p / "height.json").read_text())
CY = 960.0


def scales(d: dict) -> dict | None:
    s, rows = d["summary"], d["rows"]
    if s["scale_from"] or not s["k_far_n"]:
        return None
    circ = float(np.median([np.sqrt(r["near_fit"][2] * r["near_fit"][3]) for r in rows])) / 0.225
    fs = float(np.median([r["floor_sole_y"] for r in rows if r.get("floor_sole_y")]))
    y_fp = s["hub_rest_y"] + s["px_per_m_rest"] * 0.225
    k = float(k_fix) if k_fix else s["k_far_median"]
    return {"k_far": k, "k_floor": (fs - CY) / (y_fp - CY), "lock": k * circ,
            "rest": k * s["px_per_m_rest"], "floor_y": fs, "plate_floor_y": s["floor_plate_y"]}


sc = {c: scales(d) for c, d in data.items()}
print("| clip | k far plate (n) | k floor line | S_lock px/m | S_rest px/m | midline floor row (sole / plate) |")
print("|---|---|---|---|---|---|")
for c, v in sc.items():
    if v:
        print(f"| {c} | {v['k_far']:.4f} ({data[c]['summary']['k_far_n']}) | {v['k_floor']:.4f} "
              f"| {v['lock']:.1f} | {v['rest']:.1f} | {v['floor_y']:.0f} / {v['plate_floor_y']:.0f} |")
ses = [v for c in scale_clips if (v := sc.get(c))]
s_lock = float(np.median([v["lock"] for v in ses])) if ses else float("nan")
s_rest = float(np.median([v["rest"] for v in ses])) if ses else float("nan")
s_ses = (s_lock + s_rest) / 2
print(f"\nsession scale from {len(ses)} clips: S_lock {s_lock:.1f}, S_rest {s_rest:.1f}, "
      f"used {s_ses:.1f} px/m")


def own_scale(c: str) -> tuple[float, float, float]:
    v = sc.get(c)
    if v:
        return (v["lock"] + v["rest"]) / 2, v["lock"], v["rest"]
    return s_ses, s_lock, s_rest


is_direct = lambda r: r["cat"] == "hips" and r.get("floor_sole_y") and r.get("head_xy")  # noqa: E731
eye_off = [(r["eye_y"] - r["head_xy"][1]) for c, d in data.items()
           for r in d["rows"] if is_direct(r)]
eye_off_px = float(np.median(eye_off)) if eye_off else None
print(f"head top above near eye (direct frames, px): {eye_off_px}")

print("\n| clip | scale used px/m | direct cm (IQR, n) | at S_lock / S_rest | eye-based lockout cm (IQR, n) |")
print("|---|---|---|---|---|")
direct_c, eye_c = {}, {}
for c, d in data.items():
    rows = d["rows"]
    s_use, sl, sr = own_scale(c)
    px = [r["floor_sole_y"] - r["head_xy"][1] for r in rows if is_direct(r)]
    ey = [r["floor_sole_y"] - r["eye_y"] + eye_off_px for r in rows
          if r["cat"] == "overhead" and r.get("floor_sole_y") and eye_off_px is not None
          and sc.get(c)]
    cell = lambda v, s: (f"{np.median(v) / s * 100:.1f} ({np.percentile(v, 25) / s * 100:.1f}–"  # noqa: E731
                         f"{np.percentile(v, 75) / s * 100:.1f}), n={len(v)}") if v else "–"
    if px:
        direct_c[c] = float(np.median(px)) / s_use * 100
    if ey:
        eye_c[c] = float(np.median(ey)) / s_use * 100
    both = (f"{np.median(px) / sl * 100:.1f} / {np.median(px) / sr * 100:.1f}" if px else "–")
    print(f"| {c} | {s_use:.1f} | {cell(px, s_use)} | {both} | {cell(ey, s_use)} |")

print()
for name, v in (("direct", direct_c), ("eye-based", eye_c)):
    if v:
        a = np.array(list(v.values()))
        m = float(np.median(a))
        print(f"{name}: median of {len(a)} clips {m:.1f} cm with shoes (~{m - shoe:.1f} barefoot, "
              f"shoe {shoe} cm), range {a.min():.1f}–{a.max():.1f}")
