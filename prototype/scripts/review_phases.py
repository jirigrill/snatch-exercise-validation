"""Review material for #13: phase marks (definition v2) on side-on reps.

usage: uv run python scripts/review_phases.py
reads  out/<clip>/raw_pose.npz, plate.npz and ../vids/IMG_<clip>.MOV
writes out/review13/<clip>_rep<k>.jpg   one sheet per rep: columns = setup,
           transition, catch, lockout; rows = event -0.1 s, event, +0.1 s
       out/review13/checklist.md        verdict + visibility ticks to fill in
       out/review13/model_visibility.json  model scores per event frame (for
           #15; kept out of the checklist so the ticks are not biased)
"""

import json
from pathlib import Path

import cv2
import numpy as np

from snatch.angles import COCO, mid_y, sagittal_angles
from snatch.phases import find_reps_v2
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frames, probe

CLIPS = ["4581", "4583", "4584", "4587"]  # side-on, v2 phases (4579: no reps)
SIDE = "r"
PHASES = ("setup", "transition", "catch", "lockout")
NEAR = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")
SKELETON = [("shoulder", "elbow"), ("elbow", "wrist"), ("shoulder", "hip"),
            ("hip", "knee"), ("knee", "ankle")]
OFFSETS_S = (-0.1, 0.0, 0.1)
TILE_H = 560

out_dir = Path("out/review13")
out_dir.mkdir(exist_ok=True)
checklist = ["# Phase review (#13)", "",
             "Phase frames are marked by definition v2 (hub height). For each "
             "event look at the middle row of the sheet (rows above/below are "
             "-0.1 s / +0.1 s for timing).", "",
             "Verdict per phase: **accept**, or **correct** with the rule/frame "
             "you would use. Visibility: tick a joint only if you can really see "
             "it on the middle-row frame (behind plate / out of view = not "
             "visible). Near side = lifter's right.", ""]
model_vis: dict[str, dict[str, float]] = {}

for clip in CLIPS:
    raw, plate = np.load(f"out/{clip}/raw_pose.npz"), np.load(f"out/{clip}/plate.npz")
    kps, scores, fps = raw["keypoints"], raw["scores"], float(raw["fps"])
    ks = smooth_keypoints(kps, fps)
    reps = find_reps_v2(
        hub_y=smooth(plate["hub_y"], fps), nose_y=mid_y(ks, "nose"),
        hip_y=mid_y(ks, "hip"), knee=sagittal_angles(ks, SIDE)["knee"], fps=fps,
        knee_y=mid_y(ks, "knee"))
    want = {}  # frame -> (rep, phase, offset)
    for k, r in enumerate(reps):
        for ph in PHASES:
            f = getattr(r, ph)
            if f is None:
                continue
            for o in OFFSETS_S:
                want[min(max(f + round(o * fps), 0), len(kps) - 1)] = (k, ph, o)
    info = probe(f"../vids/IMG_{clip}.MOV")
    grabs: dict[tuple[int, str, float], np.ndarray] = {}
    last = max(want, default=-1)
    for i, img in enumerate(frames(f"../vids/IMG_{clip}.MOV", info)):
        if i > last:
            break
        if i not in want:
            continue
        k, ph, o = want[i]
        img = img.copy()
        pt = lambda j: tuple(int(v) for v in kps[i, COCO[f"{SIDE}_{j}"]])
        for a, b in SKELETON:
            cv2.line(img, pt(a), pt(b), (255, 200, 0), 4)
        for j in NEAR:
            cv2.circle(img, pt(j), 9, (0, 200, 255), -1)
            cv2.putText(img, j[:2], (pt(j)[0] + 10, pt(j)[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        if plate["found"][i]:
            cx, cy, a, b, ang = (plate[x][i] for x in ("hub_x", "hub_y", "a", "b", "angle"))
            cv2.ellipse(img, ((cx, cy), (2 * a, 2 * b), ang), (0, 255, 0), 3)
            cv2.circle(img, (int(cx), int(cy)), 6, (0, 0, 255), -1)
        label = f"{ph} f{i} ({o:+.1f}s)" if o else f"{ph.upper()} f{i}"
        grabs[(k, ph, o)] = (img, label)  # type: ignore[assignment]
        if o == 0:
            model_vis[f"{clip}_rep{k + 1}_{ph}_f{i}"] = {
                j: round(float(scores[i, COCO[f"{SIDE}_{j}"]]), 3) for j in NEAR}
    for k, r in enumerate(reps):
        # one crop for the whole rep, so tiles are comparable
        fr = [f for ph in PHASES if (f := getattr(r, ph)) is not None]
        pts = kps[min(fr):max(fr) + 1, :, :].reshape(-1, 2)
        hubs = np.c_[plate["hub_x"], plate["hub_y"]][min(fr):max(fr) + 1]
        allp = np.vstack([pts, hubs[~np.isnan(hubs).any(1)]])
        x0, y0 = np.percentile(allp, 1, axis=0) - 250
        x1, y1 = np.percentile(allp, 99, axis=0) + 250
        x0, y0 = max(int(x0), 0), max(int(y0), 0)
        rows = []
        for o in OFFSETS_S:
            cells = []
            for ph in PHASES:
                g = grabs.get((k, ph, o))
                if g is None:
                    cells.append(np.zeros((TILE_H, int(TILE_H * (x1 - x0) / (y1 - y0)), 3), np.uint8))
                    continue
                img, label = g
                c = img[y0:int(y1), x0:int(x1)]
                c = cv2.resize(c, (int(TILE_H * c.shape[1] / c.shape[0]), TILE_H))
                for th, col in ((6, (0, 0, 0)), (2, (255, 255, 255))):
                    cv2.putText(c, label, (8, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, th)
                cells.append(c)
            rows.append(np.hstack(cells))
        name = f"{clip}_rep{k + 1}"
        cv2.imwrite(str(out_dir / f"{name}.jpg"), np.vstack(rows),
                    [cv2.IMWRITE_JPEG_QUALITY, 80])
        checklist += [f"## {name}  (`{name}.jpg`)", "",
                      "| phase | frame | t (s) | verdict | corrected rule / frame | "
                      + " | ".join(j[:3] for j in NEAR) + " |",
                      "|---|---|---|---|---|" + "---|" * len(NEAR)]
        for ph in PHASES:
            f = getattr(r, ph)
            if f is None:
                continue
            checklist.append(f"| {ph} | {f} | {f / fps:.3f} | accept / correct | | "
                             + " | ".join("[ ]" for _ in NEAR) + " |")
        checklist.append("")
    print(clip, "reps", len(reps), flush=True)

(out_dir / "checklist.md").write_text("\n".join(checklist) + "\n")
(out_dir / "model_visibility.json").write_text(json.dumps(model_vis, indent=1) + "\n")
print("wrote", sorted(p.name for p in out_dir.iterdir()))
