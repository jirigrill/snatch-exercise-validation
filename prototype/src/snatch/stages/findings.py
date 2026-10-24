"""S9: bar-path metrics per attempt (snatch.findings; rules in .scratch/plan/D-judge.md, "S9 findings").

Reads phases.json (S7 borders, phases, window), judgement.json (S8; one record per attempt, read so a verdict change
reruns S9), plate.npz (hub track, px_per_m), facing.json (x sign) and the athlete's athlete.json (height_m).

- findings.json: {attempts: [{attempt, findings: [] (no rules yet), metrics {name: {value, value_px, unit, frames,
  at, missing}}}]}. value null when a border is missing or the span has no found plate frame (missing names it), or (cm, %) when
  the window has no found plate frame to give px_per_m; value_px kept otherwise.
- findings_sheet.jpg: a row per attempt; the liftoff frame cropped around the hub path, the hub trail over the
  window coloured by S7 phase, each metric as a labelled arrow (x metrics horizontal at the arrow-tip frame,
  height metrics vertical) with its value; a text tile lists all 6 (or the missing borders).
"""

import json
from pathlib import Path

import cv2
import numpy as np

from snatch.findings import METRICS, Track, metrics
from snatch.stage import ATHLETE, CLIP, Context, Stage
from snatch.video import frames, probe

TILE_H = 700
PHASE_BGR = ((180, 180, 180), (225, 160, 60), (90, 200, 90), (60, 160, 250), (80, 80, 240), (200, 120, 200),
             (120, 220, 220), (240, 200, 160))
ARROW_BGR = {"pull1_away_cm": (0, 255, 255), "pull2_toward_cm": (255, 0, 255), "loop_away_cm": (0, 128, 255),
             "peak_height_pct": (0, 255, 0), "drop_under_cm": (255, 255, 0), "catch_x_cm": (255, 255, 255)}


def track_of(plate: dict) -> Track:
    return Track(np.asarray(plate["hub_x"], float), np.asarray(plate["hub_y"], float),
                 np.asarray(plate["found"], bool), np.asarray(plate["px_per_m"], float))


def fmt(m: dict) -> str:
    if m["value"] is None:
        return f"- (missing {','.join(m['missing'])})" if m["missing"] else f"- ({m['value_px']} px, no px_per_m in window)"
    return f"{m['value']:+.1f} {m['unit']}"


def _put(img: np.ndarray, s: str, xy: tuple[int, int], col: tuple[int, int, int], sc: float = 0.6) -> None:
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, sc, (0, 0, 0), 4)
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1)


def _row(img: np.ndarray, rec: dict, ms: dict, tr: Track, verdict: str) -> np.ndarray:
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
        if name in ("peak_height_pct", "drop_under_cm"):
            ax = int(tr.hub_x[at] - x0) + (60 if name == "peak_height_pct" else -60)
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
    return np.hstack([g, info])


def run(ctx: Context, tmp: Path) -> None:
    recs = json.loads(ctx.path("phases.json").read_text())["attempts"]
    judged = {j["attempt"]: j for j in json.loads(ctx.path("judgement.json").read_text())["attempts"]}
    plate = dict(np.load(ctx.path("plate.npz")))
    tr = track_of(plate)
    sign = 1 if json.loads(ctx.path("facing.json").read_text())["facing"] == "right" else -1
    height = float(json.loads(ctx.path(ATHLETE).read_text())["height_m"])
    out = [dict(attempt=r["attempt"], findings=[], metrics=metrics(r, tr, sign, height)) for r in recs]
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
        rows.append(_row(imgs[lift[r["attempt"]]], r, o["metrics"], tr,
                         f"{j.get('performed_type')}: {j.get('lift_result')} {j.get('reason') or ''}"))
    w = max(x.shape[1] for x in rows)
    rows = [np.pad(x, ((0, 0), (0, w - x.shape[1]), (0, 0))) for x in rows]
    cv2.imwrite(str(tmp / "findings_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])


STAGE = Stage("S9", (CLIP, "phases.json", "judgement.json", "plate.npz", "facing.json", ATHLETE),
              ("findings.json", "findings_sheet.jpg"), run)
