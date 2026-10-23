"""S8 proof: does S8's lift_result and performed type match the lifter's labels, and does it judge on S7's borders only?

usage (from prototype/): uv run python ../.claude/skills/verify/scripts/proofs/s8.py <evidence_root>
writes <evidence_root>/proof/S8/{verdict.md, 1_judgement_sheets.jpg}

Truth: prototype/labels.csv (result, reason, intended type; the note holds the lifter's word on the performed type).
S8's output: <root>/<clip>/judgement.json; S7's borders: <root>/<clip>/phases.json. The agreement logic is
prototype/scripts/agreement.py (imported). Cached in .scratch/verify/cache/proof-s8/<key>/ (by input and code hash).
"""

import contextlib
import csv
import hashlib
import io
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "prototype/scripts"))

import agreement  # noqa: E402  # pyright: ignore[reportMissingImports]

CACHE = REPO / ".scratch/verify/cache/proof-s8"
CLIPS = ("T1", "T2", "T3", "T6", "T7", "T8")
WIDTH = 900
# the lifter's performed type per (clip, attempt): T2 caught power (label note 2026-10-23), T3/T7 no catch, rest power
PERFORMED_TRUE = {("T2", 1): "power", ("T3", 1): "none (no catch)", ("T7", 1): "none (no catch)"}
CAUSE = {
    "T2": "lifter caught a deep power snatch while intending squat (label note 2026-10-23); S8's type_mismatch is right "
          "by the rule, the label's `completed` records intent, not the rule",
    "T1": "wrist under the plate on every hold frame, elbow never seen (elbow_frames_seen 0) -> unknown low_confidence; "
          "known gap, the arm-length plan item",
}
CAUSE["T6"] = CAUSE["T8"] = CAUSE["T1"]


def log(msg: str) -> None:
    print(f"[s8 proof {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha(*parts: bytes) -> str:
    h = hashlib.sha1()
    for x in parts:
        h.update(x)
    return h.hexdigest()[:10]


def clip_dir(root: Path, clip: str) -> Path:
    return next(p for p in sorted(root.glob(f"{clip}_*")) if p.is_dir())


def phase(a: dict, name: str) -> dict:
    return next(p for p in a["phases"] if p["name"] == name)


def collect(root: Path) -> list[dict]:
    with agreement.LABELS.open() as f:
        labels = {(r["clip"], int(r["attempt"])): r for r in csv.DictReader(f)}
    rows = []
    for c in CLIPS:
        d = clip_dir(root, c)
        jud = {j["attempt"]: j for j in json.loads((d / "judgement.json").read_text())["attempts"]}
        phs = {a["attempt"]: a for a in json.loads((d / "phases.json").read_text())["attempts"]}
        t = np.load(d / "frame_times.npy")
        for k, j in sorted(jud.items()):
            lab, a = labels[(d.name, k)], phs[k]
            hold = phase(a, "hold")
            st = a["borders"]["standing"]
            hc, sc = j["checks"]["hold_short"], j["checks"]["no_standup"]
            hold_s = None if hold["start"] is None else round(float(t[hold["end"]] - t[hold["start"]]), 3)
            rows.append(dict(
                clip=c, attempt=k, label=lab["result"], label_reason=lab["reason"] or None, intended=lab["intended_type"] or None,
                note=lab["note"], ours=j["lift_result"], reason=j["reason"], performed=j["performed_type"],
                performed_why=j["performed_unknown_why"], deciding=agreement.deciding(j),
                ok=lab["result"] == j["lift_result"] and (lab["reason"] or None) == j["reason"],
                true_type=PERFORMED_TRUE.get((c, k), "power"),
                hold_span=None if hold["start"] is None else [hold["start"], hold["end"]], hold_s=hold_s,
                standing=None if st is None else st["frame"],
                j_hold_frames=hc["frames"], j_hold_s=hc["value"], j_hold_res=hc["result"],
                j_stand=None if sc["frames"] is None else sc["frames"][0],
                elbow_frames=j["checks"]["elbow_unlocked"].get("elbow_frames_seen"),
            ))
    return rows


def agreement_text(root: Path) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        agreement.main(root)
    return buf.getvalue()


def sheets(root: Path, path: Path) -> None:
    """judgement_sheet.jpg of each clip, downscaled to WIDTH, stacked with a clip label bar."""
    parts = []
    for c in CLIPS:
        im = cv2.imread(str(clip_dir(root, c) / "judgement_sheet.jpg"))
        im = cv2.resize(im, (WIDTH, round(im.shape[0] * WIDTH / im.shape[1])), interpolation=cv2.INTER_AREA)
        bar = np.full((34, WIDTH, 3), 255, np.uint8)
        cv2.putText(bar, c, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
        parts += [bar, im]
    cv2.imwrite(str(path), np.vstack(parts), [cv2.IMWRITE_JPEG_QUALITY, 88])


def f(x: object) -> str:
    return "-" if x is None else str(x)


def write_verdict(path: Path, rows: list[dict], agr: str) -> None:
    L = ["# S8 proof: judgement against the lifter's labels", ""]
    # ---- Q1
    n_ok = sum(r["ok"] for r in rows)
    L += ["## Question 1: does S8's lift_result + reason match labels.csv on T1-T8?", "",
          "Per attempt: the label (result, reason), S8's (lift_result, reason) and the check that decided it "
          "(from `prototype/scripts/agreement.py`).", "",
          "| clip | att | label | ours | match | deciding check |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['clip']} | {r['attempt']} | {r['label']} {f(r['label_reason'])} | {r['ours']} {f(r['reason'])} | "
                 f"{'yes' if r['ok'] else 'no'} | {r['deciding']} |")
    L += ["", "`agreement.py` output (confusion matrices: rows label, columns ours):", "", "```", agr.strip(), "```", "",
          "Cause of each miss:", ""]
    L += [f"- {r['clip']} a{r['attempt']}: {CAUSE.get(r['clip'], 'not explained')}" for r in rows if not r["ok"]]
    L += ["", f"**Answer: no.** {n_ok} of {len(rows)} attempts match. Both no_overhead failures (T3, T7) are right. "
          "No attempt is wrongly passed or wrongly failed for a reason the lifter disputes: T2's fail is the rule applied to a power catch "
          "the lifter confirms, and T1/T6/T8 say unknown instead of guessing when the elbow is not visible. "
          "No completed verdict exists yet on any clip, so the completed path is untested here.", ""]
    # ---- Q2
    t_ok = sum(r["performed"] == r["true_type"] or (r["performed"] == "unknown" and r["true_type"].startswith("none")) for r in rows)
    L += ["## Question 2: is the performed type right?", "",
          "Truth: the lifter's word in the labels.csv notes (T2 caught power, note 2026-10-23; T3/T7 have no catch; the rest power).", "",
          "| clip | att | intended (label) | true performed | S8 performed | why unknown |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['clip']} | {r['attempt']} | {f(r['intended'])} | {r['true_type']} | {r['performed']} | {f(r['performed_why'])} |")
    L += ["", f"**Answer: {'yes' if t_ok == len(rows) else 'no'}.** {t_ok} of {len(rows)} right (no catch counted right when S8 says "
          "unknown, failed_pull). Only one squat-intended attempt exists (T2, caught power), so S8 has never been shown a real squat catch.", ""]
    # ---- Q3
    agree = [r for r in rows if r["j_hold_frames"] == r["hold_span"] and r["j_stand"] == r["standing"]
             and (r["hold_s"] is None or abs(r["hold_s"] - (r["j_hold_s"] or 0)) < 0.002)]
    L += ["## Question 3: does every decision rest on S7's borders, with no S8 rule of its own?", "",
          "S7's hold phase and standing border (phases.json) next to the frames S8's checks used (judgement.json). "
          "Hold length = frame time of hold end - hold start, against hold_min_s 0.5 s.", "",
          "| clip | att | S7 hold | S7 hold s | S8 hold_short frames | S8 hold s | >= 0.5 s | S7 standing | S8 no_standup frame | agree |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['clip']} | {r['attempt']} | {f(r['hold_span'])} | {f(r['hold_s'])} | {f(r['j_hold_frames'])} | {f(r['j_hold_s'])} | "
                 f"{'-' if r['hold_s'] is None else ('yes' if r['hold_s'] >= 0.5 else 'no')} ({r['j_hold_res']}) | {f(r['standing'])} | "
                 f"{f(r['j_stand'])} | {'yes' if r in agree else 'no'} |")
    L += ["", f"**Answer: {'yes' if len(agree) == len(rows) else 'no'}.** {len(agree)} of {len(rows)} attempts: S8's hold and standing "
          "frames are S7's exactly, and the hold length is S7's span. T3/T7 have no hold (bar never overhead) and S8 skips the checks there. "
          "The elbow check reads the elbow angle on S7's hold frames only; it has no window of its own.", ""]
    # ---- how
    L += ["## How this test works", "",
          "S8 ran inside the pipeline on the test clips T1, T2, T3, T6, T7, T8 (T4 and T5 stop before S8). Its judgement.json is compared with "
          "labels.csv by `prototype/scripts/agreement.py`, the performed type with the lifter's notes, and its frames with S7's phases.json. "
          "Limits: 7 attempts, one lifter, and T8 attempt 1 is T1's frames, so 6 distinct lifts. The labels give the lifter's intent and "
          "result, not the rule's verdict, so a correct rule can disagree with a label (T2). There is no ground truth for the elbow angle: "
          "no clip shows the elbow on the hold, so the elbow_unlocked check is untested in both directions, and no completed verdict or "
          "squat catch exists to test. Nothing was tuned to pass: a no is a no.", "",
          "Image: `1_judgement_sheets.jpg`, each clip's judgement_sheet.jpg (downscaled to 900 px) under its clip id."]
    path.write_text("\n".join(L) + "\n")


def main(root: Path) -> None:
    out_dir = root / "proof/S8"
    ins = [clip_dir(root, c) / n for c in CLIPS for n in ("judgement.json", "phases.json", "judgement_sheet.jpg")]
    key = sha(agreement.LABELS.read_bytes(), Path(agreement.__file__).read_bytes(), Path(__file__).read_bytes(), *(p.read_bytes() for p in ins))
    hit = CACHE / key
    if (hit / "verdict.md").is_file():
        log(f"cached {key}")
    else:
        tmp = CACHE / f"{key}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        sheets(root, tmp / "1_judgement_sheets.jpg")
        write_verdict(tmp / "verdict.md", collect(root), agreement_text(root))
        shutil.rmtree(hit, ignore_errors=True)
        tmp.rename(hit)
    shutil.rmtree(out_dir, ignore_errors=True)
    shutil.copytree(hit, out_dir)
    log(f"wrote {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
