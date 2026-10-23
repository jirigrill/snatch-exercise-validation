"""S8 judgement vs labels.csv over the clips of one evidence root (no target: see .scratch/plan/D-judge.md).

usage: uv run python scripts/agreement.py <root>   (root holds out dirs named <clip stem>, each with judgement.json)

Prints the agreement % (lift_result and, where labelled, performed type = intended_type), a confusion matrix of
lift_result (label rows, ours columns) and one of performed type vs intended_type, then one line per disagreement:
clip, attempt, label, ours, reason, the deciding check values. A labelled attempt without judgement.json (a clip
stopped before S8) is listed as missing.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

LABELS = Path(__file__).resolve().parents[1] / "labels.csv"
RESULTS = ("completed", "failed", "unknown")
TYPES = ("muscle", "power", "squat", "unknown")


def matrix(title: str, rows: tuple[str, ...], cols: tuple[str, ...], n: Counter) -> None:
    print(f"\n{title} (rows label, columns ours)")
    print(f"{'':>12}" + "".join(f"{c:>11}" for c in cols))
    for r in rows:
        print(f"{r:>12}" + "".join(f"{n[r, c]:>11}" for c in cols))


def deciding(j: dict) -> str:
    c = j["checks"]
    keep = [k for k, v in c.items() if v["result"] in ("fail", "unsure")] or ["no_overhead"]
    out = []
    for k in keep:
        v = c[k]
        extra = "".join(f" {x}={v[x]}" for x in ("elbow_min", "performed", "intended", "unsure") if x in v)
        out.append(f"{k}:{v['result']} value={v['value']} threshold={v['threshold']}{v['unit'] and ' ' + v['unit']}{extra}")
    return "; ".join(out)


def main(root: Path) -> int:
    with LABELS.open() as f:
        labels = list(csv.DictReader(f))
    res, typ, lines = Counter(), Counter(), []
    agree = total = t_agree = t_total = 0
    for lab in labels:
        jf = root / lab["clip"] / "judgement.json"
        if not jf.parent.is_dir():
            continue
        if not jf.exists():
            lines.append(f"{lab['clip'][:2]} a{lab['attempt']}: label {lab['result']} {lab['intended_type']}, missing (stopped before S8)")
            continue
        by = {j["attempt"]: j for j in json.loads(jf.read_text())["attempts"]}
        j = by.get(int(lab["attempt"]))
        if j is None:
            lines.append(f"{lab['clip'][:2]} a{lab['attempt']}: no such attempt in judgement.json")
            continue
        total += 1
        res[lab["result"], j["lift_result"]] += 1
        ok = lab["result"] == j["lift_result"] and (lab["reason"] or None) == j["reason"]
        agree += ok
        if lab["intended_type"]:
            t_total += 1
            typ[lab["intended_type"], j["performed_type"]] += 1
            t_agree += lab["intended_type"] == j["performed_type"]
        if not ok or (lab["intended_type"] and lab["intended_type"] != j["performed_type"]):
            lines.append(f"{lab['clip'][:2]} a{lab['attempt']}: label {lab['result']} {lab['reason'] or '-'} {lab['intended_type'] or '-'}"
                         f" | ours {j['lift_result']} {j['reason'] or '-'} {j['performed_type']} | {deciding(j)}")
    print(f"lift_result + reason agree: {agree}/{total} ({100 * agree / total if total else 0:.0f} %)")
    print(f"performed type = intended_type: {t_agree}/{t_total} ({100 * t_agree / t_total if t_total else 0:.0f} %)")
    matrix("lift_result", RESULTS, RESULTS, res)
    matrix("type: intended_type (label) vs performed_type (ours)", TYPES[:3], TYPES, typ)
    print("\ndisagreements:")
    print("\n".join(lines) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
