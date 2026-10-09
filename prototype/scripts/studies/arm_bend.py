"""D2 early arm bend: 2D shoulder-to-hub distance and elbow angle per rep.

usage: uv run python scripts/studies/arm_bend.py [--no-grabs] label=out/<clip> [label=out/<clip> …]
       e.g. straight30=out/20261007_9_… bent30=out/20261007_10_… straight25=out/20261007_3_…
reads  out/<clip>/raw_pose.npz, plate.npz; the clip from ../vids/spike or ../vids
writes out/<clip>/arm_bend.json (per rep), out/<clip>/arm_bend_sheet.jpg (frame
       grabs at setup / bar at knee / transition / bar at hip, near shoulder-
       elbow-hub drawn), out/d2_arm_bend/{reps.csv,curves.png,summary.md}

Reps are v2 (snatch.phases.find_reps_v2), computed exactly as
scripts/compare_phases.py does; nothing in the clip's other outputs changes.
Near side = lifter's right (r_shoulder, r_elbow, r_wrist). Signals and the
event definitions are in snatch.armbend.
"""

import csv
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import cv2
import matplotlib
import numpy as np

from snatch.angles import COCO, mid_y, sagittal_angles
from snatch.armbend import arm_signals, at, phase_time, pull_events, separation, window_min
from snatch.phases import find_reps_v2
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frame_times, frames, mean_rate, probe

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SIDE = "r"
EVENTS = ("setup", "knee", "transition", "hip")
SIGNALS = ("d_cm", "rel", "straight", "elbow_hub_deg", "elbow_deg")
SUMMARY = Path("out/d2_arm_bend")

args = sys.argv[1:]
grabs = "--no-grabs" not in args
targets = [a.split("=", 1) for a in args if "=" in a]


def video_for(clip: str) -> str:
    for d in ("../vids/spike", "../vids"):
        p = Path(d) / f"{clip}.MOV"
        if p.exists():
            return str(p)
    raise FileNotFoundError(clip)


def analyse(out: Path) -> list[dict]:
    raw, plate = np.load(out / "raw_pose.npz"), np.load(out / "plate.npz")
    kps, scores = raw["keypoints"], raw["scores"]
    t = frame_times(raw)
    fps = mean_rate(t)
    kps_s = smooth_keypoints(kps, fps)
    ang = sagittal_angles(kps_s, SIDE)
    hip_y, knee_y = mid_y(kps_s, "hip"), mid_y(kps_s, "knee")
    # reps as compare_phases.py (hub_y smoothed without masking, as there)
    reps = find_reps_v2(hub_y=smooth(plate["hub_y"], fps), nose_y=mid_y(kps_s, "nose"),
                        hip_y=hip_y, knee=ang["knee"], fps=fps, knee_y=knee_y, t=t)
    anchor = "nose"
    if not reps:
        # no bar overhead (20261007_10: every rep peaks at face height), so the
        # rep is anchored on the hub passing the shoulders instead; only the pull
        # (setup to bar at hip) is used here, which this anchor still brackets
        reps = find_reps_v2(hub_y=smooth(plate["hub_y"], fps),
                            nose_y=mid_y(kps_s, "shoulder"), hip_y=hip_y,
                            knee=ang["knee"], fps=fps, knee_y=knee_y, t=t)
        anchor = "shoulder"
    found = plate["found"]
    hub = np.stack([smooth(np.where(found, plate["hub_x"], np.nan), fps),
                    smooth(np.where(found, plate["hub_y"], np.nan), fps)], 1)
    j = {p: COCO[f"{SIDE}_{p}"] for p in ("shoulder", "elbow", "wrist", "hip", "knee")}
    near_knee_y, near_hip_y = kps_s[:, j["knee"], 1], kps_s[:, j["hip"], 1]
    rows = []
    for k, rep in enumerate(reps):
        ev = pull_events(hub[:, 1], near_knee_y, near_hip_y, rep)
        end = ev.hip if ev.hip is not None else rep.overhead_start
        ppm = float(np.nanmedian(np.where(found, plate["px_per_m"], np.nan)[rep.setup:end + 1]))
        sig = arm_signals(kps_s[:, j["shoulder"]], kps_s[:, j["elbow"]],
                          kps_s[:, j["wrist"]], hub, ppm)
        sig["rel"] = sig["d_cm"] / sig["d_cm"][rep.setup]
        row: dict = {"clip": out.name, "rep": k + 1, "anchor": anchor, "fps": fps, "px_per_m": ppm,
                     **{f"f_{e}": getattr(ev, e) for e in EVENTS}}
        for s in SIGNALS:
            for e in EVENTS:
                row[f"{s}@{e}"] = at(sig[s], getattr(ev, e))
            v, i = window_min(sig[s], rep.setup, ev.hip)
            row[f"{s}_min"] = v
            row[f"{s}_min_pt"] = (float(phase_time(np.array([i]), ev)[0])
                                  if i is not None else math.nan)
        w = slice(rep.setup, end + 1)
        row["hub_found"] = float(found[w].mean())
        row["score_sh_el"] = float(scores[w][:, [j["shoulder"], j["elbow"]]].mean())
        row["score_wrist"] = float(scores[w, j["wrist"]].mean())
        a, b = rep.setup - round(0.3 * fps), (ev.hip or end) + round(0.3 * fps)
        idx = np.arange(a, b)
        row["_curve"] = {"pt": phase_time(idx, ev).tolist(),
                         **{s: sig[s][a:b].tolist() for s in SIGNALS}}
        row["_points"] = {e: None if getattr(ev, e) is None else
                          {p: kps_s[getattr(ev, e), j[p]].tolist() for p in ("shoulder", "elbow", "wrist")}
                          | {"hub": hub[getattr(ev, e)].tolist()} for e in EVENTS}
        rows.append(row)
    (out / "arm_bend.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if not k.startswith("_curve")} for r in rows],
        indent=1, default=lambda x: None))
    return rows


def sheet(out: Path, rows: list[dict]) -> None:
    want = {r[f"f_{e}"]: (r["rep"] - 1, c, r["_points"][e])
            for r in rows for c, e in enumerate(EVENTS) if r[f"f_{e}"] is not None}
    clip = video_for(out.name)
    info = probe(clip)
    tiles: dict = {}
    for i, img in enumerate(frames(clip, info)):
        if i > max(want):
            break
        if i not in want:
            continue
        k, c, p = want[i]
        im = img.copy()
        pts = {n: tuple(int(v) for v in p[n]) for n in ("shoulder", "elbow", "wrist", "hub")}
        cv2.line(im, pts["shoulder"], pts["hub"], (0, 255, 255), 3)
        cv2.line(im, pts["shoulder"], pts["elbow"], (0, 0, 255), 4)
        cv2.line(im, pts["elbow"], pts["hub"], (0, 0, 255), 4)
        for n, col in (("shoulder", (255, 0, 0)), ("elbow", (0, 0, 255)),
                       ("wrist", (255, 0, 255)), ("hub", (0, 255, 0))):
            cv2.circle(im, pts[n], 9, col, -1)
        cx, cy = pts["shoulder"][0], (pts["shoulder"][1] + pts["hub"][1]) // 2
        h = 700
        x0, y0 = max(0, cx - h // 2), max(0, cy - h // 2)
        crop = cv2.resize(im[y0:y0 + h, x0:x0 + h], (420, 420))
        r = rows[k]
        e = EVENTS[c]
        lab = f"r{k + 1} {e} d={r[f'd_cm@{e}']:.1f} el={r[f'elbow_hub_deg@{e}']:.0f}"
        cv2.putText(crop, lab, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(crop, lab, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        tiles[(k, c)] = crop
    blank = np.zeros((420, 420, 3), np.uint8)
    grid = np.vstack([np.hstack([tiles.get((k, c), blank) for c in range(len(EVENTS))])
                      for k in range(len(rows))])
    cv2.imwrite(str(out / "arm_bend_sheet.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 85])


def fmt(x: float, nd: int = 1) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


all_rows = []
for label, d in targets:
    out = Path(d)
    rows = analyse(out)
    for r in rows:
        r["group"] = label
    if grabs and rows:
        sheet(out, rows)
    all_rows += rows
    print(out.name, len(rows), "reps")

SUMMARY.mkdir(parents=True, exist_ok=True)
cols = [k for k in all_rows[0] if not k.startswith("_")]
with open(SUMMARY / "reps.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["group"] + [c for c in cols if c != "group"], extrasaction="ignore")
    w.writeheader()
    w.writerows(all_rows)

groups = list(dict.fromkeys(r["group"] for r in all_rows))
colours = dict(zip(groups, plt.get_cmap("tab10").colors))
fig, axes = plt.subplots(len(SIGNALS), 1, figsize=(11, 3.2 * len(SIGNALS)), sharex=True)
for r in all_rows:
    c = r["_curve"]
    for ax, s in zip(axes, SIGNALS):
        ax.plot(c["pt"], c[s], color=colours[r["group"]], lw=1.2,
                ls="--" if r["group"].startswith("bent") else "-")
for ax, s in zip(axes, SIGNALS):
    ax.set_ylabel(s)
    for x in (0, 1, 2):
        ax.axvline(x, color="grey", lw=0.6)
    ax.grid(alpha=0.3)
axes[-1].set_xlabel("pull time: 0 setup (liftoff), 1 bar at knee, 2 bar at hip")
axes[-1].set_xlim(-0.6, 2.6)
axes[0].legend(handles=[plt.Line2D([], [], color=colours[g], label=g) for g in groups])
fig.tight_layout()
fig.savefig(SUMMARY / "curves.png", dpi=110)

# per-rep table and separation of every group against the pooled straight reps
KEYS = ["d_cm@setup", "d_cm@knee", "d_cm@transition", "d_cm@hip", "d_cm_min",
        "rel@knee", "rel@transition", "rel@hip", "rel_min", "rel_min_pt",
        "straight_min", "elbow_hub_deg@knee", "elbow_hub_deg@transition",
        "elbow_hub_deg@hip", "elbow_hub_deg_min", "elbow_deg@knee", "elbow_deg@hip"]
lines = ["# D2 arm bend per rep", "",
         "| group | clip | rep | " + " | ".join(KEYS) + " | hub found | score sh/el | score wrist |",
         "|---|---|---|" + "---|" * (len(KEYS) + 3)]
for r in all_rows:
    lines.append(f"| {r['group']} | {r['clip']} | {r['rep']} | "
                 + " | ".join(fmt(r[k], 3 if k.startswith(("rel", "straight")) else 1) for k in KEYS)
                 + f" | {r['hub_found']:.2f} | {r['score_sh_el']:.2f} | {r['score_wrist']:.2f} |")
straight = [g for g in groups if g.startswith("straight")]
lines += ["", "## Separation vs straight groups",
          "", "diff = mean grp − mean ref; d = Cohen's d (pooled SD); gap = distance between "
          "the two ranges in the direction of diff (> 0: no overlap, < 0: overlap)", ""]
for ref_name, ref in [("straight30", ["straight30"]), ("all straight", straight)]:
    a_rows = [r for r in all_rows if r["group"] in ref]
    if not a_rows:
        continue
    lines += [f"### reference: {ref_name} (n = {len(a_rows)})", "",
              "| group | key | n | mean ref | sd ref | mean grp | sd grp | diff | d | gap | range ref | range grp |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in groups:
        if g in ref:
            continue
        b_rows = [r for r in all_rows if r["group"] == g]
        for k in KEYS:
            if k.endswith("_pt"):
                continue
            a, b = [r[k] for r in a_rows], [r[k] for r in b_rows]
            if len(b) < 2 or any(map(math.isnan, a + b)):
                continue
            s = separation(a, b)
            lines.append(f"| {g} | {k} | {s['n_b']} | {s['mean_a']:.3f} | {s['sd_a']:.3f} | "
                         f"{s['mean_b']:.3f} | {s['sd_b']:.3f} | {s['diff']:+.3f} | "
                         f"{s['cohen_d']:+.1f} | {s['gap']:+.3f} | {min(a):.3f}–{max(a):.3f} | {min(b):.3f}–{max(b):.3f} |")
    lines.append("")
(SUMMARY / "summary.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
