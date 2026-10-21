"""Compare blind marker frames with S7 phase borders; build a blind review page for the disputed ones.

Run from prototype/:
  uv run python ../.claude/skills/verify/scripts/s7_marks_review.py ROOT OUT_DIR

ROOT   = S7 run root (dirs T<n>_*/ with phases.json, frame_times.npy)
OUT_DIR gets: review.html (+ img/), key.json (letter -> source, per item; keep it away from the
              human), items.json (every item: candidates, status, tolerance, agreed frame).
Marks: .scratch/s7-marks/{opus,sonnet}_{A,B}.json; borders and crops from marks/BRIEF.md.
T8 attempt 1 = same frames as T1: merged into one item "T1 = T8 a1" (id T1-<border>).
"""

import html
import json
import random
import re
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import mark_strips  # noqa: E402
from snatch import video  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
MARKS = REPO / ".scratch/s7-marks"
BORDERS = ["liftoff", "first_knee_max", "deepest_rebend", "full_extension", "bar_peak", "bar_lowest", "standing"]
TOL = {"liftoff": 0.03, "bar_peak": 0.03, "bar_lowest": 0.03,
       "first_knee_max": 0.05, "deepest_rebend": 0.05, "full_extension": 0.05, "standing": 0.10}
COLORS = [(0, 0, 255), (0, 200, 0), (255, 120, 0), (0, 200, 255), (255, 0, 255), (200, 200, 0)]  # BGR
COLOR_NAMES = ["red", "green", "blue", "yellow", "magenta", "cyan"]
CELL_W = 260
SEED = 7
PAD = 8


def parse_brief() -> tuple[dict[str, str], dict[tuple[str, str], tuple[int, ...]]]:
    text = (MARKS / "BRIEF.md").read_text()
    defs = {m.group(1): m.group(2).strip() for m in re.finditer(r"^\d\. `(\w+)`: (.+)$", text, re.M)}
    crops = {}
    for m in re.finditer(r"^\| (T\d) \| (\d) \| [\d–]+ \| ([\d,]+) \|$", text, re.M):
        crops[(m.group(1), m.group(2))] = tuple(int(v) for v in m.group(3).split(","))
    return defs, crops


def load_marks() -> dict[str, dict]:
    out: dict[str, dict] = {"opus": {}, "sonnet": {}}
    for who in out:
        for grp in "AB":
            p = MARKS / f"{who}_{grp}.json"
            if p.exists():
                out[who].update(json.loads(p.read_text()))
    return out


def load_s7(root: Path) -> dict[str, dict]:
    res = {}
    for clip in ("T1", "T2", "T3", "T6", "T7", "T8"):
        d = next((x for x in sorted(root.glob(f"{clip}_*")) if x.is_dir()), root / f"{clip}_missing")
        if not (d / "phases.json").exists():
            # S7 did not run for this clip: no S7 candidate, times from the video's fps
            print(f"WARNING: no phases.json for {clip}: S7 left out of its items", file=sys.stderr)
            info = video.probe(str(next((REPO / "vids/test").glob(f"{clip}_*.MOV"))))
            res[clip] = {"times": np.arange(info.n_frames + 1) / info.fps, "attempts": None}
            continue
        ph = json.loads((d / "phases.json").read_text())
        res[clip] = {
            "times": np.load(d / "frame_times.npy"),
            "attempts": {str(a["attempt"]): a["borders"] for a in ph["attempts"]},
        }
    return res


def marker_frame(marks, who, clip, att, border):
    b = marks[who].get(clip, {}).get(att, {}).get(border)
    return None if b is None or b.get("frame") is None else int(b["frame"])


def build_items(marks, s7):
    """One dict per (clip, attempt, border); T8 a1 merged into T1."""
    items = []
    for clip, att in [("T1", "1"), ("T2", "1"), ("T3", "1"), ("T6", "1"), ("T7", "1"), ("T8", "2")]:
        for border in BORDERS:
            items.append((clip, att, border, f"{clip}-{border}" if clip != "T8" else f"T8a2-{border}",
                          f"{clip} a{att}" if clip != "T1" else "T1 = T8 a1"))
    out = []
    for clip, att, border, iid, label in items:
        cands = []  # (source, clip, frame|None)
        for who in ("opus", "sonnet"):
            cands.append((f"{who} {clip}", clip, marker_frame(marks, who, clip, att, border)))
        if (clip, att) == ("T1", "1"):
            for who in ("opus", "sonnet"):
                cands.append((f"{who} T8", "T8", marker_frame(marks, who, "T8", "1", border)))
        if s7[clip]["attempts"] is not None:
            sb = s7[clip]["attempts"].get(att, {}).get(border)
            cands.append(("S7", clip, None if sb is None else int(sb["frame"])))
        out.append({"id": iid, "clip": clip, "attempt": att, "border": border, "label": label,
                    "tol": TOL[border], "cands": cands})
    return out


def judge(item, s7):
    times = {c: s7[c]["times"] for c in s7}
    tol = item["tol"]
    markers = [(s, c, f) for s, c, f in item["cands"] if s != "S7"]
    s7c = next(((s, c, f) for s, c, f in item["cands"] if s == "S7"), None)
    nn = [(c, f) for _, c, f in markers if f is not None]
    nulls = len(markers) - len(nn)

    def t(c, f):
        return float(times[c][f])

    reasons = []
    mean_frame = None
    if nn and nulls:
        reasons.append("marker null vs frame")
    if len(nn) >= 2:
        ts = [t(c, f) for c, f in nn]
        if max(ts) - min(ts) > tol:
            reasons.append("markers disagree")
    if not reasons:
        if nn:
            mean_frame = round(statistics.mean(f for _, f in nn))
            mt = statistics.mean(t(c, f) for c, f in nn)
            if s7c is None:
                pass
            elif s7c[2] is None:
                reasons.append("markers agree, S7 null")
            elif abs(t(s7c[1], s7c[2]) - mt) > tol:
                reasons.append("markers agree, S7 off")
        elif s7c is not None and s7c[2] is not None:
            reasons.append("markers agree null, S7 has a frame")
    item["status"] = "human" if reasons else "agreed"
    item["reasons"] = reasons
    item["agreed_frame"] = None if reasons else mean_frame  # null-agreed => None
    item["agreed_null"] = (not reasons) and not nn
    return item


def frame_list(cand_frames, n_frames, cap=48):
    """Candidates always in; range +-PAD clamped to the clip; at most `cap` cells."""
    lo, hi = max(0, min(cand_frames) - PAD), min(n_frames - 1, max(cand_frames) + PAD)
    n = hi - lo + 1
    k = len(set(cand_frames))
    step = 1 if n <= cap else -(-n // (cap - k))  # grid cells + candidates off the grid <= cap
    return sorted(set(range(lo, hi + 1, step)) | set(cand_frames))


def n_frames(clip, s7):
    """Real frame count: frame_times.npy length (S7 ran), else decode-count like the pipeline."""
    if s7[clip]["attempts"] is not None:
        return len(s7[clip]["times"])
    path = str(next((REPO / "vids/test").glob(f"{clip}_*.MOV")))
    return sum(1 for _ in video.frames(path))


def render_images(items, s7, crops, out_dir, rng):
    """Decode each clip once up to the largest needed frame; draw one image per human item."""
    key = {}
    need = {}  # clip -> {item id: frames}
    for it in items:
        if it["status"] != "human":
            continue
        # letters: shuffled, fixed seed
        letters = [chr(65 + i) for i in range(len(it["cands"]))]
        rng.shuffle(letters)
        it["letters"] = letters
        key[it["id"]] = {l: s for l, (s, _, _) in zip(letters, it["cands"])}
        # frames per candidate clip are identical for T1/T8 merge; draw from T1 video
        fr = [f for _, _, f in it["cands"] if f is not None]
        it["strip_frames"] = frame_list(fr, n_frames(it["clip"], s7))
        need.setdefault(it["clip"], []).append(it)
    img_dir = out_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    for clip, its in need.items():
        path = next((REPO / "vids/test").glob(f"{clip}_*.MOV"))
        x0, y0, x1, y1 = crops[(clip, its[0]["attempt"])]
        wanted = set().union(*(set(i["strip_frames"]) for i in its))
        cells = {}
        for i, fr in enumerate(video.frames(str(path), stop=max(wanted) + 1)):
            if i in wanted:
                c = fr[y0:y1, x0:x1]
                s = CELL_W / c.shape[1]
                cells[i] = cv2.resize(c, (CELL_W, round(c.shape[0] * s)), interpolation=cv2.INTER_AREA)
        for it in its:
            cols = 8
            miss = [f for f in it["strip_frames"] if f not in cells]
            if miss:
                print(f"WARNING: {it['id']}: frames {miss} not in the video ({len(cells)} decoded); dropped", file=sys.stderr)
            frames = [f for f in it["strip_frames"] if f in cells]
            h, w = cells[frames[0]].shape[:2]
            rows = -(-len(frames) // cols)
            sheet = np.zeros((h * rows, w * cols, 3), np.uint8)
            by_frame: dict[int, list[int]] = {}
            for k, (_, _, f) in enumerate(it["cands"]):
                if f is not None:
                    by_frame.setdefault(f, []).append(k)
            for n, f in enumerate(frames):
                cell = cells[f].copy()
                for depth, k in enumerate(by_frame.get(f, [])):
                    t = 5 * (depth + 1) + 2 * depth
                    col = COLORS[k % len(COLORS)]
                    cv2.rectangle(cell, (t // 2, t // 2), (w - 1 - t // 2, h - 1 - t // 2), col, 5)
                mark_strips.label(cell, f"f{f}")
                # letters banner at the bottom, in candidate colours
                for depth, k in enumerate(by_frame.get(f, [])):
                    col = COLORS[k % len(COLORS)]
                    txt = it["letters"][k]
                    x = 8 + depth * 52
                    cv2.rectangle(cell, (x, h - 58), (x + 46, h - 8), col, -1)
                    cv2.putText(cell, txt, (x + 8, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 4, cv2.LINE_AA)
                r, c = divmod(n, cols)
                sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = cell
                cv2.rectangle(sheet, (c * w, r * h), ((c + 1) * w - 1, (r + 1) * h - 1), (60, 60, 60), 1)
            name = f"{it['id']}.jpg"
            cv2.imwrite(str(img_dir / name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
            it["image"] = f"img/{name}"
    return key


def write_html(items, defs, out_dir):
    hum = [i for i in items if i["status"] == "human"]
    parts = ["<!doctype html><meta charset=utf-8><title>S7 borders review</title>",
             "<style>body{font:15px sans-serif;max-width:1700px;margin:20px auto;padding:0 16px}"
             "img{max-width:100%;border:1px solid #888}h2{margin-top:36px;border-top:2px solid #444;padding-top:10px}"
             ".sw{display:inline-block;width:14px;height:14px;margin-right:4px;vertical-align:middle}</style>",
             "<h1>S7 phase borders: blind review</h1>",
             f"<p>{len(hum)} items. Each strip shows frames (frame number top-left; a coloured outline plus lettered "
             "tag marks a candidate). You do not know who proposed which letter.</p>",
             "<p><b>How to answer:</b> reply one line per item, like <code>T1-liftoff f268</code> or "
             "<code>T7-full_extension none</code> (the border does not exist). Any frame on the strip is fine, "
             "not only a candidate.</p>"]
    for it in hum:
        letters = it["letters"]
        cl = []
        for k, (_, _, f) in enumerate(it["cands"]):
            col = COLORS[k % len(COLORS)]
            sw = f"<span class=sw style='background:rgb({col[2]},{col[1]},{col[0]})'></span>"
            cl.append((letters[k], f"{sw}{letters[k]}: " + (f"f{f}" if f is not None else "none")))
        cl.sort()
        parts.append(f"<h2 id='{it['id']}'>{html.escape(it['id'])} <small>({html.escape(it['label'])})</small></h2>")
        parts.append(f"<p><b>{it['border']}</b>: {html.escape(defs[it['border']])}</p>")
        parts.append(f"<p>Candidates: {',&nbsp; '.join(s for _, s in cl)}</p>")
        parts.append(f"<img src='{it['image']}' loading=lazy>")
    (out_dir / "review.html").write_text("\n".join(parts))


def main() -> None:
    root, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    defs, crops = parse_brief()
    marks, s7 = load_marks(), load_s7(root)
    items = [judge(i, s7) for i in build_items(marks, s7)]
    key = render_images(items, s7, crops, out_dir, random.Random(SEED))
    (out_dir / "key.json").write_text(json.dumps(key, indent=1))
    write_html(items, defs, out_dir)
    dump = [{"id": i["id"], "clip": i["clip"], "attempt": i["attempt"], "border": i["border"],
             "label": i["label"], "tol": i["tol"], "status": i["status"], "reasons": i["reasons"],
             "agreed_frame": i["agreed_frame"], "agreed_null": i["agreed_null"],
             "candidates": [{"source": s, "clip": c, "frame": f} for s, c, f in i["cands"]]} for i in items]
    (out_dir / "items.json").write_text(json.dumps(dump, indent=1))
    n_h = sum(i["status"] == "human" for i in items)
    print(f"items {len(items)}: human {n_h}, agreed {len(items) - n_h} -> {out_dir}")


if __name__ == "__main__":
    main()
