"""Did the camera move between the side-on spike clips? (for transferring px lengths)

usage: uv run python scripts/studies/skeleton_camera.py
reads  ../vids/spike/<clip>.MOV (first frame), out/<clip>/person.npz, plate.npz, raw_pose.npz
writes out/skeleton/camera.md (table), out/skeleton/camera_diff.jpg (C1 vs each clip,
       background difference after no alignment)

Per clip, against 20261007_1 (C1):
- background shift/scale/roll: SIFT matches on the first frame, the lifter's
  boxes over the clip (+15 %) and the bottom 35 % of the image (bar, plates)
  masked out, similarity transform by RANSAC (2 px). (ECC on the same masks
  gave scale errors of up to 3.5 % and was dropped.)
- hub at rest (median hub over rest frames, snatch.studies.views.rest_mask) and the
  near-plate radius sqrt(a b) at rest: the bar's set-down spot and depth.
- standing near hip-ankle distance (knee and hip > 165 deg, median, px):
  the lifter's own depth; this is the px-length rescale factor between clips.
"""

from pathlib import Path

import cv2
import numpy as np

from snatch.angles import COCO, sagittal_angles
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frame_times, frames, mean_rate, probe
from snatch.studies.views import rest_mask

CLIPS = ["20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right",
         "20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right",
         "20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right",
         "20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right",
         "20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right",
         "20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right",
         "20261007_10_jiri_v3_powersnatch_10kg_3rep_fail-bend-elbows_0deg_right",
         "20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right",
         "20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right"]
OUT = Path("out/skeleton")


def first_frame(clip: str) -> np.ndarray:
    path = f"../vids/spike/{clip}.MOV"
    for img in frames(path, probe(path)):
        return img.copy()
    raise RuntimeError(clip)


def mask_for(clip: str, shape) -> np.ndarray:
    box = np.load(f"out/{clip}/person.npz")["bbox"]
    m = np.ones(shape[:2], np.uint8)
    for b in box[~np.isnan(box).any(1)][::24]:  # every box over the clip
        w, h = b[2] - b[0], b[3] - b[1]
        x0, y0 = int(max(b[0] - 0.15 * w, 0)), int(max(b[1] - 0.15 * h, 0))
        m[y0:int(b[3] + 0.15 * h), x0:int(b[2] + 0.15 * w)] = 0
    m[int(0.65 * shape[0]):] = 0
    return m


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ref = first_frame(CLIPS[0])
    ref_m = mask_for(CLIPS[0], ref.shape)
    sift = cv2.SIFT_create(4000)
    k0, d0 = sift.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), ref_m)
    rows, diffs = [], []
    for clip in CLIPS:
        img = first_frame(clip)
        m = mask_for(clip, img.shape)
        k1, d1 = sift.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), m)
        good = [p for p, q in cv2.BFMatcher().knnMatch(d0, d1, k=2) if p.distance < 0.7 * q.distance]
        p0 = np.float32([k0[g.queryIdx].pt for g in good])
        p1 = np.float32([k1[g.trainIdx].pt for g in good])
        M, inl = cv2.estimateAffinePartial2D(p0, p1, ransacReprojThreshold=2.0)
        sc = float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
        tx, ty = float(M[0, 2]), float(M[1, 2])
        rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
        n_inl = int(inl.sum())
        raw = np.load(f"out/{clip}/raw_pose.npz")
        fps = mean_rate(frame_times(raw))
        k = smooth_keypoints(raw["keypoints"].astype(float), fps)
        a = sagittal_angles(k, "r")
        st = (a["knee"] > 165) & (a["hip"] > 165)
        d = np.hypot(*(k[:, COCO["r_hip"]] - k[:, COCO["r_ankle"]]).T)
        sh = np.hypot(*(k[:, COCO["r_knee"]] - k[:, COCO["r_ankle"]]).T)
        row = {"clip": clip, "tx": tx, "ty": ty, "scale": sc, "rot": rot, "n_inl": n_inl, "d_stand": float(np.median(d[st])),
               "shank_stand": float(np.median(sh[st])), "n_stand": int(st.sum()),
               "ankle_x": float(np.median(k[st, COCO["r_ankle"], 0])),
               "ankle_y": float(np.median(k[st, COCO["r_ankle"], 1]))}
        p = Path(f"out/{clip}/plate.npz")
        if p.exists():
            pl = np.load(p)
            rest = rest_mask(smooth(pl["hub_y"], fps), pl["found"], fps)
            row |= {"hub_rest_x": float(np.median(pl["hub_x"][rest])),
                    "hub_rest_y": float(np.median(pl["hub_y"][rest])),
                    "r_rest": float(np.median(np.sqrt(pl["a"][rest] * pl["b"][rest])))}
        rows.append(row)
        diffs.append(cv2.resize(cv2.absdiff(ref, img), None, fx=0.25, fy=0.25))
        print(row, flush=True)
    c1 = rows[0]
    lines = ["| clip | bg tx px | bg ty px | bg scale | bg roll deg (inliers) | hub rest x, y | plate r rest px | ankle x, y (standing) | "
             "hip-ankle stand px (ratio to C1) | shank stand px |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        hub = f"{r['hub_rest_x']:.0f}, {r['hub_rest_y']:.0f}" if "hub_rest_x" in r else "– (no plate)"
        rr = f"{r['r_rest']:.1f}" if "r_rest" in r else "–"
        lines.append(f"| {r['clip']} | {r['tx']:+.1f} | {r['ty']:+.1f} | {r['scale']:.4f} | {r['rot']:+.2f} ({r['n_inl']}) | {hub} | {rr} | "
                     f"{r['ankle_x']:.0f}, {r['ankle_y']:.0f} | {r['d_stand']:.1f} ({r['d_stand'] / c1['d_stand']:.3f}) "
                     f"(n {r['n_stand']}) | {r['shank_stand']:.1f} |")
    (OUT / "camera.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    while len(diffs) % 3:
        diffs.append(np.zeros_like(diffs[0]))
    cv2.imwrite(str(OUT / "camera_diff.jpg"),
                np.vstack([np.hstack(diffs[i:i + 3]) for i in range(0, len(diffs), 3)]))


if __name__ == "__main__":
    main()
