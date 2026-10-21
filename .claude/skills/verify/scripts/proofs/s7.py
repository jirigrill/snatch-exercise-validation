"""S7 proof: does S7 put each phase border within tolerance of the true frame, and is it better than the blind markers?

usage (from prototype/): uv run python ../.claude/skills/verify/scripts/proofs/s7.py <evidence_root>
writes <evidence_root>/proof/S7/{verdict.md, 1_error_dots.png, 2_<clip>_a<k>_fail_strip.jpg ...}

Truth: prototype/tests/data/s7_reference.json (true frame per clip, attempt and border; null = the border does
not exist; tolerance per border). Markers: two agent markers (opus, sonnet) marked the borders blind from raw
frame strips, files .scratch/s7-marks/{opus,sonnet}_{A,B}.json. S7's borders: <root>/<clip>/phases.json.
Cached in .scratch/verify/cache/proof-s7/<key>/ (results, by input and code hash) and
.scratch/verify/cache/proof-s7/frames-<hash>/ (decoded frames of the clips, so a changed layout reruns in seconds).
"""

import hashlib
import inspect
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import matplotlib
import numpy as np

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / ".claude/skills/verify/scripts"))

from check_pipeline import S7_REFERENCE, s7_errors  # noqa: E402  # pyright: ignore[reportMissingImports]
from snatch import phases as ph  # noqa: E402
from snatch import video  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

CACHE = REPO / ".scratch/verify/cache/proof-s7"
MARKS = REPO / ".scratch/s7-marks"
MARKERS = ("opus", "sonnet")
MARGIN = 0.12  # crop margin around the union person box, share of its size
TILE_H = 340
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"]


def log(msg: str) -> None:
    print(f"[s7 proof {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def file_key(p: Path) -> str:
    s = p.stat()
    return f"{s.st_size}-{int(s.st_mtime)}"


def sha(*parts: bytes) -> str:
    h = hashlib.sha1()
    for x in parts:
        h.update(x)
    return h.hexdigest()[:10]


# ---------------------------------------------------------------- data

def clip_dir(root: Path, clip: str) -> Path:
    return next(p for p in sorted(root.glob(f"{clip}_*")) if p.is_dir())


def load_marks(clip: str, attempt: str) -> dict[str, dict[str, int | None]]:
    """{marker: {border: frame|None}} from the .scratch/s7-marks files."""
    res: dict[str, dict[str, int | None]] = {}
    for m in MARKERS:
        for part in "AB":
            d = json.loads((MARKS / f"{m}_{part}.json").read_text())
            if clip in d and attempt in d[clip]:
                res[m] = {n: (d[clip][attempt].get(n) or {}).get("frame") for n in ph.BORDERS}
    return res


def collect(root: Path, ref: dict) -> dict:
    """Everything the verdict and the images need, JSON-serialisable."""
    rows, marker_rows, times, dirs = [], [], {}, {}
    for clip in ref["clips"]:
        d = clip_dir(root, clip)
        dirs[clip] = d.name
        t = np.load(d / "frame_times.npy")
        times[clip] = t
        errs = s7_errors(d, ref, clip)
        for k, row in errs.items():
            marks = load_marks(clip, k)
            for n, (tf, sf, dd, ok) in row.items():
                r = dict(clip=clip, attempt=k, border=n, true=tf, s7=sf, err=dd, ok=ok, tol=ref["tolerance_s"][n],
                         source=ref["clips"][clip][k][n]["source"])
                for m in MARKERS:
                    mf = marks.get(m, {}).get(n)
                    r[m] = mf
                    if tf is None or mf is None:
                        r[f"{m}_err"], r[f"{m}_ok"] = None, tf is None and mf is None
                    else:
                        e = float(t[mf] - t[tf])
                        r[f"{m}_err"], r[f"{m}_ok"] = e, abs(e) <= r["tol"] + 1e-9
                rows.append(r)
    # consistency: T1 vs T8 attempt 1 (same frames)
    cons = []
    s7_t1 = {r["border"]: r["s7"] for r in rows if r["clip"] == "T1" and r["attempt"] == "1"}
    s7_t8 = {r["border"]: r["s7"] for r in rows if r["clip"] == "T8" and r["attempt"] == "1"}
    m1, m8 = load_marks("T1", "1"), load_marks("T8", "1")
    t = times["T1"]
    for n in ph.BORDERS:
        c: dict = {"border": n}
        for who, a, b in [("s7", s7_t1[n], s7_t8[n])] + [(m, m1[m][n], m8[m][n]) for m in MARKERS]:
            c[who] = None if a is None or b is None else float(abs(t[a] - t[b]))
            c[f"{who}_nullmix"] = (a is None) != (b is None)
        cons.append(c)
    return dict(rows=rows, cons=cons, dirs=dirs, tol=ref["tolerance_s"])


def med(x: list[float]) -> float | None:
    return float(np.median(x)) if x else None


def f3(x: float | None) -> str:
    return "-" if x is None else f"{x:.3f}"


def fe(x: float | None) -> str:
    return "-" if x is None else f"{x:+.3f}"


# ---------------------------------------------------------------- images

def dot_chart(data: dict, path: Path) -> None:
    rows, tol = data["rows"], data["tol"]
    atts = sorted({(r["clip"], r["attempt"]) for r in rows}, key=lambda a: (int(a[0][1:]), a[1]))
    col = {a: COLORS[i % len(COLORS)] for i, a in enumerate(atts)}
    fig, ax = plt.subplots(figsize=(9, 6.6), dpi=100)
    ax.set_xscale("symlog", linthresh=0.1, linscale=1.0)
    ax.set_xlim(-6, 6)
    for i, n in enumerate(ph.BORDERS):
        ax.add_patch(Rectangle((-tol[n], i - 0.42), 2 * tol[n], 0.84, color="#b9e3b9", zorder=0))
        for j, a in enumerate(atts):
            r = next(r for r in rows if (r["clip"], r["attempt"], r["border"]) == (*a, n))
            y = i + (j - (len(atts) - 1) / 2) * 0.105
            if r["err"] is not None:
                ax.plot(r["err"], y, "o", color=col[a], ms=7, mec="k" if r["ok"] else "none", mew=1.2 if r["ok"] else 0, zorder=3)
            elif r["true"] is not None:  # S7 null, a true border exists
                ax.plot(-5.2, y, "X", color=col[a], ms=9, zorder=3)
            elif r["s7"] is not None:  # S7 found one, truth has none
                ax.plot(5.2, y, "P", color=col[a], ms=9, zorder=3)
    ax.axvline(0, color="k", lw=0.8)
    ax.axvline(-4.4, color="#999", lw=0.6, ls=":")
    ax.axvline(4.4, color="#999", lw=0.6, ls=":")
    ax.set_yticks(range(len(ph.BORDERS)), [f"{n}\n(tol {tol[n]:g} s)" for n in ph.BORDERS], fontsize=10)
    ax.set_ylim(len(ph.BORDERS) - 0.4, -0.6)
    ax.set_xticks([-4, -2, -1, -0.5, -0.1, 0, 0.1, 0.5, 1, 2, 4], ["-4", "-2", "-1", "-0.5", "-0.1", "0", "0.1", "0.5", "1", "2", "4"], fontsize=10)
    ax.set_xlabel("S7 - true (s).  negative = S7 earlier than true, positive = later  (axis stretched near 0)", fontsize=10)
    ax.set_title("S7 error per border: one dot per attempt, green band = tolerance", fontsize=12)
    handles = [Line2D([], [], marker="o", ls="", color=col[a], label=f"{a[0]} a{a[1]}") for a in atts]
    handles += [Line2D([], [], marker="o", ls="", color="w", mec="k", mew=1.2, label="black ring = within tolerance"),
                Line2D([], [], marker="X", ls="", color="#444", ms=9, label="X at left edge: S7 null, a true border exists"),
                Line2D([], [], marker="P", ls="", color="#444", ms=9, label="+ at right edge: S7 has one, truth has none")]
    ax.legend(handles=handles, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.text(0.99, -0.085, "both null = pass (not drawn)", transform=ax.transAxes, fontsize=8, ha="right", va="top", color="#555")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def grab_frames(clip_file: Path, wanted: set[int]) -> dict[int, np.ndarray]:
    """Decoded frames (BGR), cached as jpg in CACHE/frames-<hash>/."""
    d = CACHE / f"frames-{sha(clip_file.name.encode(), file_key(clip_file).encode())}"
    d.mkdir(parents=True, exist_ok=True)
    out: dict[int, np.ndarray] = {i: cv2.imread(str(d / f"{i}.jpg")) for i in wanted if (d / f"{i}.jpg").is_file()}  # pyright: ignore[reportAssignmentType]
    missing = sorted(wanted - set(out))
    if missing:
        log(f"decoding {clip_file.name[:2]} up to frame {missing[-1]} for {len(missing)} frames")
        info = video.probe(str(clip_file))
        want = set(missing)
        for i, img in enumerate(video.frames(str(clip_file), info, stop=missing[-1] + 1)):
            if i in want:
                cv2.imwrite(str(d / f"{i}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                out[i] = img.copy()
    return out


def text(img: np.ndarray, lines: list[str], y0: int = 20, scale: float = 0.55, color=(255, 255, 255)) -> None:
    for j, s in enumerate(lines):
        cv2.putText(img, s, (6, y0 + j * 20), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def strips(data: dict, root: Path, out_dir: Path) -> list[str]:
    names = []
    for clip in data["dirs"]:
        d = root / data["dirs"][clip]
        pn = np.load(d / "person.npz")
        t = np.load(d / "frame_times.npy")
        clip_file = REPO / "vids/test" / str(pn["clip"])
        attempts = json.loads((d / "attempts.json").read_text())["attempts"]
        for a in attempts:
            k = str(a["attempt"])
            fails = [r for r in data["rows"] if r["clip"] == clip and r["attempt"] == k and not r["ok"]]
            if not fails:
                continue
            s, e = a["window"]
            box = pn["bbox"][s:e]
            x1, y1 = np.nanmin(box[:, 0]), np.nanmin(box[:, 1])
            x2, y2 = np.nanmax(box[:, 2]), np.nanmax(box[:, 3])
            mw, mh = (x2 - x1) * MARGIN, (y2 - y1) * MARGIN
            wanted = {f for r in fails for f in (r["true"], r["s7"]) if f is not None}
            imgs = grab_frames(clip_file, wanted)
            H, W = next(iter(imgs.values())).shape[:2]
            cx1, cy1, cx2, cy2 = (int(max(0, x1 - mw)), int(max(0, y1 - mh)), int(min(W, x2 + mw)), int(min(H, y2 + mh)))
            tw = max(int((cx2 - cx1) * TILE_H / (cy2 - cy1)), 230)

            def tile(frame: int | None, head: str, sub: str, color) -> np.ndarray:
                if frame is None:
                    img = np.full((TILE_H, tw, 3), 40, np.uint8)
                    text(img, [head, sub], 22, 0.6, color)
                    cv2.putText(img, "no border", (tw // 2 - 50, TILE_H // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
                else:
                    c = imgs[frame][cy1:cy2, cx1:cx2]
                    img = cv2.resize(c, (int(c.shape[1] * TILE_H / c.shape[0]), TILE_H))
                    img = cv2.copyMakeBorder(img, 0, 0, 0, max(tw - img.shape[1], 0), cv2.BORDER_CONSTANT, value=(40, 40, 40))[:, :tw]
                    cv2.rectangle(img, (0, 0), (tw, 44), (0, 0, 0), -1)
                    text(img, [head, sub], 18, 0.6, color)
                return cv2.copyMakeBorder(img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))

            pairs = []
            for r in fails:
                tr, s7 = r["true"], r["s7"]
                err = f"{r['err']:+.2f} s" if r["err"] is not None else ("S7 null" if s7 is None else "no true border")
                pairs.append(np.hstack([
                    tile(tr, f"{r['border']}  TRUE", f"f{tr} t={t[tr]:.2f}s" if tr is not None else "none", (120, 255, 120)),
                    tile(s7, f"{r['border']}  S7 ({err})", f"f{s7} t={t[s7]:.2f}s" if s7 is not None else "null", (110, 190, 255))]))
            pad = np.full_like(pairs[0], 255)
            rows = [np.hstack(pairs[i:i + 2] + ([pad] if len(pairs[i:i + 2]) == 1 else [])) for i in range(0, len(pairs), 2)]
            name = f"2_{clip}_a{k}_fail_strip.jpg"
            cv2.imwrite(str(out_dir / name), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
            names.append(name)
    return names


# ---------------------------------------------------------------- verdict

def write_verdict(path: Path, data: dict, ref: dict, strip_names: list[str]) -> None:
    rows, tol, cons = data["rows"], data["tol"], data["cons"]
    n_att = len({(r["clip"], r["attempt"]) for r in rows})
    L = ["# S7 proof: are S7's phase borders where they really are?", ""]
    # ---- Q1
    L += ["## Question 1: does S7 put each phase border within tolerance of the true frame?", "",
          "One row per attempt and border. true / S7 = frame numbers (`-` = the border does not exist / S7 gave none). "
          "S7 - true in seconds of frame time (negative = S7 earlier). Pass = both are null, or both are frames and the "
          "difference is within the tolerance.", "",
          "| clip a | border | true | S7 | S7 - true (s) | tol (s) | result |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['clip']} a{r['attempt']} | {r['border']} | {r['true'] if r['true'] is not None else '-'} | "
                 f"{r['s7'] if r['s7'] is not None else '-'} | {fe(r['err'])} | {r['tol']:g} | {'pass' if r['ok'] else '**FAIL**'} |")
    L += ["", "Totals per border:", "", "| border | pass | fail | S7 null where a true border exists | S7 has one, truth has none | S7 early / late (fails with both frames) |",
          "|---|---|---|---|---|---|"]
    fails_text = []
    for n in ph.BORDERS:
        rr = [r for r in rows if r["border"] == n]
        bad = [r for r in rr if not r["ok"]]
        nul = [r for r in bad if r["s7"] is None and r["true"] is not None]
        ext = [r for r in bad if r["s7"] is not None and r["true"] is None]
        both = [r for r in bad if r["err"] is not None]
        early, late = [r["err"] for r in both if r["err"] < 0], [r["err"] for r in both if r["err"] > 0]
        el = (f"{len(early)} early (median {med([-x for x in early]) or 0:.2f} s)" if early else "0 early") + ", " + \
             (f"{len(late)} late (median {med(late) or 0:.2f} s)" if late else "0 late")
        L.append(f"| {n} | {len(rr) - len(bad)}/{len(rr)} | {len(bad)} | {len(nul)} | {len(ext)} | {el} |")
        if bad:
            bits = []
            if nul:
                bits.append(f"null where a true border exists in {len(nul)} ({', '.join(f'{r['clip']} a{r['attempt']}' for r in nul)})")
            if ext:
                bits.append(f"a border where truth has none in {len(ext)} ({', '.join(f'{r['clip']} a{r['attempt']}' for r in ext)})")
            if both:
                bits.append(f"{el} (worst {max(both, key=lambda r: abs(r['err']))['err']:+.2f} s)")
            fails_text.append(f"{n} {len(bad)}/{len(rr)} fail: " + "; ".join(bits))
    ok_n = sum(r["ok"] for r in rows)
    L += ["", f"Overall: **{ok_n}/{len(rows)}** borders pass ({n_att} attempts x {len(ph.BORDERS)} borders).", ""]
    ans = "yes" if ok_n == len(rows) else "no"
    L.append(f"**Answer: {ans}.** {ok_n} of {len(rows)} borders are within tolerance." +
             ("" if ans == "yes" else " Failing: " + ". ".join(fails_text) + "."))
    if strip_names:
        L += ["", "Images: `1_error_dots.png` (the error of every border, tolerance shaded); per attempt with failing borders a strip of the "
              "frames at the true border next to the frame at S7's (" + ", ".join(f"`{s}`" for s in strip_names) + ")."]
    # ---- Q2
    L += ["", "## Question 2: is S7 better than the blind markers it replaces?", "",
          "The markers (two agents, opus and sonnet, marking blind from raw frame strips) are what S7 replaces as the way to get the "
          "borders. Median |error| against the true frame in seconds, over the attempts where the truth, S7 and both markers all gave a frame "
          "(n); pass = the border rule of question 1 applied to each (out of all attempts).", "",
          "| border | n | S7 median abs err (s) | opus | sonnet | S7 pass | opus pass | sonnet pass |", "|---|---|---|---|---|---|---|---|"]
    better, worse, mixed = [], [], []
    for n in ph.BORDERS:
        rr = [r for r in rows if r["border"] == n]
        com = [r for r in rr if None not in (r["err"], r["opus_err"], r["sonnet_err"])]
        m_s7, m_o, m_s = (med([abs(r[k]) for r in com]) for k in ("err", "opus_err", "sonnet_err"))
        P = {k: sum(r[k] for r in rr) for k in ("ok", "opus_ok", "sonnet_ok")}
        L.append(f"| {n} | {len(com)} | {f3(m_s7)} | {f3(m_o)} | {f3(m_s)} | {P['ok']}/{len(rr)} | {P['opus_ok']}/{len(rr)} | {P['sonnet_ok']}/{len(rr)} |")
        if m_s7 is not None and m_o is not None and m_s is not None:
            (better if m_s7 < min(m_o, m_s) else worse if m_s7 > max(m_o, m_s) else mixed).append(n)
    tot = {k: sum(r[k] for r in rows) for k in ("ok", "opus_ok", "sonnet_ok")}
    L.append(f"| all | | | | | {tot['ok']}/{len(rows)} | {tot['opus_ok']}/{len(rows)} | {tot['sonnet_ok']}/{len(rows)} |")
    L += ["", "Marker consistency: T1 and T8 attempt 1 are the same frames, marked twice by each marker without knowing it "
          "(different sheets, different sessions); S7 on the two clips for comparison. |frame time difference| of the same border in seconds "
          "(`null` mix = one marked it, the other not).", "",
          "| border | S7 | opus | sonnet |", "|---|---|---|---|"]
    for c in cons:
        def cell(w: str) -> str:
            return "null mix" if c[f"{w}_nullmix"] else ("both null" if c[w] is None else f"{c[w]:.3f}")
        L.append(f"| {c['border']} | {cell('s7')} | {cell('opus')} | {cell('sonnet')} |")
    cm = {w: med([c[w] for c in cons if c[w] is not None]) for w in ("s7", "opus", "sonnet")}
    L.append(f"| median | {f3(cm['s7'])} | {f3(cm['opus'])} | {f3(cm['sonnet'])} |")
    L += ["", f"**Answer: {'yes' if len(better) >= 4 and not worse else 'mixed, not clearly'}.** "
          f"Passing borders: S7 {tot['ok']}/{len(rows)}, opus {tot['opus_ok']}/{len(rows)}, sonnet {tot['sonnet_ok']}/{len(rows)}. "
          f"By median error S7 is better than both markers on {', '.join(better) or 'no border'}; worse than both on {', '.join(worse) or 'no border'}; "
          f"between them on {', '.join(mixed) or 'none'}. Consistency (same frames marked twice, median difference): S7 {f3(cm['s7'])} s, "
          f"opus {f3(cm['opus'])} s, sonnet {f3(cm['sonnet'])} s. Caution: the truth was built from the markers (where both agreed, their mean; "
          "elsewhere the developer chose after seeing their marks), so it favours the markers; S7's numbers here are a fair floor, the markers' "
          "numbers a flattering ceiling. Medians over n=1 (first_knee_max, deepest_rebend: S7 gives these borders rarely) say little."]
    # ---- how
    srcs = [ref["clips"][r["clip"]][r["attempt"]][r["border"]]["source"] for r in rows if r["true"] is not None]
    n_h, n_m = srcs.count("human"), srcs.count("markers agree")
    L += ["", "## How this test works", "",
          f"Two agent markers (opus, sonnet) each marked all {len(ph.BORDERS)} borders of every attempt blind: they saw only raw-frame strips "
          "of the clip (no pipeline output, no code, no S7 result) and wrote a frame per border or null. S7 ran on the same clips. "
          "Truth per border: where the two markers agreed within the tolerance, the mean of their frames (`markers agree`, "
          f"{n_m} borders with a true frame); where they disagreed, or agreed and S7 was off, the developer looked at the frames on a blind review page "
          f"(S7's value not shown) and picked the true frame or said the border does not exist (`human`, {n_h} borders with a true frame; "
          "null truths are counted among the human verdicts). Tolerance per border in seconds of frame time: "
          + ", ".join(f"{n} {tol[n]:g}" for n in ph.BORDERS) + ". A border passes when both truth and S7 are null, or both are frames within the tolerance; "
          "S7 giving a border the truth does not have (or the reverse) is a fail.", "",
          "Limits: one lifter, 6 clips (T1, T2, T3, T6, T7, T8), 7 attempts (T1 = T8 attempt 1, the same frames, so effectively 6 distinct), "
          "so a handful of cases per border, not statistics. The human picked from strips, some at every 2nd frame, so a true frame can be 1 frame off "
          "(0.004 s at 240 fps, small against every tolerance). `markers agree` items were not seen by the human: if both markers share a bias, "
          "the truth carries it, and it favours the markers in question 2. No clip has a different lifter, camera angle or a lift that fails past the pull. "
          "Nobody tunes S7 to pass this: a no is reported as a no, and the check in `check_pipeline.py` only fails when a border that passed "
          "before stops passing (`passing` in `prototype/tests/data/s7_reference.json`)."]
    path.write_text("\n".join(L) + "\n")


def main(root: Path) -> None:
    ref = json.loads(S7_REFERENCE.read_text())
    out_dir = root / "proof/S7"
    key = sha(S7_REFERENCE.read_bytes(), *(clip_dir(root, c).joinpath("phases.json").read_bytes() for c in ref["clips"]),
              *(p.read_bytes() for p in sorted(MARKS.glob("*_[AB].json"))), Path(__file__).read_bytes(), inspect.getsource(s7_errors).encode())
    hit = CACHE / key
    if (hit / "verdict.md").is_file():
        log(f"cached {key}")
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.copytree(hit, out_dir)
        return
    data = collect(root, ref)
    tmp = CACHE / f"{key}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    dot_chart(data, tmp / "1_error_dots.png")
    names = strips(data, root, tmp)
    write_verdict(tmp / "verdict.md", data, ref, names)
    shutil.rmtree(hit, ignore_errors=True)
    tmp.rename(hit)
    shutil.rmtree(out_dir, ignore_errors=True)
    shutil.copytree(hit, out_dir)
    log(f"wrote {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
