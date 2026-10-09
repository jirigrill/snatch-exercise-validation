"""Body height (with shoes) from standing frames of a side-on clip (#22, docs/results/35).

usage: uv run python scripts/studies/body_height.py ../vids/spike/<clip>.MOV out/<clip> [--side r|l]
reads  out/<clip>/raw_pose.npz, plate.npz, person.npz
writes out/<clip>/height.json   per-frame rows and the clip summary
       out/<clip>/height_sheet.jpg   chosen frames: head top (red), sole (green),
                                     midline floor (cyan), far plate (magenta)

Frames: upright (near knee >= 163, hip >= 165 deg, trunk within 12 deg of
vertical), still (nose < 0.3, ankles < 0.15 m/s), feet found; split into "hips"
(wrists below the shoulders: bar at the hips, arms down) and "overhead"
(wrists above the nose: lockout). One frame every 0.1 s.
Head top: highest foreground pixel above the eyes against a background made
from setup frames (snatch.height.head_top), not the YOLOX box (that box ends
at the hands or plate overhead; its top is reported for the hips frames).
Floor: midline floor from the near shoe's lowest green pixel
(floor_from_sole) and from the resting plate (floor_from_plate); their mean.
Scale at the midline: k * near-plate px_per_m; k = --k if given (e.g. another
session's value), else the far plate in the overhead frames (median), else the
protocol (4 m, s = 0.70 m).
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from snatch import height as H
from snatch import plate as P
from snatch.angles import COCO, sagittal_angles
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frames, probe

args = sys.argv[1:]
side = "r"
if "--side" in args:
    i = args.index("--side")
    side = args[i + 1]
    del args[i:i + 2]
scale_from: list[Path] = []
if "--scale-from" in args:
    i = args.index("--scale-from")
    scale_from = [Path(p) for p in args[i + 1].split(",")]
    del args[i:i + 2]
k_override = None  # --k 0.81: depth ratio from another session (no far plate, unknown distance)
if "--k" in args:
    i = args.index("--k")
    k_override = float(args[i + 1])
    del args[i:i + 2]
clip, out = args[0], Path(args[1])
far_side = "l" if side == "r" else "r"
Z_C, S_M = 4.0, 0.70

raw, per = np.load(out / "raw_pose.npz"), np.load(out / "person.npz")
pl = np.load(out / "plate.npz") if not scale_from else None
session: dict = {}
if scale_from:  # bar only, no plate: the session's scale and floor (same tripod, same marks)
    sums = [json.loads((d / "height.json").read_text())["summary"] for d in scale_from]
    session = {key: float(np.median([sm[key] for sm in sums]))
               for key in ("px_per_m_mid", "floor_plate_y", "camera_height_m")}
fps = float(raw["fps"])
n = len(raw["keypoints"])
kp = smooth_keypoints(raw["keypoints"], fps)
ang = sagittal_angles(kp, side)
ppm_all = float(np.nanmedian(pl["px_per_m"])) if pl is not None else session["px_per_m_mid"] / 0.82
c = lambda name: kp[:, COCO[name]]  # noqa: E731


def speed(x: np.ndarray) -> np.ndarray:
    v = np.gradient(x, axis=0) * fps
    return np.hypot(v[:, 0], v[:, 1]) / ppm_all


upright = (ang["knee"] >= 163) & (ang["hip"] >= 165) & (np.abs(ang["trunk"]) <= 12)
still = ((speed(c("nose")) < 0.3) & (speed(c(f"{side}_ankle")) < 0.15)
         & (speed(c(f"{far_side}_ankle")) < 0.15))
wrist_y = kp[:, [COCO["l_wrist"], COCO["r_wrist"]], 1].mean(1)
shoulder_y = kp[:, [COCO["l_shoulder"], COCO["r_shoulder"]], 1].mean(1)
cat = np.where(wrist_y > shoulder_y, "hips", np.where(wrist_y < c("nose")[:, 1], "overhead", ""))
ok = upright & still & (cat != "")

# windows of >= 0.15 s, one frame per 0.1 s
pick: list[int] = []
i = 0
while i < n:
    if not ok[i]:
        i += 1
        continue
    j = i
    while j < n and ok[j] and cat[j] == cat[i]:
        j += 1
    if j - i >= 0.15 * fps:
        pick += list(range(i + int(0.05 * fps), j, int(0.1 * fps)))
    i = j

# plate at rest (on the floor): lowest hub, hub still
hub_rest_y = ppm_rest = float("nan")
if pl is not None:
    hub_y = smooth(pl["hub_y"], fps)
    hub_v = np.abs(np.gradient(hub_y)) * fps / ppm_all
    rest = pl["found"] & (hub_v < 0.02) & (hub_y > np.nanpercentile(hub_y[pl["found"]], 97) - 3)
    hub_rest_y = float(np.median(pl["hub_y"][rest]))
    ppm_rest = float(np.median(pl["px_per_m"][rest]))
else:
    rest = np.ones(n, bool)
# background: setup frames (bar on the floor, wrists below the knees), spread out
knee_y = kp[:, [COCO["l_knee"], COCO["r_knee"]], 1].mean(1)
setup = np.flatnonzero(rest & (wrist_y > knee_y))
bg_idx = setup[np.linspace(0, len(setup) - 1, min(40, len(setup))).astype(int)].tolist()

need = set(pick) | set(bg_idx)
info = probe(clip)
imgs: dict[int, np.ndarray] = {}
for f, img in enumerate(frames(clip, info)):
    if f in need:
        imgs[f] = img.copy()
    if f > max(need):
        break
bg = np.median(np.stack([imgs[f] for f in bg_idx]), 0).astype(np.uint8)
cy = info.height / 2

r0 = float(pl["r0"]) if pl is not None else 0.0
rows = []
for f in pick:
    img, k = imgs[f], kp[f]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if pl is not None:
        near = H.find_near_plate(gray, k, r0)  # plate.npz can follow other round objects
        if near is None:
            continue
        ppm = P.px_per_m(near[2], near[3])
        rn_c = float(np.sqrt(near[2] * near[3]))
    else:
        near, ppm, rn_c = None, ppm_all, 0.0
    row = dict(frame=f, cat=str(cat[f]), px_per_m=round(ppm, 2),
               near_fit=None if near is None else [round(v, 2) for v in near],
               tracker_px_per_m=round(float(pl["px_per_m"][f]), 2)
               if pl is not None and pl["found"][f] else None,
               knee=round(float(ang["knee"][f]), 1), hip=round(float(ang["hip"][f]), 1),
               bbox_top=round(float(per["bbox"][f, 1]), 1),
               bbox_bottom=round(float(per["bbox"][f, 3]), 1),
               ankle_near_y=round(float(k[COCO[f"{side}_ankle"], 1]), 1),
               ankle_far_y=round(float(k[COCO[f"{far_side}_ankle"], 1]), 1),
               ear_y=round(float(k[COCO[f"{side}_ear"], 1]), 1),
               eye_y=round(float(k[COCO[f"{side}_eye"], 1]), 1))
    discs: list[tuple[float, float, float]] = [] if near is None else [
        (near[0], near[1], max(near[2], near[3]))]
    far = None
    if row["cat"] == "overhead" and near is not None:
        far = H.fit_far_plate(gray, (near[0], near[1], max(near[2], near[3])))
        row["far_fit"] = None if far is None else [round(v, 2) for v in far]
        if far is not None:
            discs.append(far[:3])
            row["k_far_major"] = round(H.midline_ratio(max(near[2], near[3]), far[2]), 4)
            row["k_far_geo"] = round(H.midline_ratio(rn_c, far[2]), 4)
    if row["cat"] == "overhead" and near is not None and far is None:
        row["head_xy"] = None  # far plate not found: it may hide the head top
    else:
        ht = H.head_top(img, bg, k, 0.82 * ppm, discs=tuple(discs))
        row["head_xy"] = None if ht is None else [round(v, 1) for v in ht]
    so = H.sole_bottom(img, k, ppm)
    row["sole_xy"] = None if so is None else [round(v, 1) for v in so]
    rows.append(row)

# a fit on another round object (balls, air-bike wheels): radius off the clip's median
ppm_med = float(np.median([r["px_per_m"] for r in rows])) if rows else np.nan
rows = [r for r in rows if abs(r["px_per_m"] / ppm_med - 1) <= 0.05]
k_far = [r["k_far_geo"] for r in rows if r.get("k_far_geo") and r["far_fit"][3] >= 120]
k_proto = H.protocol_ratio(Z_C, S_M)
k_use = k_override if k_override else float(np.median(k_far)) if len(k_far) >= 3 else k_proto
if pl is not None:
    hc = H.camera_height_m(hub_rest_y, ppm_rest, cy)
    floor_plate = H.floor_from_plate(hub_rest_y, ppm_rest, k_use, cy)
    # one scale per clip: the per-frame plate fits scatter ~2% (lettering, hands)
    pm = k_use * ppm_med
else:
    hc, floor_plate, pm = (session["camera_height_m"], session["floor_plate_y"],
                           session["px_per_m_mid"])
    k_use = 1.0
for r in rows:
    r["floor_plate_y"] = round(floor_plate, 1)
    if r["sole_xy"]:
        r["floor_sole_y"] = round(H.floor_from_sole(r["sole_xy"][1], r["ankle_near_y"],
                                                    r["ankle_far_y"], pm, Z_C, hc), 1)
    floors = [r[key] for key in ("floor_sole_y", "floor_plate_y") if key in r]
    r["ear_cm"] = round((float(np.mean(floors)) - r["ear_y"]) / pm * 100, 1)
    r["eye_cm"] = round((float(np.mean(floors)) - r["eye_y"]) / pm * 100, 1)
    if r["head_xy"]:
        r["head_above_ear_cm"] = round((r["ear_y"] - r["head_xy"][1]) / pm * 100, 1)
        r["head_above_eye_cm"] = round((r["eye_y"] - r["head_xy"][1]) / pm * 100, 1)
        for key in ("floor_sole_y", "floor_plate_y"):
            if key in r:
                r["h_" + key[6:-2]] = round((r[key] - r["head_xy"][1]) / pm * 100, 1)
        if "h_sole" in r:
            r["h_cm"] = round((r["h_sole"] + r["h_plate"]) / 2, 1)
        if r["cat"] == "hips":
            r["h_bbox_cm"] = round((r["floor_sole_y"] - r["bbox_top"]) / pm * 100, 1) \
                if "floor_sole_y" in r else None


def stats(vals: list[float]) -> dict:
    v = np.array([x for x in vals if x is not None], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "median": round(float(np.median(v)), 1),
            "iqr": [round(float(q), 1) for q in np.percentile(v, [25, 75])]}


summary = {
    "clip": Path(clip).stem, "side": side, "fps": fps, "frames": len(rows),
    "k_far_median": round(float(np.median(k_far)), 4) if k_far else None,
    "k_far_n": len(k_far), "k_protocol": round(k_proto, 4), "k_used": round(k_use, 4),
    "hub_rest_y": round(hub_rest_y, 1), "px_per_m_rest": round(ppm_rest, 1),
    "camera_height_m": round(hc, 3), "px_per_m_near_median": round(ppm_med, 2),
    "px_per_m_mid": round(pm, 2), "floor_plate_y": round(floor_plate, 1),
    "scale_from": [d.name for d in scale_from],
    "by_cat": {cname: {m: stats([r.get(m) for r in rows if r["cat"] == cname])
                       for m in ("h_cm", "h_sole", "h_plate", "h_bbox_cm",
                                 "ear_cm", "head_above_ear_cm", "eye_cm",
                                 "head_above_eye_cm")}
               for cname in ("hips", "overhead")},
    "all": {m: stats([r.get(m) for r in rows]) for m in ("h_cm", "h_sole", "h_plate")},
}
(out / "height.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
print(json.dumps(summary, indent=1))

# sheet: up to 8 frames, crop around the lifter; lockout-only clips (no head
# top) show the near eye (yellow) instead, as used by height_summary.py
show = [r for r in rows if r.get("h_cm")] or [r for r in rows if r.get("floor_sole_y")]
show = [show[i] for i in np.linspace(0, len(show) - 1, min(8, len(show))).astype(int)] if show else []
tiles = []
for r in show:
    img = imgs[r["frame"]].copy()
    if r.get("head_xy"):
        hx, hy = r["head_xy"]
    else:
        hx, hy = float(kp[r["frame"], COCO[f"{side}_eye"], 0]), r["eye_y"]
        cv2.circle(img, (int(hx), int(hy)), 4, (0, 255, 255), -1)
    for y, col in ((hy, (0, 0, 255)), (r.get("floor_sole_y"), (255, 255, 0)),
                   (r["floor_plate_y"], (255, 0, 255))):
        if y is not None:
            cv2.line(img, (int(hx) - 120, int(y)), (int(hx) + 120, int(y)), col, 1)
    if r.get("head_xy"):
        cv2.circle(img, (int(hx), int(hy)), 4, (0, 0, 255), -1)
    if r["sole_xy"]:
        cv2.circle(img, (int(r["sole_xy"][0]), int(r["sole_xy"][1])), 4, (0, 255, 0), -1)
    nf = r["near_fit"]
    if nf:
        cv2.ellipse(img, ((nf[0], nf[1]), (2 * nf[2], 2 * nf[3]), nf[4]), (0, 255, 0), 1)
    if r.get("far_fit"):
        fx, fy, fr, _ = r["far_fit"]
        cv2.circle(img, (int(fx), int(fy)), int(fr), (255, 0, 255), 1)
    cv2.rectangle(img, (int(per["bbox"][r["frame"], 0]), int(r["bbox_top"])),
                  (int(per["bbox"][r["frame"], 2]), int(r["bbox_bottom"])), (0, 200, 255), 1)
    x0 = int(np.clip(hx - 300, 0, img.shape[1] - 600))
    y0 = int(np.clip(hy - 280, 0, img.shape[0] - 1000))
    t = img[y0:y0 + 1000, x0:x0 + 600].copy()
    label = f"{r['h_cm']} cm" if r.get("h_cm") else f"eye {r['eye_cm']} cm"
    cv2.putText(t, f"f{r['frame']} {r['cat']} {label}", (8, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    tiles.append(t)
if tiles:
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
    cv2.imwrite(str(out / "height_sheet.jpg"), cv2.resize(grid, None, fx=0.6, fy=0.6),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
