"""S9 proof: are the 6 bar-path metrics read on S7's borders, null exactly where a border is missing, and does
report.json carry judgement.json's label?

usage (from prototype/): uv run python ../.claude/skills/verify/scripts/proofs/s9.py <evidence_root>
writes <evidence_root>/proof/S9/{verdict.md, 1_findings_sheets.jpg}

Inputs per clip (T1-T8 that reached S8): findings.json, report.json, judgement.json, phases.json, findings_sheet.jpg.
No truth for the values or the faults (thresholds from the sources, not clip labels): the verdict lists them for the eye check of the
sheets (each arrow on its frames, value as drawn). Cached in .scratch/verify/cache/proof-s9/<key>/.
"""

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "prototype/src"))
from snatch.findings import FAULTS  # noqa: E402

REPO = Path(__file__).resolve().parents[5]
CACHE = REPO / ".scratch/verify/cache/proof-s9"
CLIPS = ("T1", "T2", "T3", "T4", "T6", "T7", "T8")
FILES = ("findings.json", "report.json", "judgement.json", "phases.json", "findings_sheet.jpg")
WIDTH = 1100


def log(msg: str) -> None:
    print(f"[s9 proof {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def clip_dir(root: Path, clip: str) -> Path | None:
    return next((p for p in sorted(root.glob(f"{clip}_*")) if p.is_dir()), None)


def done(root: Path) -> list[tuple[str, Path]]:
    out = []
    for c in CLIPS:
        d = clip_dir(root, c)
        if d is not None and all((d / n).is_file() for n in FILES):
            out.append((c, d))
    return out


def sheets(clips: list[tuple[str, Path]], path: Path) -> None:
    parts = []
    for c, d in clips:
        im = cv2.imread(str(d / "findings_sheet.jpg"))
        im = cv2.resize(im, (WIDTH, round(im.shape[0] * WIDTH / im.shape[1])), interpolation=cv2.INTER_AREA)
        bar = np.full((34, WIDTH, 3), 255, np.uint8)
        cv2.putText(bar, c, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
        parts += [bar, im]
    cv2.imwrite(str(path), np.vstack(parts), [cv2.IMWRITE_JPEG_QUALITY, 88])


def write_verdict(path: Path, clips: list[tuple[str, Path]], root: Path) -> None:
    L = ["# S9 proof", "", "Metrics per attempt (value, frames start-end, `@` = arrow tip; null = the missing borders).", ""]
    bad = []
    for c, d in clips:
        fnd = json.loads((d / "findings.json").read_text())["attempts"]
        rep = json.loads((d / "report.json").read_text())["attempts"]
        jud = json.loads((d / "judgement.json").read_text())["attempts"]
        phs = {p["attempt"]: p for p in json.loads((d / "phases.json").read_text())["attempts"]}
        for f, r, j in zip(fnd, rep, jud):
            k = f["attempt"]
            want = ("completed_with_errors" if any(x["severity"] == "error" for x in f["findings"]) else "completed_clean"
                    ) if j["lift_result"] == "completed" else j["lift_result"]
            same = (r["final_label"], r["reason"]) == (want, j["reason"])
            if sorted([x["fault"] for x in f["checked"] + f["skipped"]]) != sorted(FAULTS):
                bad.append(f"{c} a{k}: a fault neither checked nor skipped")
            if not same:
                bad.append(f"{c} a{k}: report {r['final_label']} {r['reason']} != judgement {j['lift_result']} {j['reason']}")
            for n, m in f["metrics"].items():
                miss = [b for b in m["missing"] if b != "bar_overhead" and not b.startswith("plate@") and phs[k]["borders"].get(b)]
                if miss or (m["missing"] and m["value"] is not None):
                    bad.append(f"{c} a{k} {n}: missing {m['missing']} vs borders")
            L.append(f"## {c} a{k}: {r['final_label']} {r['reason'] or ''} (label consistent with judgement + findings: {same})")
            for n, m in f["metrics"].items():
                v = f"null (missing {', '.join(m['missing'])})" if m["value"] is None and m["missing"] else (
                    f"null ({m['value_px']} px; window has no found plate frame for px_per_m)" if m["value"] is None else
                    f"{m['value']:+.1f} {m['unit']} ({m['value_px']:+.0f} px), f{m['frames'][0]}-{m['frames'][1]} @{m['at']}")
                L.append(f"- {n}: {v}")
            for x in f["checked"]:
                L.append(f"- fault {x['fault']}: {'FOUND' if x['found'] else 'ok'} {x['value']} vs {x['threshold']} {x['unit']}")
            for x in f["skipped"]:
                L.append(f"- fault {x['fault']}: skipped ({x['reason']})")
            L.append("")
    stopped = [p.name for p in sorted(root.iterdir()) if p.is_dir() and (p / "pipeline_status.json").is_file()
               and not (p / "report.json").is_file() and not p.name.startswith("calibrate")]
    L += ["## Checks", f"- report label == judgement and null metrics name real missing borders: "
          f"{'PASS' if not bad else 'FAIL'}", *(f"  - {b}" for b in bad),
          f"- no report.json (stopped before S8 or calibrate): {', '.join(stopped) or 'none'}", "",
          "Image: `1_findings_sheets.jpg`, each clip's findings_sheet.jpg under its clip id. Eye check (sheets.md): "
          "each numbered arrow starts at its start border's hub and ends at the `@` frame; the value matches the list."]
    path.write_text("\n".join(L) + "\n")


def main(root: Path) -> None:
    out_dir = root / "proof/S9"
    clips = done(root)
    key = hashlib.sha1(Path(__file__).read_bytes() + "|".join(d.name for _, d in clips).encode()
                       + b"".join((d / n).read_bytes() for _, d in clips for n in FILES)).hexdigest()[:10]
    hit = CACHE / key
    if (hit / "verdict.md").is_file():
        log(f"cached {key}")
    else:
        tmp = CACHE / f"{key}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        sheets(clips, tmp / "1_findings_sheets.jpg")
        write_verdict(tmp / "verdict.md", clips, root)
        shutil.rmtree(hit, ignore_errors=True)
        tmp.rename(hit)
    shutil.rmtree(out_dir, ignore_errors=True)
    shutil.copytree(hit, out_dir)
    log(f"wrote {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
