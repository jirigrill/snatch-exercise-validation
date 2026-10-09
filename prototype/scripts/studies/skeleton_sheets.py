"""Frame sheets: observed vs rebuilt near knee (visual check of the skeleton).

usage: uv run python scripts/studies/skeleton_sheets.py
reads  out/<clip>/raw_pose.npz (+ plate.npz for the loaded clips), the videos
writes out/skeleton/sheet_c1.jpg   C1 (no plate): per pull, frames at bar-at-knee, mid
                                   transition, bar-at-hip. Green = observed knee (truth),
                                   cyan = rebuilt (C1 table, leave-one-pull-out)
       out/skeleton/sheet_loaded.jpg  loaded clips, rep 1: the hidden-knee frames at mid
                                   first pull and mid transition. Red = RTMPose knee (a
                                   guess, behind the plate), cyan = rebuilt with the C1
                                   table, yellow = rebuilt with the clip's own table,
                                   magenta = far knee. Thin lines: hip-knee-ankle.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from snatch.studies import skeleton as sk
from snatch.signals import smooth
from snatch.video import frames, probe
from snatch.studies.views import ellipse_dist

sys.path.insert(0, str(Path(__file__).parent))
import skeleton_loaded as sl  # noqa: E402
import skeleton_validate as sv  # noqa: E402

OUT = Path("out/skeleton")
J = sv.J
SHOW = ["20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right",
        "20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right",
        "20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right",
        "20261007_10_jiri_v3_powersnatch_10kg_3rep_fail-bend-elbows_0deg_right",
        "20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right"]


def grab(clip: str, want: set[int]) -> dict[int, np.ndarray]:
    path = f"../vids/spike/{clip}.MOV"
    got = {}
    for i, img in enumerate(frames(path, probe(path))):
        if i in want:
            got[i] = img.copy()
        if i >= max(want):
            break
    return got


def draw(im, k, i, pts, label, centre):
    for p, col in pts:
        cv2.circle(im, (int(p[0]), int(p[1])), 8, col, 2)
    for kn, col in ((pts[0][0], pts[0][1]), (pts[1][0], pts[1][1])):
        for j in (J["hip"], J["ankle"]):
            cv2.line(im, tuple(int(v) for v in k[i, j]), (int(kn[0]), int(kn[1])), col, 1)
    x, y = int(centre[0]), int(centre[1])
    crop = cv2.resize(im[max(y - 220, 0):y + 220, max(x - 220, 0):x + 220], (440, 440))
    for th, c in ((4, (0, 0, 0)), (1, (255, 255, 255))):
        cv2.putText(crop, label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, th)
    return crop


def grid(tiles, cols):
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    return np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])


def main() -> None:
    c1 = sv.load(sv.C1)
    ev = sv.pulls(c1)
    tiles = []
    want = {}
    for pi, e in enumerate(ev):
        m = np.ones(len(c1["k"]), bool)
        m[max(e["setup"] - int(0.5 * c1["fps"]), 0):e["peak"] + int(0.5 * c1["fps"])] = False
        kh = sv.rebuild(c1, sv.calib(c1, m)["table"], c1["k"][:, J["hip"]], c1["k"][:, J["ankle"]])
        for f in (e["knee"], (e["knee"] + e["hip"]) // 2, e["hip"]):
            want[f] = (pi, kh[f])
    imgs = grab(sv.C1, set(want))
    for f in sorted(want):
        pi, kh = want[f]
        kn = c1["k"][f, J["knee"]]
        err = np.hypot(*(kh - kn)) / sv.PX_PER_M * 100
        tiles.append(draw(imgs[f], c1["k"], f, [(kn, (0, 255, 0)), (kh, (255, 255, 0))],
                          f"_1_ pull {pi + 1} f{f} err {err:.1f} cm", kn))
    cv2.imwrite(str(OUT / "sheet_c1.jpg"), grid(tiles, 3), [cv2.IMWRITE_JPEG_QUALITY, 85])

    c1l = sl.load(sv.C1)
    tab1 = sl.table_from(c1l, np.ones(len(c1l["k"]), bool))
    tiles = []
    for clip in SHOW:
        c = sl.load(clip)
        pl = np.load(f"out/{clip}/plate.npz")
        fps, k = c["fps"], c["k"]
        found = pl["found"].astype(bool)
        hub_y = smooth(np.where(found, pl["hub_y"], np.nan), fps)
        kr = c["kraw"][:, J["knee"]]
        dist = np.where(found, ellipse_dist(kr[:, 0], kr[:, 1], pl["hub_x"], pl["hub_y"], pl["a"], pl["b"],
                                            pl["angle"]), np.inf)
        e = sk.pull_windows(hub_y, k[:, J["knee"], 1], k[:, J["hip"], 1], c["ang"]["knee"], fps, c["t"])[0]
        lab = sk.phase_labels(len(k), e, fps)
        k_c1 = sl.rebuild(c, tab1.scaled(c["d_stand"] / c1l["d_stand"]))
        q = [(sl.J[n], n) for n in ("hip", "ankle")]
        clear = (dist > 1.15)
        for n_, _ in q:
            p = c["kraw"][:, n_]
            clear &= np.where(found, ellipse_dist(p[:, 0], p[:, 1], pl["hub_x"], pl["hub_y"], pl["a"], pl["b"],
                                                  pl["angle"]), np.inf) > 1.15
        clear &= (c["score"][:, [J["knee"], J["hip"], J["ankle"]]] >= 0.6).all(1)
        k_own = sl.rebuild(c, sl.table_from(c, clear))
        picks = []
        for pi in (1, 2):
            idx = np.flatnonzero((lab == pi) & (dist < 1))
            if len(idx):
                picks.append(int(idx[len(idx) // 2]))
        imgs = grab(clip, set(picks))
        for f in picks:
            im = imgs[f]
            cv2.ellipse(im, ((pl["hub_x"][f], pl["hub_y"][f]), (2 * pl["a"][f], 2 * pl["b"][f]), pl["angle"][f]),
                        (0, 255, 0), 1)
            d = np.hypot(*(k_c1[f] - k[f, J["knee"]])) / sv.PX_PER_M * 100
            tiles.append(draw(im, k, f, [(k[f, J["knee"]], (0, 0, 255)), (k_c1[f], (255, 255, 0)),
                                         (k_own[f], (0, 255, 255)), (k[f, sl.FAR_KNEE], (255, 0, 255))],
                              f"_{clip.split('_')[1]}_ {sk.PHASES[lab[f]]} f{f} C1-RTM {d:.1f} cm", k[f, J["knee"]]))
    cv2.imwrite(str(OUT / "sheet_loaded.jpg"), grid(tiles, 4), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("wrote", OUT / "sheet_c1.jpg", OUT / "sheet_loaded.jpg")


if __name__ == "__main__":
    main()
