"""Check a review file against an evidence root and print the PR comment (publish_evidence.sh).

usage: uv run python render_comment.py <evidence_root> <review.md> <blob url of the root> <files line>   (from prototype/)

Shown stages = the ones diff_outputs.py found new or changed on any clip (<root>/changes.json), else, with
no <root>/base/, the ones whose code changed vs main (stage_files.py show; SHOW_STAGES="S2 C3" adds names,
`all` shows all). Each shown stage is a section in pipeline order: its title and text from
features/stage-guide.md, a proof (<root>/proof/<stage>/verdict.md + png/jpg, if present), then one
subsection per clip where it ran: the clip's detail lines from the log and the stage's images, each
followed by its review bullet. A calibration stage is its own section "(calibration, T5)" and its review
key is "<stage> calibration" when the stage is also an analyze stage (S1, S4), else the stage name.

review.md: `## <stage>` sections of bullets `- <clip id> <image stem>: <verdict>` (a stage's images are
png/jpg outputs and, of an mp4, its _sheet and _worst jpg). Text before the first `##` is kept as notes.
Fails (exit 1, before anything is pushed) when a shown image has no bullet, a bullet of a _worst image
misses a frame of its .worst, a bullet names no shown image, a section is for a stage that is not shown,
or the guide has no section for a shown stage. All clips stay open; only over GitHub's 65536 characters
are a stage's later clips collapsed, and the comment says so. A proof's own headings are demoted
below the stage's (`## Question` -> `##### Question`).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from snatch.stages import CALIBRATE, STAGES

from diff_outputs import clip_id, rollup  # pyright: ignore[reportMissingImports]  (run as a script: its dir is on sys.path)

HERE = Path(__file__).resolve().parent
LIMIT = 65000  # GitHub's comment limit is 65536 characters
STATE_ORDER = ("new", "changed", "identical", "absent", "no outputs")


class Fail(Exception):
    pass


def guide() -> dict[str, tuple[str, str]]:
    """stage name -> (title, body) of features/stage-guide.md."""
    out = {}
    for sec in re.split(r"^## ", (HERE.parent / "features" / "stage-guide.md").read_text(), flags=re.M)[1:]:
        head, _, body = sec.partition("\n")
        name, _, title = head.partition(" · ")
        out[name.strip()] = (title.strip(), body.strip())
    return out


def parse_review(text: str) -> tuple[str, dict[str, list[tuple[str, set[str], str]]]]:
    """(notes before the first ##, {section: [(clip id, stems, bullet text)]})."""
    notes, sections, cur = [], {}, None
    for line in text.splitlines():
        if m := re.match(r"##\s+(.+?)\s*$", line):
            cur = sections.setdefault(m[1], [])
        elif cur is None:
            notes.append(line)
        elif m := re.match(r"- (\S+) ([^:]+):", line.replace("`", "")):
            cur.append((m[1], set(re.split(r"\s*(?:,|&|\band\b|\s)\s*", m[2].strip())), line))
        elif cur and line.strip():
            cur[-1] = (*cur[-1][:2], cur[-1][2] + "\n" + line)
    return "\n".join(notes).strip(), sections


def log_detail(logs: dict[str, list[str]], clip: str, ctx: str, stage: str) -> list[str]:
    """The `  <stage>: …` lines of the first run's check (ctx "cal" or "ana") in the clip's log (calibration: the first log with it)."""
    for c, lines in logs.items():
        if ctx == "ana" and c != clip:
            continue
        cur, found = None, []
        for line in lines:
            if re.match(r"(\(cached\) )?calibrate rerun:|rerun:", line):
                cur = "skip"
            elif re.match(r"(\(cached\) )?calibrate:", line):
                cur = "cal"
            elif line.startswith("first:"):
                cur = "ana"
            elif cur == ctx and re.match(rf"  {re.escape(stage)}:", line):
                found.append(line)
        if found:
            return found
    return []


def images(stage, d: Path) -> list[str]:
    """The stage's shown images that exist in clip dir d, relative to it: png/jpg outputs, an mp4's _sheet and _worst jpg."""
    out = []
    for o in stage.outputs:
        if o.endswith((".jpg", ".png")):
            out.append(o)
        elif o.endswith(".mp4"):
            out += [f"{o[:-4]}{x}.jpg" for x in ("_sheet", "_worst")]
    return [x for x in out if (d / x).is_file()]


def shown_stages(root: Path) -> tuple[dict[tuple[str, str], str], dict[str, dict], str]:
    """({(kind, stage): state} for the shown stages, {stage: {clip: state}} for the table, note)."""
    if (root / "base").is_dir():
        res = json.loads((root / "changes.json").read_text())
        table = {s: v for s, v in res.items() if not s.startswith("_")}
        shown = {}
        for s, clips in table.items():
            for kind in ("analyze", "calibrate"):
                st = {c: v for c, v in clips.items() if c.startswith("calibrate_") == (kind == "calibrate")}
                if (r := rollup(st)) in ("new", "changed"):
                    shown[(kind, s)] = r
        note = f"not compared (no passing base run): {', '.join(res['_no_base'])}" if res.get("_no_base") else ""
        return shown, table, note
    base = subprocess.check_output(["git", "merge-base", "HEAD", "origin/main"], text=True).strip()
    lines = subprocess.check_output([sys.executable, str(HERE / "stage_files.py"), "show", base, *os.environ.get("SHOW_STAGES", "").split()],
                                    text=True).splitlines()
    shown = {(k, s): "code changed" for k, s in (line.split() for line in lines)}
    return shown, {}, "No baseline (`base/` missing, run base_run.sh): stages shown by code change vs main, not by output change."


def main(root: Path, review_path: Path, url: str, files_line: str) -> str:
    gd, (notes, review) = guide(), parse_review(review_path.read_text())
    shown, table, note = shown_stages(root)
    dirs = {clip_id(p.name): p for p in sorted(root.iterdir()) if p.is_dir() and p.name not in ("athletes", "base", "proof")}
    analyze_names = {s.name for s in STAGES}
    lists = {"analyze": STAGES, "calibrate": CALIBRATE}
    key = lambda kind, s: f"{s} calibration" if kind == "calibrate" and s in analyze_names else s  # noqa: E731
    logs = {clip_id(p.name): p.read_text().splitlines() for p in sorted(root.glob("*.log"))}
    results = {c: next((x for x in reversed(ls) if re.match(r"(OK evidence:|FAIL:)", x)), "") for c, ls in logs.items()}
    ok = all(r.startswith("OK evidence:") for r in results.values())

    # the gate: every shown image has a bullet, every bullet an image, no stale section
    errors, used = [], set()
    plan = []  # (kind, stage, [(clip, dir, [images])])
    for kind, stages in lists.items():
        for st in stages:
            if (kind, st.name) not in shown:
                continue
            if st.name not in gd:
                errors.append(f"features/stage-guide.md has no section for {st.name}")
            per_clip = []
            for c, d in dirs.items():
                if c.startswith("calibrate_") != (kind == "calibrate"):
                    continue
                if table and table[st.name].get(c, {}).get("state") in (None, "absent", "no outputs"):
                    continue
                imgs = images(st, d)
                per_clip.append((c if kind == "analyze" else c.split("_")[1], d, imgs))
                for x in imgs:
                    stem, label = Path(x).stem, c if kind == "analyze" else c.split("_")[1]
                    b = [b for b in review.get(key(kind, st.name), []) if b[0] == label and stem in b[1]]
                    used |= {id(x_) for x_ in b}
                    if not b:
                        errors.append(f"{key(kind, st.name)}: no bullet for `- {label} {stem}:`")
                    elif x.endswith("_worst.jpg"):
                        w = (d / (x[:-10] + ".worst")).read_text().splitlines()[0].split()
                        errors += [f"{key(kind, st.name)}: `- {label} {stem}` misses frame {n}" for n in w
                                   if not any(re.search(rf"(?<!\d){n}(?!\d)", t[2]) for t in b)]
            plan.append((kind, st, per_clip))
    keys = {key(k, s) for k, s in shown}
    errors += [f"review section `## {k}` is for a stage that is not shown (stale review)" for k in review if k not in keys]
    errors += [f"{k}: bullet `{t[2].splitlines()[0][:50]}` names no shown image"
               for k, bs in review.items() if k in keys for t in bs if id(t) not in used]
    if errors:
        raise Fail("; ".join(errors))

    def block(kind: str, st, c: str, d: Path, imgs: list[str]) -> list[str]:
        label = key(kind, st.name)
        state = table[st.name][c if kind == "analyze" else "calibrate_" + c]["state"] if table else ""
        out = [f"#### {c}{' (identical to main)' if state == 'identical' else ''}", ""]
        det = log_detail(logs, c, "ana", st.name) if kind == "analyze" else log_detail(logs, "", "cal", st.name)
        if det:
            out += ["```", *det, "```", ""]
        for x in imgs:
            out += [f"![{x}]({url}/{d.name}/{x}?raw=true)"]
            if x.endswith("_worst.jpg"):
                w = (d / (x[:-10] + ".worst")).read_text().splitlines()
                out += [f"worst frames (from {Path(x[:-10]).name}.worst): {' '.join('f' + n for n in w[0].split())} - {w[1] if len(w) > 1 else ''}"]
            out += [""] + [t[2] + "\n" for t in review.get(label, []) if t[0] == c and Path(x).stem in t[1]]
        return out

    def render(open_clips: int | None) -> str:
        head = f"## /verify evidence: `{root.name}` {'✅ OK' if ok else '❌ FAIL'}"
        first = next(iter(logs.values()), [""])[0]
        out = [head, "", first, "", "| clip | result |", "|---|---|"]
        out += [f"| {c} | {'✅ OK' if r.startswith('OK') else '❌ ' + (r or 'no result line (run did not finish)').replace('|', '/')} |"
                for c, r in results.items()]
        if notes:
            out += ["", notes]
        out += ["", f"### What changed vs main (base {base_sha(root)})" if table else "### What changed vs main", ""]
        out += ["| stage | state | clips | files |", "|---|---|---|---|"]
        for name in dict.fromkeys(s.name for s in [*STAGES, *CALIBRATE]):
            clips = table.get(name, {})
            if table:
                st = rollup(clips)
                off = {c: v["files"] for c, v in clips.items() if v["state"] in ("new", "changed")}
                fl = {}
                for f in off.values():
                    for k, v in f.items():
                        fl.setdefault(k, v)
                cl = ", ".join(off) if off else ("all" if st == "identical" else "-")
                fs = "; ".join(f"`{k}` {v}".strip() for k, v in list(fl.items())[:6]) + (f"; +{len(fl) - 6} more" if len(fl) > 6 else "")
                out.append(f"| {name} | {st} | {cl} | {fs} |")
            else:
                on = [k for k, s in shown if s == name]
                out.append(f"| {name} | {'code changed' if on else 'code unchanged'} | | |")
        out += ["", note] if note else []
        if table:
            out += ["", "Unchanged stages show no images; their outputs are identical to main's on every clip." if plan
                    else "No stage changed vs main: every output is identical, so no images are shown."]
        for kind, st, per_clip in plan:
            label = key(kind, st.name)
            title, body = gd[st.name]
            states = {c: v for c, v in table.get(st.name, {}).items() if c.startswith("calibrate_") == (kind == "calibrate")}
            state = rollup(states) if table else "code changed"
            cal = f" (calibration, {per_clip[0][0]})" if kind == "calibrate" and per_clip else ""
            out += ["", f"### {st.name} · {title}{cal} ({state})", "", body]
            proof = root / "proof" / label.replace(" ", "_")
            if (proof / "verdict.md").is_file():
                verdict = re.sub(r"^(#{1,6}) ", lambda m: "#" * min(6, len(m.group(1)) + 3) + " ",
                                 (proof / "verdict.md").read_text().strip(), flags=re.M)
                out += ["", "#### Proof", "", verdict, ""]
                out += [f"![{p.name}]({url}/proof/{proof.name}/{p.name}?raw=true)" for p in sorted(proof.glob("*.png")) + sorted(proof.glob("*.jpg"))]
            keep = len(per_clip) if open_clips is None else open_clips
            for i, (c, d, imgs) in enumerate(per_clip):
                b = block(kind, st, c, d, imgs)
                out += [""] + (b if i < keep else ["<details><summary>%s · %s</summary>" % (st.name, c), "", *b, "", "</details>"])
        ex = [p for p in sorted(root.iterdir()) if p.is_file() and p.suffix in (".png", ".jpg")]
        if ex:
            out += ["", "### Explainer"] + [f"![{p.name}]({url}/{p.name}?raw=true)" for p in ex]
        if open_clips is not None:
            out += ["", f"Clip blocks collapsed to fit GitHub's 65536-character limit ({open_clips} per stage left open)."]
        return "\n".join([*out, "", files_line, ""])

    text = render(None)
    for k in (2, 1, 0):
        if len(text) > LIMIT:
            text = render(k)
    if len(text) > LIMIT:
        raise Fail(f"the comment is {len(text)} characters even collapsed (GitHub allows 65536)")
    return text


def base_sha(root: Path) -> str:
    for log in sorted((root / "base").glob("*.log")):
        return log.read_text().split()[1]
    return "?"


if __name__ == "__main__":
    try:
        print(main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]), end="")
    except Fail as e:
        sys.exit(f"FAIL: {e}")
