"""Propose one row per rep for every clip, from the plate hub (snatch.reps).

usage: uv run python scripts/find_reps.py ../vids
reads  out/<clip>/plate.npz; where its track failed the check, pose instead:
       out/<clip>/raw_pose_sparse.npz (extract_pose.py --every N) or
       raw_pose.npz taken at every 8th frame; out/<clip>/phases.json for the bar-only clip
writes out/reps_proposed.csv  proposed rows, not hand-checked (a checked rep
           list is deferred to the gate 1 set, #20)
       out/reps_check/<clip>.png  hub height with the proposed lifts shaded,
           to check the boundaries against

Outcome, fail cause and variant are copied from the file name (per clip, not
per rep) and marked unchecked; the person checking sets them per rep.
"""

import csv
import json
import re
import sys
from pathlib import Path

import matplotlib
import numpy as np

from snatch.angles import COCO
from snatch.reps import (Lift, find_lifts, find_pose_holds, find_pose_lifts,
                         height_above_floor, pose_range)
from snatch.video import mean_rate, probe, timestamps

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIELDS = ["clip", "rep", "start_frame", "end_frame", "pose_start", "pose_end",
          "fps", "peak_m", "source", "variant", "outcome", "fail_cause",
          "checked", "notes"]
VARIANT = {"powersnatch": "power", "squatsnatch": "squat", "standup": "hold"}
# pose-based lifts start ~0.4 s late and end up to ~0.9 s early vs the hub
# (checked on the 7 snatch clips of 2026-10-01): pad more
PAD_S = {"plate": (1.0, 1.0), "pose": (1.5, 2.0), "phases": (1.0, 1.0)}


def sparse_pose(clip_dir: Path) -> np.ndarray | None:
    """Keypoints on a sparse set of frames (NaN elsewhere): the sparse pass
    (extract_pose.py --every N) as it is, or a full run taken at every 8th
    frame so both sources are judged alike."""
    if (clip_dir / "raw_pose_sparse.npz").exists():
        return np.load(clip_dir / "raw_pose_sparse.npz")["keypoints"].astype(float)
    if (clip_dir / "raw_pose.npz").exists():
        k = np.load(clip_dir / "raw_pose.npz")["keypoints"].astype(float)
        keep = np.zeros(len(k), bool)
        keep[::8] = True
        k[~keep] = np.nan
        return k
    return None


def ymean(k: np.ndarray, *names: str) -> np.ndarray:
    return np.nanmean(np.stack([k[:, COCO[n], 1] for n in names]), 0)


def from_name(stem: str) -> dict[str, str]:
    """Variant, outcome, fail cause and rep count as written in the file name."""
    reps = re.search(r"_(\d+)rep_", stem)
    lifts = [v for k, v in VARIANT.items() if f"_{k}_" in stem]
    m = re.search(r"_(success|fail)(?:_(.+))?_-?\d+deg$", stem)
    return {"variant": "+".join(lifts),
            "outcome": {"success": "made", "fail": "missed"}[m.group(1)] if m else "",
            "fail_cause": (m.group(2) or "") if m else "",
            "n_reps": reps.group(1) if reps else ""}


vids = Path(sys.argv[1])
out = Path("out")
check_dir = out / "reps_check"
check_dir.mkdir(exist_ok=True)
rows = []
for mov in sorted(vids.glob("*.MOV"), key=lambda p: [int(x) if x.isdigit() else x
                                                     for x in re.split(r"(\d+)", p.stem)]):
    clip = mov.stem
    info = probe(str(mov))
    t = timestamps(str(mov), info.fps)  # 2026-10-05 drops frames: ~200 fps, tagged 240
    fps = mean_rate(t)
    name = from_name(clip)
    notes = []
    plate_path = out / clip / "plate.npz"
    p = np.load(plate_path) if plate_path.exists() else None
    k = sparse_pose(out / clip)
    h = None
    if p is not None and str(p["status"]) == "ok":
        h = height_above_floor(p["hub_y"], p["found"], p["px_per_m"], t)
        lifts, source, kind = find_lifts(h, t), "plate hub", "plate"
    elif k is not None and (p is not None or "_bar_" not in clip):
        with np.errstate(all="ignore"):
            wrist, knee, hip = (ymean(k, "l_wrist", "r_wrist"), ymean(k, "l_knee", "r_knee"),
                                ymean(k, "l_hip", "r_hip"))
        lifts = find_pose_lifts(wrist, k[:, COCO["nose"], 1], knee, hip, t)
        source, kind = "pose, wrists above chest (sparse frames)", "pose"
        if not lifts:
            lifts = find_pose_holds(wrist, knee, hip, t)
            source = "pose, wrists above mid-thigh (no overhead phase; sparse frames)"
        if p is not None:
            notes.append(f"plate {str(p['status'])[:40]}")
    elif (out / clip / "phases.json").exists():  # bar only: no plate to track
        reps = json.loads((out / clip / "phases.json").read_text())["reps"]
        lifts = [Lift(r["setup"], r["overhead_end"], float("nan")) for r in reps]
        source, kind = "phases.json v1 setup..overhead_end (no plate)", "phases"
    else:
        print(clip, "no plate.npz or pose: run track_plate.py or extract_pose.py --every 8",
              flush=True)
        continue
    if name["n_reps"] and len(lifts) != int(name["n_reps"]):
        notes.append(f"found {len(lifts)} lifts, name says {name['n_reps']}")
    for k, lf in enumerate(lifts, 1):
        ps, pe = pose_range(lf, t, info.n_frames, *PAD_S[kind])
        rows.append({"clip": clip, "rep": k, "start_frame": lf.start,
                     "end_frame": lf.end, "pose_start": ps, "pose_end": pe,
                     "fps": f"{fps:.1f}",
                     "peak_m": "" if np.isnan(lf.peak_m) else f"{lf.peak_m:.2f}",
                     "source": source, "variant": name["variant"],
                     "outcome": name["outcome"], "fail_cause": name["fail_cause"],
                     "checked": "no", "notes": "; ".join(notes)})
    if not lifts:
        rows.append({"clip": clip, "rep": "", "source": source, "checked": "no",
                     "notes": "; ".join(notes + ["no lift found"])})
    if h is not None:
        fig, ax = plt.subplots(figsize=(12, 3))
        ax.plot(t, h, lw=0.8)
        for k, lf in enumerate(lifts, 1):
            ps, pe = pose_range(lf, t, info.n_frames, *PAD_S[kind])
            ax.axvspan(t[ps], t[min(pe, len(t) - 1)], color="0.9")
            ax.axvspan(t[lf.start], t[min(lf.end, len(t) - 1)], color="tab:green", alpha=0.3)
            ax.text(t[lf.start], 0.05, f"rep {k}\nf{lf.start}-{lf.end}", fontsize=8)
        ax.set(xlabel="s", ylabel="hub above floor (m)",
               title=f"{clip} — {source}; green = lift, grey = pose range")
        fig.tight_layout()
        fig.savefig(check_dir / f"{clip}.png", dpi=90)
        plt.close(fig)
    print(clip, [(lf.start, lf.end) for lf in lifts], "; ".join(notes), flush=True)

with open(out / "reps_proposed.csv", "w", newline="") as f:
    w = csv.DictWriter(f, FIELDS)
    w.writeheader()
    w.writerows(rows)
print("wrote", out / "reps_proposed.csv", len(rows), "rows")
