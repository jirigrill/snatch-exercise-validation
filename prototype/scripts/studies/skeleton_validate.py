"""Synthetic-occlusion test of the knee skeleton on the bar-only side-on clips.

usage: uv run python scripts/studies/skeleton_validate.py [--seed 0]
reads  out/{C1,C2}/raw_pose.npz (C1 = 20261007_1_..._standup_bar_..., C2 =
       20261007_2_..._powersnatch_bar_..., no plates: the near knee is never hidden)
writes out/skeleton/validate.json, out/skeleton/validate.md (tables),
       out/skeleton/validate_curves.png

The observed (smoothed) near knee is the ground truth. The knee is rebuilt
from the near hip and ankle (snatch.skeleton.two_circle_knee) with lengths
calibrated on frames that do not include the test rep:
  C1 rep k: calibrated on C1 minus rep k (leave one rep out), and on C2;
  C2:       calibrated on C1 (and on C2 itself, for reference).
Length models: "fixed-standing" (median over upright frames), "fixed-p90"
(90th percentile over the calibration frames), "table" (median per bin of
d / d_standing, snatch.skeleton.LengthTable).
Phases from the wrist (no hub here): setup (0.25 s before liftoff), first
pull (liftoff -> wrist at the near knee), transition (wrist at knee -> wrist
at hip), second pull (wrist at hip -> peak knee extension), catch (C2: peak
extension -> lockout). cm at the session body scale 352.8 px/m (doc 35, k
from the far plate; x 0.975 at k = 0.829).
"""

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

from snatch import skeleton as sk
from snatch.angles import COCO, joint_angle, mid_y, sagittal_angles
from snatch.height import facing
from snatch.phases import find_reps
from snatch.signals import smooth_keypoints
from snatch.video import frame_times, mean_rate

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

C1 = "20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right"
C2 = "20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right"
PX_PER_M = 352.8
OUT = Path("out/skeleton")
PHASES = sk.PHASES
seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 0
J = {p: COCO[f"r_{p}"] for p in ("hip", "knee", "ankle", "wrist", "shoulder")}


def load(clip: str) -> dict:
    raw = np.load(f"out/{clip}/raw_pose.npz")
    t = frame_times(raw)
    fps = mean_rate(t)
    k = smooth_keypoints(raw["keypoints"].astype(float), fps)
    ang = sagittal_angles(k, "r")
    return {"clip": clip, "fps": fps, "t": t, "kraw": raw["keypoints"].astype(float),
            "k": k, "score": raw["scores"], "ang": ang,
            "facing": facing(np.median(k, 0))}


def pulls(c: dict) -> list[dict]:
    """Pull windows from the near wrist (snatch.skeleton.pull_windows); C2 is
    a real snatch, so its catch ends at the v1 lockout."""
    k, fps = c["k"], c["fps"]
    ev = sk.pull_windows(k[:, J["wrist"], 1], k[:, J["knee"], 1], k[:, J["hip"], 1],
                         c["ang"]["knee"], fps, c["t"])
    if c["clip"] == C2:
        reps = find_reps(wrist_y=mid_y(k, "wrist"), nose_y=mid_y(k, "nose"),
                         hip_y=mid_y(k, "hip"), knee=c["ang"]["knee"], fps=fps,
                         knee_y=mid_y(k, "knee"), t=c["t"])
        ev = [e for e in ev if any(r.setup - fps < e["setup"] < r.overhead_start for r in reps)]
        for e in ev:
            e["lockout"] = next(r.lockout for r in reps if r.setup - fps < e["setup"] < r.overhead_start)
    return ev


def calib(c: dict, mask: np.ndarray) -> dict:
    """Length models from the frames in mask (joints visible, all of them)."""
    k = c["k"]
    hip, knee, ank = k[:, J["hip"]], k[:, J["knee"]], k[:, J["ankle"]]
    stand = mask & (c["ang"]["knee"] > 165) & (c["ang"]["hip"] > 165)
    d_stand = sk.robust_length(hip, ank, stand)
    return {
        "fixed-standing": (sk.robust_length(hip, knee, stand), sk.robust_length(knee, ank, stand)),
        "fixed-p90": (sk.robust_length(hip, knee, mask, "p90"),
                      sk.robust_length(knee, ank, mask, "p90")),
        "table": sk.length_table(hip[mask], knee[mask], ank[mask], d_stand),
        "d_stand": d_stand,
    }


def rebuild(c: dict, model, hip: np.ndarray, ank: np.ndarray, scale: float = 1.0,
            dl: float = 0.0) -> np.ndarray:
    if isinstance(model, sk.LengthTable):
        lt, ls = model.scaled(scale).lengths(np.hypot(*(ank - hip).T))
    else:
        lt, ls = model[0] * scale, model[1] * scale
    return sk.two_circle_knee(hip, ank, lt * (1 + dl), ls * (1 + dl), c["facing"])[0]


def errors(c: dict, kn_hat: np.ndarray, sel: np.ndarray) -> dict:
    k = c["k"]
    kn = k[:, J["knee"]]
    e = np.hypot(*(kn_hat - kn).T)[sel]
    a_obs = c["ang"]["knee"][sel]
    a_hat = joint_angle(k[sel, J["hip"]], kn_hat[sel], k[sel, J["ankle"]])
    dx = (kn_hat[sel, 0] - kn[sel, 0]) * c["facing"]
    cm = 100 / PX_PER_M
    return {"n": int(sel.sum()), "med_px": float(np.median(e)), "p90_px": float(np.percentile(e, 90)),
            "med_cm": float(np.median(e) * cm), "p90_cm": float(np.percentile(e, 90) * cm),
            "dx_bias_cm": float(np.median(dx) * cm), "ang_med_deg": float(np.median(np.abs(a_hat - a_obs))),
            "ang_p90_deg": float(np.percentile(np.abs(a_hat - a_obs), 90))}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    c1, c2 = load(C1), load(C2)
    p1, p2 = pulls(c1), pulls(c2)
    print(f"C1 pulls {[(e['setup'], e['knee'], e['hip'], e['peak']) for e in p1]}")
    print(f"C2 pulls {p2}")
    print(f"facing C1 {c1['facing']:+.0f} C2 {c2['facing']:+.0f}")
    res: dict = {"pulls": {C1: p1, C2: p2}, "lengths": {}, "rows": []}
    all1, all2 = np.ones(len(c1["k"]), bool), np.ones(len(c2["k"]), bool)
    cal_c1, cal_c2 = calib(c1, all1), calib(c2, all2)
    for nm, cal in (("C1", cal_c1), ("C2", cal_c2)):
        res["lengths"][nm] = {"thigh_stand": cal["fixed-standing"][0], "shank_stand": cal["fixed-standing"][1],
                              "thigh_p90": cal["fixed-p90"][0], "shank_p90": cal["fixed-p90"][1],
                              "d_stand": cal["d_stand"],
                              "table_r": ((cal["table"].edges[:-1] + cal["table"].edges[1:]) / 2).tolist(),
                              "table_thigh": cal["table"].thigh.tolist(),
                              "table_shank": cal["table"].shank.tolist()}
    # camera/scale check between C1 and C2: standing hip-ankle and shank
    s12 = cal_c2["d_stand"] / cal_c1["d_stand"]
    res["scale_c2_over_c1"] = s12
    print(f"standing hip-ankle C1 {cal_c1['d_stand']:.1f} C2 {cal_c2['d_stand']:.1f} px (ratio {s12:.3f})")

    # tests: (test clip, test rep index or None, calibration name, cal dict, scale)
    tests = []
    for i, e in enumerate(p1):
        m = all1.copy()
        m[max(e["setup"] - int(0.5 * c1["fps"]), 0):e["peak"] + int(0.5 * c1["fps"])] = False
        tests.append((c1, [e], f"C1 rep{i + 1}", "C1 other reps", calib(c1, m)))
        tests.append((c1, [e], f"C1 rep{i + 1}", "C2", cal_c2))
    tests.append((c2, p2, "C2", "C1", cal_c1))
    tests.append((c2, p2, "C2", "C2 self", cal_c2))
    curves = []
    for c, evs, tname, cname, cal in tests:
        n = len(c["k"])
        lab = np.full(n, -1)
        for e in evs:
            lab = np.where(lab < 0, sk.phase_labels(n, e, c["fps"]), lab)
        hip, ank = c["k"][:, J["hip"]], c["k"][:, J["ankle"]]
        for mname in ("fixed-standing", "fixed-p90", "table"):
            kn_hat = rebuild(c, cal[mname], hip, ank)
            for pi, ph in enumerate(PHASES):
                sel = lab == pi
                if sel.sum() < 5:
                    continue
                res["rows"].append({"test": tname, "calib": cname, "model": mname,
                                    "case": "clean", "phase": ph, **errors(c, kn_hat, sel)})
            if mname == "table" and cname in ("C1 other reps", "C1"):
                curves.append((tname, c, lab, kn_hat))
        # robustness on the table model: noise on raw hip/ankle, length +-2 %
        model = cal["table"]
        for case, kw in (("len +2%", {"dl": 0.02}), ("len -2%", {"dl": -0.02})):
            kn_hat = rebuild(c, model, hip, ank, **kw)
            for pi, ph in enumerate(PHASES):
                sel = lab == pi
                if sel.sum() >= 5:
                    res["rows"].append({"test": tname, "calib": cname, "model": "table",
                                        "case": case, "phase": ph, **errors(c, kn_hat, sel)})
        for sd in (2.0, 5.0):
            h_n = hip + rng.normal(0, sd, hip.shape)
            a_n = ank + rng.normal(0, sd, ank.shape)
            kn_hat = rebuild(c, model, h_n, a_n)
            for pi, ph in enumerate(PHASES):
                sel = lab == pi
                if sel.sum() >= 5:
                    res["rows"].append({"test": tname, "calib": cname, "model": "table",
                                        "case": f"noise {sd:.0f}px", "phase": ph,
                                        **errors(c, kn_hat, sel)})
        # raw (unsmoothed) hip/ankle as inputs, smoothed knee as truth
        kn_hat = rebuild(c, model, c["kraw"][:, J["hip"]], c["kraw"][:, J["ankle"]])
        for pi, ph in enumerate(PHASES):
            sel = lab == pi
            if sel.sum() >= 5:
                res["rows"].append({"test": tname, "calib": cname, "model": "table",
                                    "case": "raw inputs", "phase": ph, **errors(c, kn_hat, sel)})
        # conditioning: gain and clipped share per phase (table lengths)
        lt, ls = model.lengths(np.hypot(*(ank - hip).T))
        g = sk.knee_gain(hip, ank, lt, ls, c["facing"])
        _, clipped = sk.two_circle_knee(hip, ank, lt, ls, c["facing"])
        for pi, ph in enumerate(PHASES):
            sel = lab == pi
            if sel.sum() >= 5:
                res["rows"].append({"test": tname, "calib": cname, "model": "table",
                                    "case": "conditioning", "phase": ph, "n": int(sel.sum()),
                                    "gain_med": float(np.median(g[sel])),
                                    "gain_p90": float(np.percentile(g[sel], 90)),
                                    "clipped": float(clipped[sel].mean()),
                                    "knee_deg_med": float(np.median(c["ang"]["knee"][sel]))})
    res["elbow"] = elbow_test(c1, c2, p1, p2)
    (OUT / "validate.json").write_text(json.dumps(res, indent=1, default=float))
    write_md(res)
    plot(curves)


def elbow_test(c1: dict, c2: dict, p1: list, p2: list) -> list[dict]:
    """Optional method 3: elbow from shoulder + (true) wrist + arm lengths.

    Same two-circle construction (upper arm around the shoulder, forearm
    around the wrist), lengths as a table over shoulder-wrist distance, the
    side (elbow in front of / behind the line) from the calibration frames'
    median. Calibrated on C1 minus the test pull (C1) or on C1 (C2). The true
    wrist is used, so this is a best case.
    """
    E, S, W = COCO["r_elbow"], COCO["r_shoulder"], COCO["r_wrist"]
    rows = []
    tests = [(c1, e, i, f"C1 rep{i + 1}") for i, e in enumerate(p1)] + [(c2, e, 0, "C2") for e in p2]
    for c, e, i, name in tests:
        m = np.ones(len(c1["k"]), bool)
        if c is c1:
            m[max(e["setup"] - int(0.5 * c1["fps"]), 0):e["peak"] + int(0.5 * c1["fps"])] = False
        k1 = c1["k"]
        d_ref = float(np.percentile(np.hypot(*(k1[m, S] - k1[m, W]).T), 95))
        tab = sk.length_table(k1[m, S], k1[m, E], k1[m, W], d_ref)
        _, _, out = sk.local_frame(k1[m, S], k1[m, W], k1[m, E], 1.0)
        side = 1.0 if np.median(out) >= 0 else -1.0
        k = c["k"]
        lu, lf = tab.lengths(np.hypot(*(k[:, W] - k[:, S]).T))
        eh, clipped = sk.two_circle_knee(k[:, S], k[:, W], lu, lf, side)
        g = sk.knee_gain(k[:, S], k[:, W], lu, lf, side)
        lab = sk.phase_labels(len(k), e, c["fps"])
        a_obs = joint_angle(k[:, S], k[:, E], k[:, W])
        a_hat = joint_angle(k[:, S], eh, k[:, W])
        for pi, ph in enumerate(PHASES[:4]):
            sel = lab == pi
            if sel.sum() < 5:
                continue
            err = np.hypot(*(eh[sel] - k[sel, E]).T) / PX_PER_M * 100
            rows.append({"test": name, "phase": ph, "med_cm": float(np.median(err)),
                         "p90_cm": float(np.percentile(err, 90)), "gain_med": float(np.median(g[sel])),
                         "clipped": float(clipped[sel].mean()), "elbow_obs": float(np.median(a_obs[sel])),
                         "ang_err": float(np.median(np.abs(a_hat[sel] - a_obs[sel])))})
    return rows


def write_md(res: dict) -> None:
    rows = res["rows"]
    lines = ["# skeleton_validate (synthetic occlusion, C1/C2)", ""]
    lines.append("## Clean, by model (median / p90 error cm; knee angle error deg median)")
    lines.append("")
    lines.append("| test | calib | model | " + " | ".join(PHASES) + " |")
    lines.append("|---|---|---|" + "---|" * len(PHASES))
    keys = sorted({(r["test"], r["calib"], r["model"]) for r in rows if r["case"] == "clean"})
    for key in keys:
        cells = []
        for ph in PHASES:
            r = [r for r in rows if (r["test"], r["calib"], r["model"]) == key
                 and r["case"] == "clean" and r["phase"] == ph]
            cells.append(f"{r[0]['med_cm']:.1f}/{r[0]['p90_cm']:.1f} ({r[0]['ang_med_deg']:.1f}°)"
                         if r else "–")
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | " + " | ".join(cells) + " |")
    lines += ["", "## Robustness, table model (median / p90 cm)", ""]
    lines.append("| test | calib | case | " + " | ".join(PHASES) + " |")
    lines.append("|---|---|---|" + "---|" * len(PHASES))
    keys = sorted({(r["test"], r["calib"], r["case"]) for r in rows
                   if r["model"] == "table" and r["case"] not in ("conditioning",)})
    for key in keys:
        cells = []
        for ph in PHASES:
            r = [r for r in rows if (r["test"], r["calib"], r["case"]) == key
                 and r["model"] == "table" and r["phase"] == ph]
            cells.append(f"{r[0]['med_cm']:.1f}/{r[0]['p90_cm']:.1f}" if r else "–")
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | " + " | ".join(cells) + " |")
    lines += ["", "## Conditioning (table lengths): gain px/px median (p90), clipped %, knee deg", ""]
    lines.append("| test | calib | " + " | ".join(PHASES) + " |")
    lines.append("|---|---|" + "---|" * len(PHASES))
    keys = sorted({(r["test"], r["calib"]) for r in rows if r["case"] == "conditioning"})
    for key in keys:
        cells = []
        for ph in PHASES:
            r = [r for r in rows if (r["test"], r["calib"]) == key
                 and r["case"] == "conditioning" and r["phase"] == ph]
            cells.append(f"{r[0]['gain_med']:.1f} ({r[0]['gain_p90']:.1f}), {100 * r[0]['clipped']:.0f}%,"
                         f" {r[0]['knee_deg_med']:.0f}°" if r else "–")
        lines.append(f"| {key[0]} | {key[1]} | " + " | ".join(cells) + " |")
    lines += ["", "## Elbow from shoulder + true wrist (optional method 3): median / p90 cm, gain, clipped %, "
              "observed elbow deg, abs angle error deg", "", "| test | " + " | ".join(PHASES[:4]) + " |",
              "|---|" + "---|" * 4]
    for t in dict.fromkeys(r["test"] for r in res["elbow"]):
        cells = []
        for ph in PHASES[:4]:
            r = [r for r in res["elbow"] if r["test"] == t and r["phase"] == ph]
            cells.append(f"{r[0]['med_cm']:.1f}/{r[0]['p90_cm']:.1f}, g {r[0]['gain_med']:.1f}, "
                         f"{100 * r[0]['clipped']:.0f}%, {r[0]['elbow_obs']:.0f}°, ±{r[0]['ang_err']:.0f}°" if r else "–")
        lines.append(f"| {t} | " + " | ".join(cells) + " |")
    L = res["lengths"]
    lines += ["", "## Lengths (px)", "", "| clip | thigh stand | shank stand | thigh p90 | shank p90 | hip-ankle stand |",
              "|---|---|---|---|---|---|"]
    for nm, v in L.items():
        lines.append(f"| {nm} | {v['thigh_stand']:.1f} | {v['shank_stand']:.1f} | {v['thigh_p90']:.1f} | "
                     f"{v['shank_p90']:.1f} | {v['d_stand']:.1f} |")
    lines += ["", "Table (r = d/d_stand: thigh, shank px):", ""]
    for nm, v in L.items():
        lines.append(f"- {nm}: " + ", ".join(f"{r:.2f}: {a:.0f}/{b:.0f}" for r, a, b in
                                              zip(v["table_r"], v["table_thigh"], v["table_shank"])))
    (OUT / "validate.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def plot(curves) -> None:
    fig, axes = plt.subplots(len(curves), 1, figsize=(10, 2.6 * len(curves)), squeeze=False)
    for ax, (tname, c, lab, kn_hat) in zip(axes[:, 0], curves):
        idx = np.flatnonzero(lab >= 0)
        a, b = idx[0], idx[-1] + 1
        tt = c["t"][a:b] - c["t"][a]
        k = c["k"]
        obs = c["ang"]["knee"][a:b]
        hat = joint_angle(k[a:b, J["hip"]], kn_hat[a:b], k[a:b, J["ankle"]])
        ax.plot(tt, obs, label="observed knee angle")
        ax.plot(tt, hat, "--", label="rebuilt (table)")
        ax2 = ax.twinx()
        ax2.plot(tt, np.hypot(*(kn_hat[a:b] - k[a:b, J["knee"]]).T) / PX_PER_M * 100, "r:",
                 label="error cm")
        ax2.set_ylabel("error cm")
        for pi in range(1, 5):
            ch = np.flatnonzero(lab[a:b] == pi)
            if len(ch):
                ax.axvline(tt[ch[0]], color="grey", lw=0.5)
        ax.set_title(tname)
        ax.set_ylabel("knee deg")
        ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "validate_curves.png", dpi=90)


if __name__ == "__main__":
    main()
