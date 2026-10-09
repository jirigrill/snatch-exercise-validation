"""Frame grabs for the D1 visibility check (docs/results/33-d1-views.md).

usage: uv run python scripts/d1_sheets.py ../vids/spike/<clip>.MOV out/<clip> [--near]
reads  out/<clip>/raw_pose.npz, plate.npz (plate_near.npz with --near, where
       present), d1_views.json (scripts/d1_views.py, run with the same plate)
writes out/<clip>/d1_sheet.jpg  one row per rep: setup, hub at knee,
           transition, mid 2nd pull, peak extension; lifter crop with the
           near side (yellow, dot red if score < 0.5), far side (grey) and the
           plate outline (green)
       out/<clip>/d1_zoom.jpg   one row per rep, full resolution around the
           near hip and knee at the transition and the wrist mid-pull: the raw
           frame, then the same crop with the keypoints drawn
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from snatch.angles import COCO
from snatch.video import frames, probe

args = [a for a in sys.argv[1:] if a != "--near"]
clip, out = args[0], Path(args[1])
pfile = out / ("plate_near.npz" if "--near" in sys.argv and (out / "plate_near.npz").exists()
               else "plate.npz")
raw, plate = np.load(out / "raw_pose.npz"), np.load(pfile)
res = json.loads((out / "d1_views.json").read_text())
kps, scores = raw["keypoints"], raw["scores"]
BONES = [("shoulder", "elbow"), ("elbow", "wrist"), ("shoulder", "hip"),
         ("hip", "knee"), ("knee", "ankle")]
TILE_H, ZOOM = 560, 320  # zoom: half side of the full-resolution crop (px)

slots = []  # (rep index, column, frame, label)
for k, r in enumerate(res["reps"]):
    tr = r["transition"] if r["transition"] is not None else r["hub_at_knee"]
    mid = (tr + r["peak_ext"]) // 2 if tr is not None else None
    for c, (f, lab) in enumerate([(r["setup"], "setup"), (r["hub_at_knee"], "hub at knee"),
                                  (tr, "transition"), (mid, "mid 2nd pull"),
                                  (r["peak_ext"], "peak ext")]):
        if f is not None:
            slots.append((k, c, int(f), lab))
want: dict[int, list] = {}
for s in slots:
    want.setdefault(s[2], []).append(s)


def draw(img, i, thick=3):
    img = img.copy()
    if plate["found"][i]:
        cv2.ellipse(img, ((float(plate["hub_x"][i]), float(plate["hub_y"][i])),
                          (2 * float(plate["a"][i]), 2 * float(plate["b"][i])),
                          float(plate["angle"][i])), (0, 220, 0), thick)
        cv2.circle(img, (int(plate["hub_x"][i]), int(plate["hub_y"][i])), 5, (0, 220, 0), -1)
    for side, col, th in (("l", (160, 160, 160), thick - 1), ("r", (0, 230, 255), thick)):
        for a, b in BONES:
            pa, pb = kps[i, COCO[f"{side}_{a}"]], kps[i, COCO[f"{side}_{b}"]]
            cv2.line(img, tuple(int(v) for v in pa), tuple(int(v) for v in pb), col, th)
        for j in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle"):
            ki = COCO[f"{side}_{j}"]
            dot = (0, 0, 255) if scores[i, ki] < 0.5 else col
            cv2.circle(img, tuple(int(v) for v in kps[i, ki]), thick + 3, dot, -1)
    return img


def label(img, lines, scale=0.7):
    for n, s in enumerate(lines):
        for th, col in ((5, (0, 0, 0)), (2, (255, 255, 255))):
            cv2.putText(img, s, (8, 28 + 28 * n), cv2.FONT_HERSHEY_SIMPLEX, scale, col, th)
    return img


def crop(img, cx, cy, half):
    h, w = img.shape[:2]
    x0, y0 = int(np.clip(cx - half, 0, w - 2 * half)), int(np.clip(cy - half, 0, h - 2 * half))
    return img[y0:y0 + 2 * half, x0:x0 + 2 * half]


def sc(i, j):
    return f"{scores[i, COCO['r_' + j]]:.2f}"


# lifter crop: the near keypoints' extent over all grabbed frames, padded
pts = np.concatenate([kps[f] for f in want])
lo, hi = np.nanmin(pts, 0) - 120, np.nanmax(pts, 0) + 120
info = probe(clip)
x0, y0 = int(max(lo[0], 0)), int(max(lo[1], 0))
x1, y1 = int(min(hi[0], info.width)), int(min(hi[1], info.height))
tiles, zooms = {}, {}
last = max(want)
for i, img in enumerate(frames(clip, info)):
    if i > last:
        break
    for k, c, f, lab in want.get(i, []):
        d = draw(img, i)
        t = d[y0:y1, x0:x1]
        t = cv2.resize(t, (int(TILE_H * t.shape[1] / t.shape[0]), TILE_H))
        tiles[k, c] = label(t, [f"rep {k + 1} {lab} f{i}",
                                f"hip {sc(i, 'hip')} knee {sc(i, 'knee')} wrist {sc(i, 'wrist')}"], 0.55)
        if lab == "transition":
            hk = (kps[i, COCO["r_hip"]] + kps[i, COCO["r_knee"]]) / 2
            zooms[k, 0] = label(crop(img, *hk, ZOOM).copy(), [f"rep {k + 1} transition f{i} raw"])
            zooms[k, 1] = label(crop(d, *hk, ZOOM).copy(),
                                [f"hip {sc(i, 'hip')} knee {sc(i, 'knee')}"])
        if lab == "mid 2nd pull":
            wr = kps[i, COCO["r_wrist"]]
            zooms[k, 2] = label(crop(img, *wr, ZOOM).copy(), [f"mid 2nd pull f{i} raw"])
            zooms[k, 3] = label(crop(d, *wr, ZOOM).copy(),
                                [f"wrist {sc(i, 'wrist')} elbow {sc(i, 'elbow')}"])


def grid(cells, ncol, blank_shape):
    rows = []
    for k in range(len(res["reps"])):
        row = [cells.get((k, c), np.zeros(blank_shape, np.uint8)) for c in range(ncol)]
        hgt = max(x.shape[0] for x in row)
        row = [cv2.copyMakeBorder(x, 0, hgt - x.shape[0], 0, 0, cv2.BORDER_CONSTANT) for x in row]
        rows.append(np.hstack(row))
    wdt = max(r.shape[1] for r in rows)
    return np.vstack([cv2.copyMakeBorder(r, 0, 0, 0, wdt - r.shape[1], cv2.BORDER_CONSTANT)
                      for r in rows])


some = next(iter(tiles.values()))
cv2.imwrite(str(out / "d1_sheet.jpg"), grid(tiles, 5, some.shape), [cv2.IMWRITE_JPEG_QUALITY, 85])
if zooms:
    cv2.imwrite(str(out / "d1_zoom.jpg"), grid(zooms, 4, (2 * ZOOM, 2 * ZOOM, 3)),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
print("wrote", out / "d1_sheet.jpg", out / "d1_zoom.jpg")
