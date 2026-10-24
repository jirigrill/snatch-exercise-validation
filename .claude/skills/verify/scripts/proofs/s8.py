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
# (clip, attempt) whose frames are another attempt's (T8 attempt 1 is T1's clip): not a distinct lift
DUPLICATES = {("T8", 1): ("T1", 1)}
# (clip, expected S8 reason, expected elbow_frames_seen or None for any) -> cause; used only when the observed row matches
CAUSE = {
    ("T2", "type_mismatch", None): "lifter caught a deep power snatch while intending squat (label note 2026-10-23); S8's type_mismatch is right "
          "by the rule, the label's `completed` records intent, not the rule",
    ("T1", "low_confidence", 0): "wrist under the plate on every hold frame, elbow never seen (elbow_frames_seen 0) -> unknown low_confidence; "
          "known gap, the arm-length plan item",
}
CAUSE[("T6", "low_confidence", 0)] = CAUSE[("T8", "low_confidence", 0)] = CAUSE[("T1", "low_confidence", 0)]


def cause(r: dict) -> str:
    for (c, reason, ef), text in CAUSE.items():
        if c == r["clip"] and r["reason"] == reason and (ef is None or r["elbow_frames"] == ef):
            return text
    return "not explained"


def names(rs: list[dict]) -> str:
    return ", ".join(f"{r['clip']} a{r['attempt']}" for r in sorted(rs, key=lambda r: (r["clip"], r["attempt"]))) or "none"


def truth_text() -> str:
    by: dict[str, list[str]] = {}
    for (c, k), t in sorted(PERFORMED_TRUE.items()):
        by.setdefault(t, []).append(f"{c} a{k}")
    return "; ".join(f"{', '.join(v)}: {t}" for t, v in by.items()) + "; every other attempt: power"


def stopped(root: Path) -> list[str]:
    """test clips (T<n>) in labels.csv whose dir under root has no judgement.json (stopped before S8)."""
    with agreement.LABELS.open() as fh:
        dirs = sorted({r["clip"] for r in csv.DictReader(fh)})
    return sorted({d.split("_")[0] for d in dirs
                   if d.split("_")[0][1:].isdigit() and d.startswith("T") and not (root / d / "judgement.json").is_file()})


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
            hold_s = None if hold["start"] is None else round(float(t[min(hold["end"], len(t) - 1)] - t[hold["start"]]), 3)
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


def write_verdict(path: Path, rows: list[dict], agr: str, stop: list[str]) -> None:
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
    L += [f"- {r['clip']} a{r['attempt']}: {cause(r)}" for r in rows if not r["ok"]]
    no_ov = [r for r in rows if r["label_reason"] == "no_overhead"]
    no_ov_ok = [r for r in no_ov if r["ok"]]
    rule_ok = [r for r in rows if not r["ok"] and r["reason"] == "type_mismatch" and r["performed"] == r["true_type"]
               and r["intended"] != r["true_type"]]
    blind = [r for r in rows if not r["ok"] and r["ours"] == "unknown" and r["elbow_frames"] == 0]
    unexplained = [r for r in rows if not r["ok"] and r not in rule_ok and r not in blind]
    any_completed = any(r["ours"] == "completed" for r in rows)
    L += ["", f"**Answer: {'yes' if n_ok == len(rows) else 'no'}.** {n_ok} of {len(rows)} attempts match. "
          f"no_overhead failures right: {len(no_ov_ok)} of {len(no_ov)} ({names(no_ov_ok)}). "
          f"Misses that are the rule applied to the lifter's confirmed performed type (type_mismatch): {names(rule_ok)}. "
          f"Misses that say unknown with the elbow never seen (elbow_frames_seen 0): {names(blind)}. "
          f"Other misses: {names(unexplained)}. "
          + ("A completed verdict exists." if any_completed else
             "No completed verdict exists on any clip, so the completed path is untested here."), ""]
    # ---- Q2
    t_ok = sum(r["performed"] == r["true_type"] or (r["performed"] == "unknown" and r["performed_why"] == "failed_pull"
                                                     and r["true_type"].startswith("none")) for r in rows)
    squat = [r for r in rows if r["intended"] == "squat"]
    squat_true = [r for r in rows if r["true_type"] == "squat"]
    L += ["## Question 2: is the performed type right?", "",
          f"Truth: the lifter's word in the labels.csv notes ({truth_text()}).", "",
          "| clip | att | intended (label) | true performed | S8 performed | why unknown |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['clip']} | {r['attempt']} | {f(r['intended'])} | {r['true_type']} | {r['performed']} | {f(r['performed_why'])} |")
    L += ["", f"**Answer: {'yes' if t_ok == len(rows) else 'no'}.** {t_ok} of {len(rows)} right (no catch counted right only when S8 says "
          f"unknown, failed_pull). Squat-intended attempts: {len(squat)} ({names(squat)}); true squat catches: {len(squat_true)} "
          f"({names(squat_true)})" + ("; S8 has never been shown a real squat catch." if not squat_true else "."), ""]
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
          "frames are S7's exactly, and the hold length is S7's span. "
          f"Attempts with no S7 hold: {names([r for r in rows if r['hold_span'] is None])}; "
          f"S8 used no hold frames on: {names([r for r in rows if r['j_hold_frames'] is None])}. "
          "The elbow check reads the elbow angle on S7's hold frames only; it has no window of its own.", ""]
    # ---- how
    L += ["## How this test works", "",
          f"S8 ran inside the pipeline on the test clips {', '.join(sorted({r['clip'] for r in rows}))}"
          + (f" ({', '.join(stop)} have no judgement.json: stopped before S8)" if stop else "") + ". Its judgement.json is compared with "
          "labels.csv by `prototype/scripts/agreement.py`, the performed type with the lifter's notes, and its frames with S7's phases.json. "
          f"Limits: {len(rows)} attempts, one lifter"
          + "".join(f", and {c} attempt {k} is {c2} attempt {k2}'s frames" for (c, k), (c2, k2) in DUPLICATES.items()
                    if any((r["clip"], r["attempt"]) == (c, k) for r in rows))
          + f", so {len(rows) - sum(any((r['clip'], r['attempt']) == d for r in rows) for d in DUPLICATES)} distinct lifts. "
          "The labels give the lifter's intent and result, not the rule's verdict, so a correct rule can disagree with a label"
          + (f" ({names(rule_ok)})" if rule_ok else "") + ". "
          "There is no ground truth for the elbow angle: "
          f"clips with the elbow never seen on the hold (elbow_frames_seen 0): {names([r for r in rows if r['elbow_frames'] == 0])}; "
          f"clips with it seen: {names([r for r in rows if r['elbow_frames']])}. Completed verdicts: "
          f"{names([r for r in rows if r['ours'] == 'completed'])}; true squat catches: {names(squat_true)}. Nothing was tuned to pass: a no is a no.", "",
          "Image: `1_judgement_sheets.jpg`, each clip's judgement_sheet.jpg (downscaled to 900 px) under its clip id."]
    path.write_text("\n".join(L) + "\n")


def main(root: Path) -> None:
    out_dir = root / "proof/S8"
    ins = [clip_dir(root, c) / n for c in CLIPS for n in ("judgement.json", "phases.json", "judgement_sheet.jpg", "frame_times.npy")]
    with agreement.LABELS.open() as fh:
        lab_dirs = sorted({r["clip"] for r in csv.DictReader(fh)})
    # agreement.main reads <root>/<label clip>/judgement.json for every label clip whose dir exists
    agr_ins = [root / c / "judgement.json" for c in lab_dirs]
    agr_state = "|".join(f"{c}:{(root / c).is_dir()}" for c in lab_dirs).encode()
    dirs = "|".join(clip_dir(root, c).name for c in CLIPS).encode()
    key = sha(agreement.LABELS.read_bytes(), Path(agreement.__file__).read_bytes(), Path(__file__).read_bytes(), dirs, agr_state,
              *(p.read_bytes() for p in ins), *(p.read_bytes() if p.is_file() else b"-" for p in agr_ins))
    hit = CACHE / key
    if (hit / "verdict.md").is_file():
        log(f"cached {key}")
    else:
        tmp = CACHE / f"{key}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        sheets(root, tmp / "1_judgement_sheets.jpg")
        write_verdict(tmp / "verdict.md", collect(root), agreement_text(root), stopped(root))
        shutil.rmtree(hit, ignore_errors=True)
        tmp.rename(hit)
    shutil.rmtree(out_dir, ignore_errors=True)
    shutil.copytree(hit, out_dir)
    log(f"wrote {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
