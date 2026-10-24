"""S8: judge each attempt (snatch.judge; rules in .scratch/plan/D-judge.md, "S8 judge").

Reads phases.json + angles.csv (S7), pose.npz (near hip / knee y, shoulder x, S6 filled / hidden masks), plate.npz
(hub for the sheet, found per frame), facing.json and labels.csv (the repo's; intended_type of this clip's attempt, an
empty one = no label). The `intended` param (--intended) overrides the label.

- judgement.json: {attempts: [one record per attempt: performed_type, intended_type, intended_source, lift_result,
  reason, evidence_frames, checks {name: {value, threshold, unit, result, frames, worst, ...}}], params}.
- judgement_sheet.jpg: a row per attempt; tiles at bar_lowest, standing, mid-hold (S7 hold phase), bar_overhead end (grey = border
  missing), each with the verdict and the check values; a tile that is a check's worst frame says so in yellow.
  A final text tile lists every check (result, value / threshold).
- overlays/8_judgement.mp4: the attempt windows, every 4th frame; type + verdict on each frame; from bar_overhead
  end (or the window's last 0.5 s without it; every check's worst frame is drawn too) to the window end a big COMPLETED (green) / FAILED reason (red) /
  UNKNOWN (grey) banner.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from snatch import overlay
from snatch.judge import CHECKS, PARAMS, Signals, judge
from snatch.pose import HALPE26, SIDE_OF
from snatch.stage import CLIP, LABELS, Context, Stage
from snatch.video import frames, probe

OVERLAY = "overlays/8_judgement.mp4"
TILE = (300, 400)  # w x h
COLOR = {"completed": (0, 180, 0), "failed": (0, 0, 220), "unknown": (150, 150, 150)}  # BGR
SHEET_FRAMES = ("bar_lowest", "standing", "mid_hold", "overhead_end")


def labels_for(path: Path, clip: str) -> dict[int, str]:
    """{attempt: intended_type} of this clip; an empty intended_type is no label."""
    with path.open() as f:
        return {int(r["attempt"]): r["intended_type"] for r in csv.DictReader(f) if r["clip"] == clip and r["intended_type"]}


def signals(ctx: Context) -> Signals:
    pose = np.load(ctx.path("pose.npz"))
    plate = np.load(ctx.path("plate.npz"))
    side = SIDE_OF[json.loads(ctx.path("facing.json").read_text())["facing"]]
    kp = np.asarray(pose["keypoints"], float)
    n = len(kp)
    knee, elbow, hidden = np.full(n, np.nan), np.full(n, np.nan), np.ones(n, bool)
    with ctx.path("angles.csv").open() as f:
        for r in csv.DictReader(f):
            i = int(r["frame"])
            knee[i], elbow[i], hidden[i] = float(r["knee"]), float(r["elbow"]), r["wrist_hidden"] == "1"
    legs = [HALPE26[f"{side}_hip"], HALPE26[f"{side}_knee"]]
    unsure = (np.asarray(pose["filled"], bool)[:, legs] | np.asarray(pose["hidden"], bool)[:, legs]).any(1)
    j = lambda name: kp[:, HALPE26[f"{side}_{name}"]]  # noqa: E731
    return Signals(t=np.asarray(pose["t"], float), knee=knee, elbow=elbow, wrist_hidden=hidden, leg_unsure=unsure,
                   hip_y=j("hip")[:, 1], knee_y=j("knee")[:, 1],
                   plate_found=np.asarray(plate["found"], bool))


def fmt(name: str, c: dict) -> str:
    v = c["value"]
    if name == "type_mismatch" and c["result"] != "skipped":
        return f"{c['performed']} vs {c['intended']}"
    if name == "low_confidence":
        return ",".join(c["unsure"]) or "-"
    if v is None:
        return "-"
    return f"{v:.2f}/{c['threshold']:g}{c['unit']}"


def verdict(j: dict) -> str:
    return f"{j['performed_type']}: {j['lift_result'].upper()}" + (f" {j['reason']}" if j["reason"] else "")


def sheet_frames(rec: dict) -> dict[str, int | None]:
    b, oh = rec["borders"], rec["bar_overhead"]
    low = b["bar_lowest"]["frame"] if b.get("bar_lowest") else None
    stand = b["standing"]["frame"] if b.get("standing") else None
    end = int(oh["end"]) - 1 if oh else None
    hp = {p["name"]: p for p in rec["phases"]}.get("hold")
    hold_end = int(hp["end"]) - 1 if hp and hp["end"] is not None and stand is not None else end
    mid = (stand + hold_end) // 2 if stand is not None and hold_end is not None else None
    return dict(bar_lowest=low, standing=stand, mid_hold=mid, overhead_end=end)


def _text(img: np.ndarray, lines: list[tuple[str, tuple[int, int, int]]], y: int = 22, sc: float = 0.5) -> None:
    for s, col in lines:
        cv2.putText(img, s, (6, y), cv2.FONT_HERSHEY_SIMPLEX, sc, (0, 0, 0), 4)
        cv2.putText(img, s, (6, y), cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1)
        y += int(22 * sc / 0.5)


def write_sheet(path: Path, clip: str, recs: list[dict], judged: list[dict], kp: np.ndarray, plate: dict) -> None:
    info = probe(clip)
    w, h = TILE
    want = {a: sheet_frames(r) for a, r in enumerate(recs)}
    need = sorted({f for d in want.values() for f in d.values() if f is not None})
    imgs: dict[int, np.ndarray] = {}
    if need:
        for i, img in enumerate(frames(clip, info, stop=need[-1] + 1)):
            if i in need:
                imgs[i] = img
    rows = []
    for a, (r, j) in enumerate(zip(recs, judged)):
        fs = [f for f in want[a].values() if f is not None]
        box = None
        if fs:
            pts = np.concatenate([kp[fs].reshape(-1, 2), np.column_stack([plate["hub_x"][fs], plate["hub_y"][fs]])])
            pts = pts[np.isfinite(pts).all(1)]
            (x0, y0), (x1, y1) = pts.min(0), pts.max(0)
            m = 0.3 * max(x1 - x0, y1 - y0)
            box = (max(0, int(x0 - m)), max(0, int(y0 - m)), min(info.width, int(x1 + m)), min(info.height, int(y1 + m)))
        col = COLOR[j["lift_result"]]
        head = [(f"a{j['attempt']} {verdict(j)}", col)]
        row = []
        for name, f in want[a].items():
            tile = np.full((h, w, 3), 110, np.uint8)  # grey = border missing
            if f is None or box is None:
                _text(tile, head + [(f"{name}: none", (255, 255, 255))])
            else:
                x0, y0, x1, y1 = box
                g = imgs[f][y0:y1, x0:x1].copy()
                cv2.circle(g, (int(plate["hub_x"][f] - x0), int(plate["hub_y"][f] - y0)), 10, (0, 0, 255), -1)
                sc = min(w / g.shape[1], h / g.shape[0])
                g = cv2.resize(g, (max(1, int(g.shape[1] * sc)), max(1, int(g.shape[0] * sc))), interpolation=cv2.INTER_AREA)
                tile[:] = 40
                tile[:g.shape[0], :g.shape[1]] = g
                worst = [k for k, c in j["checks"].items() if c.get("worst") == f]
                _text(tile, head + [(f"{name} f{f}", (255, 255, 255))]
                      + [(f"WORST {k}", (0, 255, 255)) for k in worst])
            cv2.rectangle(tile, (0, 0), (w - 1, h - 1), col, 3)
            row.append(tile)
        info_tile = np.full((h, w, 3), 30, np.uint8)
        lines = [(f"a{j['attempt']} {verdict(j)}", col),
                 (f"intended {j['intended_type']} ({j['intended_source']})", (255, 255, 255))]
        for k in CHECKS:
            c = j["checks"][k]
            res = c["result"]
            rc = {"pass": (0, 200, 0), "fail": (0, 0, 255), "unsure": (0, 200, 255)}.get(res, (160, 160, 160))
            wf = f" w{c['worst']}" if c.get("worst") is not None else ""
            lines.append((f"{k}: {res}", rc))
            lines.append((f"  {fmt(k, c)}{wf}", (230, 230, 230)))
        _text(info_tile, lines, sc=0.42)
        row.append(info_tile)
        rows.append(np.hstack(row))
    cv2.imwrite(str(path), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])


def worst_frames(judged: list[dict]) -> set[int]:
    """Every check's worst frame (the overlay always draws them; check_pipeline's worst sheet picks from them)."""
    return {int(c["worst"]) for j in judged for c in j["checks"].values() if c.get("worst") is not None}


def run(ctx: Context, tmp: Path) -> None:
    recs = json.loads(ctx.path("phases.json").read_text())["attempts"]
    s = signals(ctx)
    labels = labels_for(ctx.path(LABELS), ctx.clip.stem)
    param = ctx.params.get("intended")
    judged = [judge(r, s, param, labels.get(int(r["attempt"]))) for r in recs]
    (tmp / "judgement.json").write_text(json.dumps(dict(attempts=judged, params=PARAMS), indent=2) + "\n")
    pose = np.load(ctx.path("pose.npz"))
    plate = dict(np.load(ctx.path("plate.npz")))
    kp = np.asarray(pose["keypoints"], float)
    write_sheet(tmp / "judgement_sheet.jpg", str(ctx.clip), recs, judged, kp, plate)

    n = len(kp)
    which = np.full(n, -1)
    banner_from = {}
    for a, (r, j) in enumerate(zip(recs, judged)):
        w0, w1 = r["window"]
        which[w0:w1] = a
        oh = r["bar_overhead"]
        banner_from[a] = int(oh["end"]) if oh else int(np.searchsorted(s.t, s.t[w1 - 1] - 0.5))
    extra = sorted({min(b, int(recs[a]["window"][1]) - 1) for a, b in banner_from.items()} | worst_frames(judged))

    def labels_at(i: int) -> list[str]:
        a = which[i]
        if a < 0:
            return ["outside attempts"]
        j = judged[a]
        return [f"attempt {j['attempt']}: {j['performed_type']} (intended {j['intended_type']}, {j['intended_source']})"]

    def annotate(img: np.ndarray, i: int) -> None:
        a = which[i]
        if a < 0 or i < banner_from[a]:
            return
        j = judged[a]
        text = verdict(j)
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 2.4, 6)
        nx, ny = np.nan_to_num(kp[i, HALPE26["nose"]], nan=100.0)
        x0, y0 = max(0, int(nx) - tw // 2), max(th + 20, int(ny) - 220)
        cv2.rectangle(img, (x0 - 16, y0 - th - 18), (x0 + tw + 16, y0 + 18), COLOR[j["lift_result"]], -1)
        cv2.putText(img, text, (x0, y0), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (255, 255, 255), 6)

    (tmp / OVERLAY).parent.mkdir(parents=True, exist_ok=True)
    overlay.render(str(ctx.clip), str(tmp / OVERLAY), poses=[{"keypoints": kp}], plate=plate, step=4, zoom=True,
                   extra=extra, frame_labels=labels_at, annotate=annotate)


STAGE = Stage("S8", (CLIP, "phases.json", "angles.csv", "pose.npz", "plate.npz", "facing.json", LABELS),
              ("judgement.json", "judgement_sheet.jpg", OVERLAY), run, params=("intended",))
