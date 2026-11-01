"""S9: bar-path metrics per attempt (snatch.findings; rules in .scratch/plan/D-judge.md, "S9 findings").

Reads phases.json (S7 borders, phases, window), judgement.json (S8; one record per attempt, read so a verdict change
reruns S9), plate.npz (hub track, px_per_m), facing.json (x sign) and the athlete's athlete.json (height_m).

- findings.json: {attempts: [{attempt, findings, checked, skipped, metrics {name: {value, value_px, unit, frames,
  at, missing}}}]}. value null when a border is missing or the span has no found plate frame (missing names it), or (cm, %) when
  the window has no found plate frame to give px_per_m; value_px kept otherwise.
- findings_sheet.jpg: a row per attempt; the liftoff frame cropped around the hub path, the hub trail over the
  window coloured by S7 phase, each metric as a labelled arrow (x metrics horizontal at the arrow-tip frame,
  height metrics vertical) with its value; a text tile lists all 8 (or the missing borders) and the fault tile
  lists every fault found / ok / skipped with its value and threshold.
"""

import json
from pathlib import Path

import cv2
import numpy as np

from snatch import overlay
from snatch.findings import FAULTS, METRICS, Body, Track, metrics, rules
from snatch.pose import HALPE26, SIDE_OF
from snatch.stage import ATHLETE, CLIP, Context, Stage
from snatch.video import frames, probe

TILE_H = 700
OVERLAY = "overlays/9_findings.mp4"
FAULT_BGR = (0, 0, 255)  # red: a fault label
PHASE_BGR = ((180, 180, 180), (225, 160, 60), (90, 200, 90), (60, 160, 250), (80, 80, 240), (200, 120, 200),
             (120, 220, 220), (240, 200, 160))
ARROW_BGR = {"pull1_away_cm": (0, 255, 255), "pull2_toward_cm": (255, 0, 255), "loop_away_cm": (0, 128, 255),
             "peak_height_pct": (0, 255, 0), "peak_rise_pct": (128, 255, 0), "drop_under_cm": (255, 255, 0),
             "catch_x_cm": (255, 255, 255), "net_x_cm": (255, 128, 0)}


def track_of(plate: dict) -> Track:
    return Track(np.asarray(plate["hub_x"], float), np.asarray(plate["hub_y"], float),
                 np.asarray(plate["found"], bool), np.asarray(plate["px_per_m"], float),
                 float(plate["plate_diameter_m"]))


def body_of(pose: dict, side: str) -> Body:
    """Near shoulder / hip of the S6 pose with why each is unsure (S6 filled mask, else hidden mask)."""
    kp, fl, hd = np.asarray(pose["keypoints"], float), np.asarray(pose["filled"], bool), np.asarray(pose["hidden"], bool)
    def why(j: int) -> list[str]:
        return ["filled" if f else "hidden" if h else "" for f, h in zip(fl[:, j], hd[:, j])]
    sh, hp = HALPE26[f"{side}_shoulder"], HALPE26[f"{side}_hip"]
    return Body(kp[:, sh], kp[:, hp], why(sh), why(hp), np.asarray(pose["t"], float))


def fmt(m: dict) -> str:
    if m["value"] is None:
        return f"- (missing {','.join(m['missing'])})" if m["missing"] else f"- ({m['value_px']} px, no px_per_m in window)"
    return f"{m['value']:+.1f} {m['unit']}"


def cmp_text(fault: str, threshold: float | list[float], found: bool = True) -> str:
    """The rule's comparison, true for the row: found rows state the fault, ok rows its complement."""
    if fault == "bad_start_back_angle":
        assert isinstance(threshold, list)
        return f"{'outside' if found else 'inside'} {threshold[0]:g}..{threshold[1]:g}"
    t = threshold[0] if isinstance(threshold, list) else threshold
    if fault == "shoulders_behind_bar":
        return f"< {t:g}" if found else f">= {t:g}"
    return f"> {t:g}" if found else f"<= {t:g}"


def _put(img: np.ndarray, s: str, xy: tuple[int, int], col: tuple[int, int, int], sc: float = 0.6) -> None:
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, sc, (0, 0, 0), 4)
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1)


def _row(img: np.ndarray, rec: dict, o: dict, tr: Track, verdict: str) -> np.ndarray:
    ms = o["metrics"]
    s, e = rec["window"]
    idx = [i for i in range(s, e) if tr.found[i]]
    xs, ys = tr.hub_x[idx], tr.hub_y[idx]
    h_img, w_img = img.shape[:2]
    m = 250
    x0, y0 = max(0, int(xs.min()) - m), max(0, int(ys.min()) - m)
    x1, y1 = min(w_img, int(xs.max()) + m), min(h_img, int(ys.max()) + m)
    g = img[y0:y1, x0:x1].copy()
    p = lambda i: (int(tr.hub_x[i] - x0), int(tr.hub_y[i] - y0))  # noqa: E731
    phase_of = {}
    for k, ph in enumerate(rec["phases"]):
        if ph["start"] is not None and ph["end"] is not None:
            for i in range(ph["start"], ph["end"]):
                phase_of[i] = k
    for a, b in zip(idx, idx[1:]):
        if b == a + 1:
            cv2.line(g, p(a), p(b), PHASE_BGR[phase_of.get(a, 0) % len(PHASE_BGR)], 3)
    for k, (name, mt) in enumerate(ms.items()):
        if mt["value_px"] is None or mt["at"] is None:
            continue
        col, (fs, _) = ARROW_BGR[name], mt["frames"]
        at, unit = mt["at"], METRICS[name][0]
        if name in ("peak_height_pct", "peak_rise_pct", "drop_under_cm"):
            ax = int(tr.hub_x[at] - x0) + {"peak_height_pct": 60, "peak_rise_pct": 120, "drop_under_cm": -60}[name]
            a, b = (ax, int(tr.hub_y[fs] - y0)), (ax, int(tr.hub_y[at] - y0))
        else:
            ay = int(tr.hub_y[at] - y0)
            a, b = (int(tr.hub_x[fs] - x0), ay), (int(tr.hub_x[at] - x0), ay)
            cv2.line(g, (a[0], ay), p(fs), col, 1)
        cv2.arrowedLine(g, a, b, col, 3, tipLength=0.2)
        cv2.circle(g, p(at), 6, col, -1)
        _put(g, f"{k + 1} {mt['value']:+.1f}{unit}" if mt["value"] is not None else f"{k + 1} {mt['value_px']:+.0f}px",
             (b[0] + 8, b[1] + 18 * (k % 2)), col, 0.8)
    sc = TILE_H / g.shape[0]
    g = cv2.resize(g, (max(1, int(g.shape[1] * sc)), TILE_H), interpolation=cv2.INTER_AREA)
    info = np.full((TILE_H, 420, 3), 30, np.uint8)
    _put(info, f"a{rec['attempt']} {verdict}", (8, 28), (255, 255, 255), 0.7)
    for k, (name, mt) in enumerate(ms.items()):
        fr = f" f{mt['frames'][0]}-{mt['frames'][1]} @{mt['at']}" if mt["at"] is not None else ""
        _put(info, f"{k + 1} {name}", (8, 70 + 60 * k), ARROW_BGR[name], 0.6)
        _put(info, f"   {fmt(mt)}{fr}", (8, 95 + 60 * k), (230, 230, 230), 0.5)
    y = 70 + 60 * len(ms) + 20
    for k, ph in enumerate(rec["phases"]):
        _put(info, ph["name"], (8 + 140 * (k % 3), y + 24 * (k // 3)), PHASE_BGR[k % len(PHASE_BGR)], 0.5)
    return np.hstack([g, info, fault_tile(o)])


def fault_tile(o: dict) -> np.ndarray:
    """Every fault: FOUND (red) / ok (green) with value vs threshold and evidence frames, or skipped (grey) + reason."""
    t = np.full((TILE_H, 560, 3), 20, np.uint8)
    _put(t, f"faults: {len(o['findings'])} found", (8, 28), (255, 255, 255), 0.7)
    ck = {c["fault"]: c for c in o["checked"]}
    sk = {c["fault"]: c for c in o["skipped"]}
    ev = {f["fault"]: f["evidence_frames"] for f in o["findings"]}
    for k, f in enumerate(FAULTS):
        y = 70 + 66 * k
        if f in ck:
            c = ck[f]
            col = FAULT_BGR if c["found"] else (90, 200, 90)
            _put(t, f"{'FOUND' if c['found'] else 'ok'} {f}", (8, y), col, 0.6)
            ev_s = f" @f{','.join(map(str, ev[f]))}" if f in ev else ""
            _put(t, f"   {c['value']:g} {cmp_text(f, c['threshold'], c['found'])} {c['unit']}{ev_s}",
                 (8, y + 24), (230, 230, 230), 0.5)
        else:
            _put(t, f"skipped {f}", (8, y), (150, 150, 150), 0.6)
            _put(t, f"   {sk[f]['reason']}"[:60], (8, y + 24), (150, 150, 150), 0.5)
    return t


def run(ctx: Context, tmp: Path) -> None:
    recs = json.loads(ctx.path("phases.json").read_text())["attempts"]
    judged = {j["attempt"]: j for j in json.loads(ctx.path("judgement.json").read_text())["attempts"]}
    plate = dict(np.load(ctx.path("plate.npz")))
    tr = track_of(plate)
    sign = 1 if json.loads(ctx.path("facing.json").read_text())["facing"] == "right" else -1
    height = float(json.loads(ctx.path(ATHLETE).read_text())["height_m"])
    side = SIDE_OF[json.loads(ctx.path("facing.json").read_text())["facing"]]
    body = body_of(dict(np.load(ctx.path("pose.npz"))), side)
    out = []
    for r in recs:
        ms = metrics(r, tr, sign, height)
        fs, ck, sk = rules(r, ms, tr, body, sign, height)
        out.append(dict(attempt=r["attempt"], findings=fs, checked=ck, skipped=sk, metrics=ms))
    (tmp / "findings.json").write_text(json.dumps(dict(attempts=out), indent=2) + "\n")

    clip = str(ctx.clip)
    info = probe(clip)
    lift = {r["attempt"]: (r["borders"]["liftoff"] or {"frame": r["window"][0]})["frame"] for r in recs}
    imgs: dict[int, np.ndarray] = {}
    for i, img in enumerate(frames(clip, info, stop=max(lift.values()) + 1)):
        if i in lift.values():
            imgs[i] = img
    rows = []
    for r, o in zip(recs, out):
        j = judged.get(r["attempt"], {})
        rows.append(_row(imgs[lift[r["attempt"]]], r, o, tr,
                         f"{j.get('performed_type')}: {j.get('lift_result')} {j.get('reason') or ''}"))
    w = max(x.shape[1] for x in rows)
    rows = [np.pad(x, ((0, 0), (0, w - x.shape[1]), (0, 0))) for x in rows]
    cv2.imwrite(str(tmp / "findings_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    write_video(ctx, tmp, recs, out, plate)


def write_video(ctx: Context, tmp: Path, recs: list[dict], out: list[dict], plate: dict) -> None:
    """9_findings.mp4: attempt windows, every 4th frame plus every evidence frame; plate + hub trail (overlay); each
    finding's label in the frame's label lines from its first to its last evidence frame (+0.5 s)."""
    t = np.asarray(plate["t"], float)
    shows: list[tuple[int, int, str]] = []
    for o in out:
        for f in o["findings"]:
            a, z = min(f["evidence_frames"]), max(f["evidence_frames"])
            z = int(np.searchsorted(t, t[z] + 0.5))
            shows.append((a, z, f"{f['fault']} {f['value']:g} ({cmp_text(f['fault'], f['threshold'])})"))
    extra = sorted({e for o in out for f in o["findings"] for e in f["evidence_frames"]})
    win = {i: r["attempt"] for r in recs for i in range(r["window"][0], r["window"][1])}
    pose = dict(np.load(ctx.path("pose.npz")))

    def labels_at(i: int) -> list[str]:
        a = win.get(i)
        if a is None:
            return ["outside attempts"]
        o = next(x for x in out if x["attempt"] == a)
        live = [s for a0, z, s in shows if a0 <= i <= z]
        return [f"attempt {a}: {len(o['findings'])} fault(s), {len(o['skipped'])} skipped", *live]

    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    s0, e0 = min(r["window"][0] for r in recs), max(r["window"][1] for r in recs)
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), poses=[{"keypoints": pose["keypoints"]}], plate=plate,
                   start=s0, end=e0, step=4, zoom=True, scale=1.0, extra=extra, frame_labels=labels_at,
                   dim=np.array([i not in win for i in range(len(t))]))


STAGE = Stage("S9", (CLIP, "phases.json", "judgement.json", "plate.npz", "pose.npz", "facing.json", ATHLETE),
              ("findings.json", "findings_sheet.jpg", OVERLAY), run, version=3)
