"""Knee skeleton on the loaded side-on clips: agreement with RTMPose's own guess.

usage: uv run python scripts/studies/skeleton_loaded.py
reads  out/<clip>/raw_pose.npz, plate.npz, height.json (px_per_m_mid) for the
       loaded right-side 0 deg clips; out/<C1>/raw_pose.npz for the calibration
writes out/skeleton/loaded.json, out/skeleton/loaded.md

Hidden: the raw near-knee keypoint inside the tracked near-plate outline
(snatch.studies.views.ellipse_dist < 1). There is no ground truth here: the numbers
are agreement between the rebuilt knee and RTMPose's knee (and the far knee),
not accuracy.
Lengths: (a) "C1": the C1 length table (snatch.studies.skeleton.length_table over
all C1 frames) scaled by the clip's standing hip-ankle / C1's (camera and
lifter depth check: scripts/studies/skeleton_camera.py); (b) "own": the same table
from the clip's own frames with the knee clear of the plate (ellipse_dist >
1.15) and the knee score >= 0.6.
Pulls from the hub (snatch.studies.skeleton.pull_windows, hub y as the bar), catch
to the v2 lockout where the clip has v2 reps.
"""

import json
from pathlib import Path

import numpy as np

from snatch import skeleton as skel
from snatch.studies import skeleton as sk
from snatch.angles import COCO, joint_angle, mid_y, sagittal_angles
from snatch.studies.height import facing
from snatch.phases import find_reps_v2
from snatch.signals import smooth, smooth_keypoints
from snatch.video import frame_times, mean_rate
from snatch.studies.views import ellipse_dist

C1 = "20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right"
LOADED = ["20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right",
          "20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right",
          "20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right",
          "20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right",
          "20261007_10_jiri_v3_powersnatch_10kg_3rep_fail-bend-elbows_0deg_right",
          "20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right",
          "20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right"]
OUT = Path("out/skeleton")
J = {p: COCO[f"r_{p}"] for p in ("hip", "knee", "ankle", "wrist", "shoulder")}
FAR_KNEE = COCO["l_knee"]


def load(clip: str) -> dict:
    raw = np.load(f"out/{clip}/raw_pose.npz")
    t = frame_times(raw)
    fps = mean_rate(t)
    k = smooth_keypoints(raw["keypoints"].astype(float), fps)
    c = {"clip": clip, "fps": fps, "t": t, "kraw": raw["keypoints"].astype(float), "k": k,
         "score": raw["scores"], "ang": sagittal_angles(k, "r"), "facing": facing(np.median(k, 0))}
    st = (c["ang"]["knee"] > 165) & (c["ang"]["hip"] > 165)
    c["d_stand"] = skel.robust_length(k[:, J["hip"]], k[:, J["ankle"]], st)
    return c


def table_from(c: dict, mask: np.ndarray) -> skel.LengthTable:
    k = c["k"]
    return skel.length_table(k[mask, J["hip"]], k[mask, J["knee"]], k[mask, J["ankle"]], c["d_stand"])


def rebuild(c: dict, tab: skel.LengthTable) -> np.ndarray:
    hip, ank = c["k"][:, J["hip"]], c["k"][:, J["ankle"]]
    lt, ls = tab.lengths(np.hypot(*(ank - hip).T))
    return skel.two_circle_knee(hip, ank, lt, ls, c["facing"])[0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c1 = load(C1)
    tab1 = table_from(c1, np.ones(len(c1["k"]), bool))
    rows, lens, wrist_rows, rebend = [], [], [], []
    for clip in LOADED:
        c = load(clip)
        pl = np.load(f"out/{clip}/plate.npz")
        h = json.loads(Path(f"out/{clip}/height.json").read_text())["summary"]
        ppm = h.get("px_per_m_mid") or 352.8
        ppm = 352.8 if not ppm or np.isnan(ppm) else ppm
        cm = 100 / ppm
        fps, k = c["fps"], c["k"]
        found = pl["found"].astype(bool)
        hub = np.stack([smooth(np.where(found, pl["hub_x"], np.nan), fps),
                        smooth(np.where(found, pl["hub_y"], np.nan), fps)], 1)
        kr = c["kraw"][:, J["knee"]]
        dist = ellipse_dist(kr[:, 0], kr[:, 1], pl["hub_x"], pl["hub_y"], pl["a"], pl["b"], pl["angle"])
        dist = np.where(found, dist, np.inf)
        hidden = dist < 1.0

        def pdist(name: str) -> np.ndarray:
            q = c["kraw"][:, J[name]]
            return np.where(found, ellipse_dist(q[:, 0], q[:, 1], pl["hub_x"], pl["hub_y"], pl["a"], pl["b"],
                                                pl["angle"]), np.inf)
        hip_d, ank_d = pdist("hip"), pdist("ankle")
        inputs_hidden = (hip_d < 1.0) | (ank_d < 1.0)
        clear = ((dist > 1.15) & (hip_d > 1.15) & (ank_d > 1.15)
                 & (c["score"][:, [J["knee"], J["hip"], J["ankle"]]] >= 0.6).all(1))
        wr = c["kraw"][:, J["wrist"]]
        wdist = np.where(found, ellipse_dist(wr[:, 0], wr[:, 1], pl["hub_x"], pl["hub_y"], pl["a"],
                                             pl["b"], pl["angle"]), np.inf)
        ev = sk.pull_windows(hub[:, 1], k[:, J["knee"], 1], k[:, J["hip"], 1], c["ang"]["knee"], fps, c["t"])
        reps = find_reps_v2(hub_y=smooth(pl["hub_y"], fps), nose_y=mid_y(k, "nose"), hip_y=mid_y(k, "hip"),
                            knee=c["ang"]["knee"], fps=fps, knee_y=mid_y(k, "knee"), t=c["t"])
        for e in ev:
            r = [r for r in reps if r.setup - fps < e["setup"] < r.overhead_start]
            e["lockout"] = r[0].lockout if r else None
        n = len(k)
        lab = np.full(n, -1)
        for e in ev:
            lab = np.where(lab < 0, sk.phase_labels(n, e, fps), lab)
        s = c["d_stand"] / c1["d_stand"]
        tabs = {"C1": tab1.scaled(s), "own": table_from(c, clear)}
        lens.append({"clip": clip, "scale_vs_C1": s, "n_clear": int(clear.sum()),
                     "own_r": ((tabs["own"].edges[:-1] + tabs["own"].edges[1:]) / 2).tolist(),
                     "own_thigh": tabs["own"].thigh.tolist(), "own_shank": tabs["own"].shank.tolist(),
                     "c1_thigh": tabs["C1"].thigh.tolist(), "c1_shank": tabs["C1"].shank.tolist(),
                     "clear_r_hist": np.histogram(np.hypot(*(k[clear, J['ankle']] - k[clear, J['hip']]).T)
                                                  / c["d_stand"], tabs["own"].edges)[0].tolist()})
        kn = k[:, J["knee"]]
        a_obs = c["ang"]["knee"]
        for tname, tab in tabs.items():
            kh = rebuild(c, tab)
            a_hat = joint_angle(k[:, J["hip"]], kh, k[:, J["ankle"]])
            a_far = joint_angle(k[:, COCO["l_hip"]], k[:, FAR_KNEE], k[:, COCO["l_ankle"]])
            for pi, ph in enumerate(sk.PHASES):
                inph = lab == pi
                if inph.sum() < 5:
                    continue
                sel = inph & hidden
                row = {"clip": clip, "lengths": tname, "phase": ph, "n_phase": int(inph.sum()),
                       "hidden_pct": float(100 * sel.sum() / inph.sum()),
                       "ankle_hidden_pct": float(100 * (inph & (ank_d < 1)).sum() / inph.sum()),
                       "hip_hidden_pct": float(100 * (inph & (hip_d < 1)).sum() / inph.sum()),
                       "inputs_hidden_of_knee_hidden_pct": float(100 * (sel & inputs_hidden).sum() / max(sel.sum(), 1))}
                if sel.sum() >= 5:
                    e = np.hypot(*(kh[sel] - kn[sel]).T) * cm
                    ef = np.hypot(*(k[sel, FAR_KNEE] - kn[sel]).T) * cm
                    efh = np.hypot(*(k[sel, FAR_KNEE] - kh[sel]).T) * cm
                    row |= {"n": int(sel.sum()),
                            "rtm_med_cm": float(np.median(e)), "rtm_p90_cm": float(np.percentile(e, 90)),
                            "rtm_dx_cm": float(np.median((kh[sel, 0] - kn[sel, 0]) * c["facing"]) * cm),
                            "ang_diff_med": float(np.median(a_hat[sel] - a_obs[sel])),
                            "ang_absdiff_med": float(np.median(np.abs(a_hat[sel] - a_obs[sel]))),
                            "far_vs_rtm_cm": float(np.median(ef)), "far_vs_rebuilt_cm": float(np.median(efh)),
                            "far_ang_vs_rtm": float(np.median(np.abs(a_far[sel] - a_obs[sel]))),
                            "far_ang_vs_rebuilt": float(np.median(np.abs(a_far[sel] - a_hat[sel]))),
                            "rtm_score": float(np.median(c["score"][sel, J["knee"]])),
                            "rtm_ang_med": float(np.median(a_obs[sel])), "hat_ang_med": float(np.median(a_hat[sel]))}
                    cl = inph & clear
                    if cl.sum() >= 5:
                        row["clear_err_cm"] = float(np.median(np.hypot(*(kh[cl] - kn[cl]).T)) * cm)
                vis = inph & clear  # knee clear of the plate: RTMPose is a real reference here
                if vis.sum() >= 5:
                    ev_ = np.hypot(*(kh[vis] - kn[vis]).T) * cm
                    row |= {"n_vis": int(vis.sum()), "vis_med_cm": float(np.median(ev_)),
                            "vis_p90_cm": float(np.percentile(ev_, 90)),
                            "vis_ang": float(np.median(np.abs(a_hat[vis] - a_obs[vis]))),
                            "vis_rtm_ang": float(np.median(a_obs[vis]))}
                rows.append(row)
        # catch bottom (lowest hip of each catch +- 0.1 s): projected lengths vs standing
        st = (c["ang"]["knee"] > 165) & (c["ang"]["hip"] > 165) & clear
        bottom = np.zeros(n, bool)
        for e in ev:
            if e["lockout"] is None:
                continue
            i = e["peak"] + int(np.argmax(k[e["peak"]:e["lockout"] + 1, J["hip"], 1]))
            bottom[i - int(0.1 * fps):i + int(0.1 * fps)] = True
        bottom &= clear
        th = np.hypot(*(k[:, J["hip"]] - kn).T)
        sh = np.hypot(*(kn - k[:, J["ankle"]]).T)
        lens[-1] |= {"thigh_stand": float(np.median(th[st])), "shank_stand": float(np.median(sh[st])),
                     "thigh_bottom": float(np.median(th[bottom])) if bottom.any() else None,
                     "shank_bottom": float(np.median(sh[bottom])) if bottom.any() else None,
                     "knee_bottom": float(np.median(a_obs[bottom])) if bottom.any() else None}
        # wrist: offset wrist - hub where the wrist is clear of the plate
        wclear = (wdist > 1.05) & found & (c["score"][:, J["wrist"]] >= 0.6) & (lab >= 0) & (lab <= 3)
        inpull = found & (lab >= 1) & (lab <= 3)
        wr_row = {"clip": clip, "pull_frames": int(inpull.sum()),
                  "wrist_inside_pct": float(100 * (wdist[inpull] < 1).mean()),
                  "wrist_score_pull": float(np.median(c["score"][inpull, J["wrist"]])),
                  "n_clear": int(wclear.sum())}
        o_all, sd_all = sk.fit_offset(k[:, J["wrist"]], hub, inpull)
        wr_row |= {"rtm_off_px": o_all.tolist(), "rtm_off_sd_px": sd_all.tolist(),
                   "rtm_off_cm": (o_all * cm).tolist(), "rtm_off_sd_cm": (sd_all * cm).tolist(),
                   "r_plate_px": float(np.nanmedian(np.sqrt(pl["a"] * pl["b"])[inpull]))}
        for pi in (1, 2, 3):
            o, sd = sk.fit_offset(k[:, J["wrist"]], hub, inpull & (lab == pi))
            wr_row[f"off_{sk.PHASES[pi]}_cm"] = (o * cm).tolist()
            wr_row[f"sd_{sk.PHASES[pi]}_cm"] = (sd * cm).tolist()
        wrist_rows.append(wr_row)
        # knee re-bend (A10): v2 transition and its depth from RTMPose's knee vs the rebuilt knee
        hub_y_raw = smooth(pl["hub_y"], fps)
        for tname, tab in tabs.items():
            kh = rebuild(c, tab)
            hip_, ank_ = k[:, J["hip"]], k[:, J["ankle"]]
            lt_, ls_ = tab.lengths(np.hypot(*(ank_ - hip_).T))
            use = hidden & (sk.knee_gain(hip_, ank_, lt_, ls_, c["facing"]) <= 2.0)
            a_hat = joint_angle(hip_, sk.fill_hidden(kn, kh, use), ank_)
            for src, ang in (("RTMPose", a_obs), (f"rebuilt {tname}", a_hat)):
                if src == "RTMPose" and tname != "C1":
                    continue
                rr = find_reps_v2(hub_y=hub_y_raw, nose_y=mid_y(k, "nose"), hip_y=mid_y(k, "hip"),
                                  knee=ang, fps=fps, knee_y=mid_y(k, "knee"), t=c["t"])
                for ri, r in enumerate(rr):
                    peak = r.setup + int(np.argmax(ang[r.setup:r.overhead_start + 1]))
                    depth = None
                    if r.transition is not None:
                        pre = ang[r.setup:r.transition + 1].max()
                        depth = float(min(pre, ang[r.transition:peak + 1].max()) - ang[r.transition])
                    rebend.append({"clip": clip, "rep": ri + 1, "source": src, "transition": r.transition,
                                   "knee_at_transition": None if r.transition is None else float(ang[r.transition]),
                                   "depth_deg": depth})
        print(clip, "pulls", [(e["setup"], e["knee"], e["hip"], e["peak"], e["lockout"]) for e in ev],
              f"scale {s:.3f} clear {clear.sum()}", flush=True)
    res = {"rows": rows, "lengths": lens, "wrist": wrist_rows, "rebend": rebend,
           "c1_table": {"r": ((tab1.edges[:-1] + tab1.edges[1:]) / 2).tolist(),
                        "thigh": tab1.thigh.tolist(), "shank": tab1.shank.tolist(), "d_stand": c1["d_stand"]}}
    (OUT / "loaded.json").write_text(json.dumps(res, indent=1, default=float))
    write_md(res)


def f(v) -> str:
    return f"{v[0]:+.1f}, {v[1]:+.1f}"


def short(clip: str) -> str:
    return "_" + clip.split("_")[1] + "_"


def write_md(res: dict) -> None:
    L = ["# skeleton_loaded (agreement, not accuracy)", "",
         "## Hidden: % of phase frames with the near knee / hip / ankle inside the plate outline (n frames)", "",
         "| clip | " + " | ".join(sk.PHASES) + " |", "|---|" + "---|" * len(sk.PHASES)]
    clips = list(dict.fromkeys(r["clip"] for r in res["rows"]))
    for c in clips:
        cells = []
        for ph in sk.PHASES:
            r = [r for r in res["rows"] if r["clip"] == c and r["phase"] == ph and r["lengths"] == "C1"]
            cells.append(f"{r[0]['hidden_pct']:.0f} / {r[0]['hip_hidden_pct']:.0f} / {r[0]['ankle_hidden_pct']:.0f} "
                         f"({r[0]['n_phase']})" if r else "–")
        L.append(f"| {short(c)} | " + " | ".join(cells) + " |")
    for tname in ("C1", "own"):
        L += ["", f"## Rebuilt ({tname} lengths) vs RTMPose knee, hidden frames: median cm / p90 cm; "
              "knee angle rebuilt - RTMPose median (abs median) deg; RTMPose angle; far knee vs RTMPose / vs rebuilt cm", "",
              "| clip | phase | n | rebuilt vs RTM cm | dx fwd cm | angle diff deg | RTM / rebuilt angle | far vs RTM cm | far vs rebuilt cm | RTM score | rebuilt vs RTM in clear frames cm |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in res["rows"]:
            if r["lengths"] != tname or "n" not in r:
                continue
            L.append(f"| {short(r['clip'])} | {r['phase']} | {r['n']} | {r['rtm_med_cm']:.1f} / {r['rtm_p90_cm']:.1f} | "
                     f"{r['rtm_dx_cm']:+.1f} | {r['ang_diff_med']:+.1f} ({r['ang_absdiff_med']:.1f}) | "
                     f"{r['rtm_ang_med']:.0f} / {r['hat_ang_med']:.0f} | {r['far_vs_rtm_cm']:.1f} | "
                     f"{r['far_vs_rebuilt_cm']:.1f} | {r['rtm_score']:.2f} | {r.get('clear_err_cm', float('nan')):.1f} |")
    for tname in ("C1", "own"):
        L += ["", f"## Rebuilt ({tname} lengths) vs RTMPose where the knee is clear of the plate (a real reference): "
              "median / p90 cm, abs angle diff deg, RTMPose knee angle", "",
              "| clip | " + " | ".join(sk.PHASES) + " |", "|---|" + "---|" * len(sk.PHASES)]
        for c in clips:
            cells = []
            for ph in sk.PHASES:
                r = [r for r in res["rows"] if r["clip"] == c and r["phase"] == ph and r["lengths"] == tname
                     and "n_vis" in r]
                cells.append(f"{r[0]['vis_med_cm']:.1f}/{r[0]['vis_p90_cm']:.1f} ({r[0]['vis_ang']:.1f}°, "
                             f"{r[0]['vis_rtm_ang']:.0f}°)" if r else "–")
            L.append(f"| {short(c)} | " + " | ".join(cells) + " |")
    L += ["", "## Projected lengths at the catch bottom vs standing (px, knee clear)", "",
          "| clip | thigh stand | thigh bottom | shank stand | shank bottom | knee at bottom deg |", "|---|---|---|---|---|---|"]
    for x in res["lengths"]:
        if x.get("thigh_bottom") is None:
            L.append(f"| {short(x['clip'])} | {x['thigh_stand']:.0f} | – | {x['shank_stand']:.0f} | – | – |")
            continue
        L.append(f"| {short(x['clip'])} | {x['thigh_stand']:.0f} | {x['thigh_bottom']:.0f} ({x['thigh_bottom'] / x['thigh_stand']:.2f}) | "
                 f"{x['shank_stand']:.0f} | {x['shank_bottom']:.0f} ({x['shank_bottom'] / x['shank_stand']:.2f}) | {x['knee_bottom']:.0f} |")
    L += ["", "## Length tables (px): own (clear frames) vs C1 scaled; r = d / d_standing", ""]
    t1 = res["c1_table"]
    L.append("| clip | scale vs C1 | n clear | " + " | ".join(f"r {r:.2f}" for r in t1["r"]) + " |")
    L.append("|---|---|---|" + "---|" * len(t1["r"]))
    L.append("| C1 | 1 | all | " + " | ".join(f"{a:.0f}/{b:.0f}" for a, b in zip(t1["thigh"], t1["shank"])) + " |")
    for x in res["lengths"]:
        cells = [f"{a:.0f}/{b:.0f} ({n})" for a, b, n in zip(x["own_thigh"], x["own_shank"], x["clear_r_hist"])]
        L.append(f"| {short(x['clip'])} | {x['scale_vs_C1']:.3f} | {x['n_clear']} | " + " | ".join(cells) + " |")
    L += ["", "## Knee re-bend (v2 transition) from RTMPose's knee angle vs the hybrid knee (rebuilt where hidden and gain <= 2, "
          "RTMPose elsewhere, snatch.studies.skeleton.fill_hidden): frame, knee deg, depth deg", "",
          "| clip | rep | RTMPose | hybrid, C1 lengths | hybrid, own lengths |", "|---|---|---|---|---|"]
    keys = sorted({(x["clip"], x["rep"]) for x in res["rebend"]}, key=lambda q: (LOADED.index(q[0]), q[1]))
    for cl, rp in keys:
        cells = []
        for src in ("RTMPose", "rebuilt C1", "rebuilt own"):
            x = [x for x in res["rebend"] if x["clip"] == cl and x["rep"] == rp and x["source"] == src]
            cells.append("–" if not x else "none" if x[0]["transition"] is None else
                         f"{x[0]['transition']}, {x[0]['knee_at_transition']:.0f}°, {x[0]['depth_deg']:.1f}°")
        L.append(f"| {short(cl)} | {rp} | " + " | ".join(cells) + " |")
    L += ["", "## Wrist vs hub in the pull (first pull + transition + second pull)", "",
          "| clip | pull frames | wrist inside plate % | wrist score | RTM wrist - hub cm (x, y) | robust SD cm | first pull | transition | second pull | plate r px |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for w in res["wrist"]:
        L.append(f"| {short(w['clip'])} | {w['pull_frames']} | {w['wrist_inside_pct']:.0f} | {w['wrist_score_pull']:.2f} | "
                 f"{f(w['rtm_off_cm'])} | {w['rtm_off_sd_cm'][0]:.1f}, {w['rtm_off_sd_cm'][1]:.1f} | "
                 f"{f(w['off_first pull_cm'])} | {f(w['off_transition_cm'])} | {f(w['off_second pull_cm'])} | {w['r_plate_px']:.0f} |")
    (OUT / "loaded.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
