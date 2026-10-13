"""Synthetic plate on the bar-only clips: how good is RTMPose's own guess of a hidden knee?

usage: uv run python scripts/studies/skeleton_paste.py          (~2 min, RTMPose on ~1200 frames)
reads  ../vids/spike/{C1,C2}.MOV, out/{C1,C2}/raw_pose.npz, person.npz,
       out/skeleton/collar_{1,2}.npz (scripts/studies/skeleton_wrist.py: the near collar),
       a real near plate from ../vids/spike/<P3>.MOV (P3 = 20261007_3_..._5kg_..., frame
       PLATE_FRAME, outline from out/<P3>/plate.npz)
writes out/skeleton/paste_{1,2}.npz (keypoints/scores of RTMPose on the pasted frames),
       out/skeleton/paste.md, out/skeleton/paste_sheet.jpg

In every frame of each pull window (setup - 0.25 s .. peak + 0.1 s) a disc of
the real 5 kg bumper (cut from P3, circle of radius sqrt(a b), resized to
R_PLATE px, the loaded clips' rest radius) is pasted with its centre on the
tracked collar + HUB_SHIFT (the plate's outer face sits ~3 cm outboard of
the collar). RTMPose-x is re-run on those frames with the clip's YOLOX boxes
(snatch.pose.run, ranges = the pull windows). Ground truth: the original
(unpasted) smoothed near knee and wrist. Compared in frames with the true
knee (wrist) inside the pasted disc:
- RTMPose on the pasted frame (raw and smoothed), i.e. its guess;
- the skeleton knee (C1 length table, leave-one-pull-out for C1, C1 for C2)
  rebuilt from the pasted run's own hip and ankle;
- wrist = collar + perspective-linear offset (skeleton_wrist.py model, fit on C1).
Limits: YOLOX boxes come from the clean frames; no far plate is pasted; the
pasted disc has no shadow or motion blur.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from scipy.signal import find_peaks

from snatch import pose
from snatch import skeleton as skel
from snatch.studies import skeleton as sk

from snatch.angles import joint_angle, sagittal_angles
from snatch.signals import smooth_keypoints
from snatch.video import frames, probe

import skeleton_validate as sv  # noqa: E402  (scripts/ is on sys.path)

C1, C2 = sv.C1, sv.C2
P3 = "20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right"
PLATE_FRAME = 1105
R_PLATE = 96.0
HUB_SHIFT = np.array([0.0, 6.0])
OUT = Path("out/skeleton")
J = sv.J
PX = sv.PX_PER_M


def plate_disc() -> tuple[np.ndarray, np.ndarray]:
    pl = np.load(f"out/{P3}/plate.npz")
    path = f"../vids/spike/{P3}.MOV"
    for i, img in enumerate(frames(path, probe(path))):
        if i == PLATE_FRAME:
            break
    cx, cy = pl["hub_x"][i], pl["hub_y"][i]
    r = float(np.sqrt(pl["a"][i] * pl["b"][i]))
    h = int(np.ceil(r)) + 2
    crop = img[int(cy) - h:int(cy) + h + 1, int(cx) - h:int(cx) + h + 1].astype(np.float32)
    s = R_PLATE / r
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
    m = np.zeros(crop.shape[:2], np.float32)
    c = (crop.shape[1] - 1) / 2
    cv2.circle(m, (int(round(c)), int(round(c))), int(R_PLATE), 1.0, -1, cv2.LINE_AA)
    return crop, m


def paste(img: np.ndarray, centre: np.ndarray, tex: np.ndarray, m: np.ndarray) -> np.ndarray:
    out = img.astype(np.float32)
    hh = tex.shape[0] // 2
    x0, y0 = int(round(centre[0])) - hh, int(round(centre[1])) - hh
    H, W = img.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + tex.shape[1], W), min(y0 + tex.shape[0], H)
    t = tex[ya - y0:yb - y0, xa - x0:xb - x0]
    mm = m[ya - y0:yb - y0, xa - x0:xb - x0, None]
    out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - mm) + t * mm
    return out.astype(np.uint8)


def run_clip(c: dict, collar: np.ndarray, tex, m) -> tuple[dict, list]:
    spans = [(e["setup"] - int(0.25 * c["fps"]), e["peak"] + int(0.1 * c["fps"]) + 1) for e in c["ev"]]
    path = f"../vids/spike/{c['clip']}.MOV"
    info = probe(path)
    boxes = np.load(f"out/{c['clip']}/person.npz")["bbox"]
    want = {e[k] for e in c["ev"] for k in ("knee", "hip")} | {(e["knee"] + e["hip"]) // 2 for e in c["ev"]}
    grabs = {}

    def images():
        for i, img in enumerate(frames(path, info)):
            if any(a <= i < b for a, b in spans) and not np.isnan(collar[i, 0]):
                img = paste(img, collar[i] + HUB_SHIFT, tex, m)
                if i in want:
                    grabs[i] = img.copy()
            yield img

    res = pose.run(images(), len(c["k"]), boxes, ranges=spans,
                   progress=lambda i: print(f"  {c['clip'][:12]} frame {i}", flush=True) if i % 200 == 0 else None)
    return res, grabs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tex, m = plate_disc()
    c1, c2 = sv.load(C1), sv.load(C2)
    c1["ev"], c2["ev"] = sv.pulls(c1), sv.pulls(c2)
    out_rows, sheet, rb_rows = [], [], []
    col = {C1: np.load(OUT / "collar_1.npz")["collar_s"], C2: np.load(OUT / "collar_2.npz")["collar_s"]}
    # wrist model: perspective-linear offset fitted on the C1 pulls (minus the test pull for C1)
    def wrist_coef(skip: int | None) -> np.ndarray:
        W, H = [], []
        for j, e in enumerate(c1["ev"]):
            if j == skip:
                continue
            lab = sk.phase_labels(len(c1["k"]), e, c1["fps"])
            sel = (lab >= 0) & (lab <= 3) & ~np.isnan(col[C1][:, 0])
            W.append(c1["k"][sel, J["wrist"]])
            H.append(col[C1][sel])
        W, H = np.vstack(W), np.vstack(H)
        A = np.c_[np.ones(len(H)), H[:, 0] - 540, H[:, 1] - 960]
        return np.linalg.lstsq(A, W - H, rcond=None)[0]

    for c in (c1, c2):
        tag = c["clip"].split("_")[1]
        f = OUT / f"paste_{tag}.npz"
        if f.exists() and "--rerun" not in sys.argv:
            d = dict(np.load(f))
            grabs = {}
        else:
            d, grabs = run_clip(c, col[c["clip"]], tex, m)
            np.savez_compressed(f, **d)
        kp = d["keypoints"].astype(float)
        posed = ~np.isnan(kp[:, 0, 0])
        # smooth only inside the posed spans (NaN outside): fill from the clean run
        kp_fill = np.where(posed[:, None, None], kp, c["kraw"])
        ks = smooth_keypoints(kp_fill, c["fps"])
        hub = col[c["clip"]] + HUB_SHIFT
        gt_knee, gt_wr = c["k"][:, J["knee"]], c["k"][:, J["wrist"]]
        inside_k = np.hypot(*(gt_knee - hub).T) < R_PLATE
        inside_w = np.hypot(*(gt_wr - hub).T) < R_PLATE
        a_gt = c["ang"]["knee"]
        a_rtm = sagittal_angles(ks, "r")["knee"]
        for pi_e, e in enumerate(c["ev"]):
            if c["clip"] == C1:
                mcal = np.ones(len(c1["k"]), bool)
                mcal[max(e["setup"] - int(0.5 * c1["fps"]), 0):e["peak"] + int(0.5 * c1["fps"])] = False
                tab = sv.calib(c1, mcal)["table"]
            else:
                tab = sv.calib(c1, np.ones(len(c1["k"]), bool))["table"]
            hip, ank = ks[:, J["hip"]], ks[:, J["ankle"]]
            lt, ls = tab.lengths(np.hypot(*(ank - hip).T))
            kh = skel.two_circle_knee(hip, ank, lt, ls, c["facing"])[0]
            a_hat = joint_angle(hip, kh, ank)
            # hybrid: rebuilt only where the pasted run's knee is inside the plate and the leg is
            # well conditioned (gain <= 2), observed elsewhere, cross-faded (snatch.studies.skeleton.fill_hidden)
            seen_hidden = np.hypot(*(kp[:, J["knee"]] - hub).T) < R_PLATE
            gain = sk.knee_gain(hip, ank, lt, ls, c["facing"])
            kb = sk.fill_hidden(ks[:, J["knee"]], kh, seen_hidden & (gain <= 2.0))
            a_hyb = joint_angle(hip, kb, ank)
            seg = slice(e["setup"], e["peak"] + 1)
            rb = {"clip": tag, "pull": pi_e + 1}
            for nm, a in (("GT", a_gt), ("RTMPose", a_rtm), ("skeleton", a_hat), ("hybrid", a_hyb)):
                mn, pr = find_peaks(-a[seg], prominence=0.5)
                ok = e["setup"] + mn >= e["knee"]
                rb[nm] = float(pr["prominences"][ok].max()) if ok.any() else 0.0
            tr = (sk.phase_labels(len(c["k"]), e, c["fps"]) == 2) & posed
            rb["hyb_tr_cm"] = float(np.median(np.hypot(*(kb[tr] - gt_knee[tr]).T)) / PX * 100)
            rb["hyb_tr_ang"] = float(np.median(np.abs(a_hyb[tr] - a_gt[tr])))
            rb_rows.append(rb)
            coef = wrist_coef(pi_e if c["clip"] == C1 else None)
            wh = hub + np.c_[np.ones(len(hub)), hub[:, 0] - HUB_SHIFT[0] - 540,
                             hub[:, 1] - HUB_SHIFT[1] - 960] @ coef - HUB_SHIFT
            lab = sk.phase_labels(len(c["k"]), e, c["fps"])
            for pi, ph in enumerate(sk.PHASES):
                sel = (lab == pi) & posed
                if sel.sum() < 5:
                    continue
                row = {"clip": tag, "pull": pi_e + 1, "phase": ph, "n": int(sel.sum())}
                sk_ = sel & inside_k
                row["knee_hidden_pct"] = float(100 * sk_.sum() / sel.sum())
                if sk_.sum() >= 5:
                    e_rr = np.hypot(*(kp[sk_, J["knee"]] - gt_knee[sk_]).T) / PX * 100
                    e_rs = np.hypot(*(ks[sk_, J["knee"]] - gt_knee[sk_]).T) / PX * 100
                    e_sk = np.hypot(*(kh[sk_] - gt_knee[sk_]).T) / PX * 100
                    row |= {"n_k": int(sk_.sum()),
                            "rtm_raw_cm": float(np.median(e_rr)), "rtm_cm": float(np.median(e_rs)),
                            "rtm_p90": float(np.percentile(e_rs, 90)),
                            "sk_cm": float(np.median(e_sk)), "sk_p90": float(np.percentile(e_sk, 90)),
                            "rtm_ang": float(np.median(np.abs(a_rtm[sk_] - a_gt[sk_]))),
                            "sk_ang": float(np.median(np.abs(a_hat[sk_] - a_gt[sk_]))),
                            "rtm_dx_cm": float(np.median((ks[sk_, J["knee"], 0] - gt_knee[sk_, 0]) * c["facing"]) / PX * 100),
                            "rtm_dang": float(np.median(a_rtm[sk_] - a_gt[sk_])),
                            "rtm_score": float(np.median(d["scores"][sk_, J["knee"]])),
                            "hip_shift_cm": float(np.median(np.hypot(*(ks[sk_, J["hip"]] - c["k"][sk_, J["hip"]]).T)) / PX * 100),
                            "ankle_shift_cm": float(np.median(np.hypot(*(ks[sk_, J["ankle"]] - c["k"][sk_, J["ankle"]]).T)) / PX * 100)}
                sw = sel & inside_w
                if sw.sum() >= 5:
                    row |= {"n_w": int(sw.sum()),
                            "w_rtm_cm": float(np.median(np.hypot(*(ks[sw, J["wrist"]] - gt_wr[sw]).T)) / PX * 100),
                            "w_hub_cm": float(np.median(np.hypot(*(wh[sw] - gt_wr[sw]).T)) / PX * 100)}
                out_rows.append(row)
        for i in sorted(grabs):
            im = grabs[i]
            for p, colr in ((gt_knee[i], (0, 255, 0)), (ks[i, J["knee"]], (0, 0, 255)), (kh[i], (255, 255, 0)),
                            (gt_wr[i], (0, 255, 0)), (ks[i, J["wrist"]], (0, 0, 255)), (wh[i], (255, 255, 0))):
                cv2.circle(im, (int(p[0]), int(p[1])), 7, colr, 2)
            for a, b in ((J["hip"], J["knee"]), (J["knee"], J["ankle"])):
                cv2.line(im, tuple(int(v) for v in ks[i, a]), tuple(int(v) for v in ks[i, b]), (0, 0, 255), 1)
            x, y = int(hub[i, 0]), int(hub[i, 1])
            crop = cv2.resize(im[max(y - 260, 0):y + 260, max(x - 260, 0):x + 260], (400, 400))
            cv2.putText(crop, f"_{tag}_ f{i}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            sheet.append(crop)
    if sheet:
        while len(sheet) % 6:
            sheet.append(np.zeros_like(sheet[0]))
        cv2.imwrite(str(OUT / "paste_sheet.jpg"), np.vstack([np.hstack(sheet[i:i + 6]) for i in range(0, len(sheet), 6)]))
    L = ["| clip | pull | phase | knee hidden % | n | RTMPose knee err cm (raw) / p90 | skeleton knee err cm / p90 | "
         "angle err deg RTM / skeleton | RTM bias: fwd cm, angle deg | RTM knee score | hip, ankle shift cm | wrist err cm RTM / hub+offset (n) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in out_rows:
        kcells = (f"{r['rtm_cm']:.1f} ({r['rtm_raw_cm']:.1f}) / {r['rtm_p90']:.1f} | {r['sk_cm']:.1f} / {r['sk_p90']:.1f} | "
                  f"{r['rtm_ang']:.1f} / {r['sk_ang']:.1f} | {r['rtm_dx_cm']:+.1f}, {r['rtm_dang']:+.1f} | {r['rtm_score']:.2f} | {r['hip_shift_cm']:.1f}, {r['ankle_shift_cm']:.1f}"
                  if "n_k" in r else "– | – | – | – | – | –")
        wcells = f"{r['w_rtm_cm']:.1f} / {r['w_hub_cm']:.1f} ({r['n_w']})" if "n_w" in r else "–"
        L.append(f"| _{r['clip']}_ | {r['pull']} | {r['phase']} | {r['knee_hidden_pct']:.0f} | {r.get('n_k', 0)} | {kcells} | {wcells} |")
    L += ["", "Knee re-bend: largest knee-angle dip (prominence, deg) after the bar passes the knee, setup -> peak "
          "(v2 counts >= 3 deg); hybrid knee error in the transition", "",
          "| clip | pull | GT | RTMPose (pasted) | skeleton | hybrid | hybrid transition err cm / angle deg |",
          "|---|---|---|---|---|---|---|"]
    for r in rb_rows:
        L.append(f"| _{r['clip']}_ | {r['pull']} | {r['GT']:.1f} | {r['RTMPose']:.1f} | {r['skeleton']:.1f} | "
                 f"{r['hybrid']:.1f} | {r['hyb_tr_cm']:.1f} / {r['hyb_tr_ang']:.1f} |")
    (OUT / "paste.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
