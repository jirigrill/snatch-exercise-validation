"""Wrist from the hub: how stable is wrist - bar on the bar-only side-on clips?

usage: uv run python scripts/studies/skeleton_wrist.py
reads  ../vids/spike/{C1,C2}.MOV, out/{C1,C2}/raw_pose.npz
writes out/skeleton/collar_{C1,C2}.npz (collar track), out/skeleton/wrist.md,
       out/skeleton/wrist_sheet.jpg (collar + wrist + rebuilt wrist on pull frames)

No plate on C1/C2, so no hub. Stand-in: the near collar of the empty bar
(the dark ring where the plate's inner face would sit, ~3 cm deeper than
the plate's outer face whose outline gives plate.npz's hub). It is tracked
by template matching (TM_CCOEFF_NORMED, 41 px template, search +-12 px per
frame, template refreshed with 10 % of the new patch each frame) from a seed
placed at wrist + SEED_OFFSET at each pull's setup and refined by a search
of +-30 px. The collar is the hub's analogue up to a near-constant offset,
so the stability of wrist - collar over a pull is what transfers.
Models: constant offset (median), and offset linear in the collar's image
position (perspective: the hand is deeper than the plate, so it projects
closer to the principal point by a factor ~ Z_plate / Z_hand), fitted on
the other pulls (C1 leave one out; C2 from C1).
"""

from pathlib import Path

import cv2
import numpy as np

from snatch.studies import skeleton as sk
from snatch.angles import COCO
from snatch.signals import smooth
from snatch.video import frames, probe

import skeleton_validate as sv  # noqa: E402  (scripts/ is on sys.path)

C1 = "20261007_1_jiri_v3_standup_bar_3rep_success_0deg_right"
C2 = "20261007_2_jiri_v3_powersnatch_bar_1rep_success_0deg_right"
OUT = Path("out/skeleton")
PX_PER_M = 352.8
SEED_OFFSET = np.array([-5.0, 57.0])  # collar - wrist at C2 frame 1450, by eye (3x zoom)
HALF, SEARCH, SEED_SEARCH = 20, 12, 30
J = {p: COCO[f"r_{p}"] for p in ("hip", "knee", "ankle", "wrist")}


def load(clip: str) -> dict:
    c = sv.load(clip)
    c["ev"] = sv.pulls(c)  # C2: only the snatch pull (v1 rep), as in skeleton_validate
    return c


def match(gray: np.ndarray, tpl: np.ndarray, p: np.ndarray, r: int) -> tuple[np.ndarray, float]:
    x0, y0 = int(p[0]) - HALF - r, int(p[1]) - HALF - r
    win = gray[y0:y0 + 2 * (HALF + r) + 1, x0:x0 + 2 * (HALF + r) + 1]
    res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    # sub-pixel: parabola on the peak
    dx = dy = 0.0
    lx, ly = loc
    if 0 < lx < res.shape[1] - 1:
        a, b, c = res[ly, lx - 1], res[ly, lx], res[ly, lx + 1]
        dx = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0.0
    if 0 < ly < res.shape[0] - 1:
        a, b, c = res[ly - 1, lx], res[ly, lx], res[ly + 1, lx]
        dy = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0.0
    return np.array([x0 + lx + dx + HALF, y0 + ly + dy + HALF]), float(mx)


def patch(gray: np.ndarray, p: np.ndarray) -> np.ndarray:
    x, y = int(round(p[0])), int(round(p[1]))
    return gray[y - HALF:y + HALF + 1, x - HALF:x + HALF + 1].astype(np.float32)


def track(c: dict, ref_tpl: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """Collar per frame over each pull (setup - 0.25 s .. peak + 0.1 s)."""
    n = len(c["k"])
    pos = np.full((n, 2), np.nan)
    score = np.full(n, np.nan)
    spans = [(e["setup"] - int(0.25 * c["fps"]), e["peak"] + int(0.1 * c["fps"])) for e in c["ev"]]
    path = f"../vids/spike/{c['clip']}.MOV"
    tpl, cur, grabs = None, None, {}
    want = {e[k]: k for e in c["ev"] for k in ("setup", "knee", "hip", "peak")}
    for i, img in enumerate(frames(path, probe(path))):
        if i > spans[-1][1]:
            break
        span = next((s for s in spans if s[0] <= i <= s[1]), None)
        if span is None:
            tpl = None
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if tpl is None:  # seed from the wrist, refine against the reference template
            cur, _ = match(g, ref_tpl, c["k"][i, J["wrist"]] + SEED_OFFSET, SEED_SEARCH)
            tpl = patch(g, cur)
        assert cur is not None  # set with tpl
        cur, sc = match(g, tpl.astype(np.uint8), cur, SEARCH)
        tpl = 0.9 * tpl + 0.1 * patch(g, cur)
        pos[i], score[i] = cur, sc
        if i in want:
            grabs[i] = img.copy()
    return pos, score, grabs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c1, c2 = load(C1), load(C2)
    path = f"../vids/spike/{C2}.MOV"
    for i, img in enumerate(frames(path, probe(path))):
        if i == 1450:
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            break
    else:
        raise ValueError(f"{path} has no frame 1450")
    seed, _ = match(g, patch(g, c2["k"][1450, J["wrist"]] + SEED_OFFSET).astype(np.uint8),
                    c2["k"][1450, J["wrist"]] + SEED_OFFSET, 2)
    ref = patch(g, seed).astype(np.uint8)
    data, grabs = {}, {}
    for c in (c1, c2):
        pos, score, gr = track(c, ref)
        pos_s = np.stack([smooth(pos[:, 0], c["fps"]), smooth(pos[:, 1], c["fps"])], 1)
        pos_s[np.isnan(pos[:, 0])] = np.nan
        np.savez_compressed(OUT / f"collar_{c['clip'].split('_')[1]}.npz", collar=pos, collar_s=pos_s, score=score)
        data[c["clip"]] = (c, pos_s, score)
        grabs[c["clip"]] = gr
        print(c["clip"], "match score median", np.nanmedian(score), "min", np.nanmin(score), flush=True)
    # per pull, offsets by phase; models fitted on the other pulls
    pulls = [(C1, i) for i in range(len(c1["ev"]))] + [(C2, 0)]
    cy = 960.0
    cx = 540.0
    lines = ["| test pull | phase | n | wrist - collar median px (x, y) | cm | robust SD cm (x, y) | "
             "const offset err cm med / p90 | perspective-linear err cm med / p90 |",
             "|---|---|---|---|---|---|---|---|"]
    for clip, ri in pulls:
        c, col, _ = data[clip]
        e = c["ev"][ri]
        lab = sk.phase_labels(len(c["k"]), e, c["fps"])
        # training pulls: all others
        tr_w, tr_h = [], []
        for clip2, rj in pulls:
            if (clip2, rj) == (clip, ri) or (clip == C1 and clip2 == C2):
                continue  # C1 tests train on the other C1 pulls only; C2 trains on C1
            c_, col_, _ = data[clip2]
            lab_ = sk.phase_labels(len(c_["k"]), c_["ev"][rj], c_["fps"])
            m = (lab_ >= 0) & (lab_ <= 3) & ~np.isnan(col_[:, 0])
            tr_w.append(c_["k"][m, J["wrist"]])
            tr_h.append(col_[m])
        W, H = np.vstack(tr_w), np.vstack(tr_h)
        o_const = np.median(W - H, 0)
        A = np.c_[np.ones(len(H)), H[:, 0] - cx, H[:, 1] - cy]
        coef, *_ = np.linalg.lstsq(A, W - H, rcond=None)
        w = c["k"][:, J["wrist"]]
        for pi in range(4):
            sel = (lab == pi) & ~np.isnan(col[:, 0])
            if sel.sum() < 5:
                continue
            o, sd = sk.fit_offset(w[sel], col[sel])
            e1 = np.hypot(*(col[sel] + o_const - w[sel]).T) / PX_PER_M * 100
            pred = col[sel] + np.c_[np.ones(sel.sum()), col[sel, 0] - cx, col[sel, 1] - cy] @ coef
            e2 = np.hypot(*(pred - w[sel]).T) / PX_PER_M * 100
            lines.append(f"| {'_' + clip.split('_')[1] + '_'} pull {ri + 1} | {sk.PHASES[pi]} | {sel.sum()} | "
                         f"{o[0]:+.0f}, {o[1]:+.0f} | {o[0] / PX_PER_M * 100:+.1f}, {o[1] / PX_PER_M * 100:+.1f} | "
                         f"{sd[0] / PX_PER_M * 100:.1f}, {sd[1] / PX_PER_M * 100:.1f} | "
                         f"{np.median(e1):.1f} / {np.percentile(e1, 90):.1f} | {np.median(e2):.1f} / {np.percentile(e2, 90):.1f} |")
        lines.append(f"| ↳ fit | | | const {o_const[0]:+.0f}, {o_const[1]:+.0f} px | | | | "
                     f"lin: o0 {coef[0, 0]:+.0f}, {coef[0, 1]:+.0f}; dx/dX {coef[1, 0]:+.3f}, dy/dY {coef[2, 1]:+.3f} |")
    (OUT / "wrist.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    # sheet: collar (green), wrist (magenta), const-offset wrist (cyan)
    tiles = []
    for clip in (C1, C2):
        c, col, _ = data[clip]
        for i in sorted(grabs[clip]):
            im = grabs[clip][i]
            p, w = col[i], c["k"][i, J["wrist"]]
            cv2.circle(im, (int(p[0]), int(p[1])), 6, (0, 255, 0), 2)
            cv2.circle(im, (int(w[0]), int(w[1])), 6, (255, 0, 255), -1)
            x, y = int(p[0]), int(p[1]) - 40
            crop = cv2.resize(im[max(y - 120, 0):y + 120, max(x - 120, 0):x + 120], (240, 240))
            cv2.putText(crop, f"_{clip.split('_')[1]}_ f{i}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 2)
            tiles.append(crop)
    while len(tiles) % 8:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(OUT / "wrist_sheet.jpg"), np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))


if __name__ == "__main__":
    main()
