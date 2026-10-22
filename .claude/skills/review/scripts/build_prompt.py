#!/usr/bin/env python3
"""Assemble the /review reviewer prompt. Run as `python3 -I build_prompt.py ...` (stdlib only).

usage: build_prompt.py --repo <root> --diff <file> --item <file> --deep yes|no [--prior <file>] --out <file>

Contents: reviewer.md (template), plan item, diff, spec context (stage object from
docs/pipeline-v2.html, its Decisions items, the stage-guide section, the plan md), CLAUDE.md,
prior findings. Nothing else: no briefs, no session text.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

PLAN_MD = {
    "B-front.md": ("S-1", "S0", "S1", "S2", "S3", "S4", "side"),
    "C-skeleton.md": ("C3", "S5", "S6"),
    "D-judge.md": ("S7", "S8", "S9", "report"),
}
MAX_SHARED = 6  # a module imported by more stage files than this is shared, not a stage's own

DEEP_TEXT = (
    "DEEP REVIEW. This diff touches a path where a bug makes all evidence lie (a verify script, a hook, "
    "or the S8 judge). For each changed function: read it in full in the repo (not just the hunks) and "
    "read its callers. Start your output with this line, before the count line:\n"
    "> **Human should read:** <one line: the deep paths touched, and what a bug there would make false>"
)
NOT_DEEP_TEXT = "Normal depth: review the diff and the spec context. Read other files only when a finding needs it."


def changed_files(diff: str) -> list[str]:
    return re.findall(r"^diff --git a/.* b/(.*)$", diff, re.M)


def stage_id_of(path: Path) -> str | None:
    m = re.search(r'Stage\(\s*"([^"]+)"', path.read_text())
    return m.group(1) if m else None


def stage_ids(repo: Path, files: list[str]) -> tuple[list[str], list[str]]:
    """Stage ids for the changed files, and notes on files that map to none."""
    sdir = repo / "prototype/src/snatch/stages"
    ids: list[str] = []
    notes: list[str] = []

    def add(i: str) -> None:
        if i not in ids:
            ids.append(i)

    for f in files:
        m = re.fullmatch(r"prototype/src/snatch/stages/(\w+)\.py", f)
        if m:
            p = repo / f
            i = stage_id_of(p) if p.exists() else None
            if i:
                add(i)
            continue
        m = re.fullmatch(r"prototype/src/snatch/(\w+)\.py", f)
        if not m or not sdir.is_dir():
            continue
        x = m.group(1)
        pat = re.compile(
            rf"^\s*from\s+snatch\.{x}\s+import\b|^\s*from\s+snatch\s+import\s+[^\n]*\b{x}\b|^\s*from\s+\.\.\s+import\s+[^\n]*\b{x}\b",
            re.M,
        )
        importers = [p for p in sorted(sdir.glob("*.py")) if p.name != "__init__.py" and pat.search(p.read_text())]
        if not importers:
            notes.append(f"{f}: no stage imports it")
        elif len(importers) > MAX_SHARED:
            notes.append(f"{f}: shared module, imported by {len(importers)} stage files; no single stage")
        else:
            for p in importers:
                i = stage_id_of(p)
                if i:
                    add(i)
    return ids, notes


def js_object(src: str, sid: str) -> str | None:
    """The `KEY: { t:"<sid> · ...` object of docs/pipeline-v2.html, up to its matching brace."""
    for variant in {sid, sid.replace("-", "−")}:
        m = re.search(r'^\s*\w+:\s*\{\s*t:"' + re.escape(variant) + r' ·', src, re.M)
        if m:
            start = src.index("{", m.start())
            depth, quote, i = 0, "", start
            while i < len(src):
                c = src[i]
                if quote:
                    if c == "\\":
                        i += 1
                    elif c == quote:
                        quote = ""
                elif c in "\"'`":
                    quote = c
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return src[m.start():i + 1].strip()
                i += 1
    return None


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def decisions(src: str, sid: str) -> list[str]:
    m = re.search(r"<h2>Decisions[^<]*</h2>(.*?)</div>\s*</div>\s*<aside", src, re.S)
    if not m:
        return []
    word = re.compile(r"(?<![\w−-])" + re.escape(sid).replace("\\-", "[-−]") + r"(?![\w])")
    out = []
    for line in m.group(1).splitlines():
        if 'class="open"' in line and word.search(strip_tags(line)):
            out.append(strip_tags(line))
    return out


def guide_section(text: str, sid: str) -> str | None:
    m = re.search(rf"^## {re.escape(sid)} ·.*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0).strip() if m else None


def fenced(body: str, lang: str = "") -> str:
    longest = max([len(r) for r in re.findall(r"`+", body)] + [2])
    fence = "`" * (longest + 1)
    return f"{fence}{lang}\n{body.rstrip()}\n{fence}"


def spec_context(repo: Path, files: list[str]) -> str:
    ids, notes = stage_ids(repo, files)
    parts: list[str] = []
    if not ids:
        parts.append(
            "No stage owns the changed files"
            + (" (" + "; ".join(notes) + ")" if notes else "")
            + ". There is no spec section for this diff. Check it against the stage-contract text instead: "
            "the docstring of `prototype/src/snatch/stage.py` and the callers of whatever changed."
        )
        return "\n\n".join(parts)
    if notes:
        parts.append("Files with no single stage: " + "; ".join(notes) + ". Check those against the stage contract (`prototype/src/snatch/stage.py` docstring and its callers).")
    spec = (repo / "docs/pipeline-v2.html").read_text()
    guide_p = repo / ".claude/skills/verify/features/stage-guide.md"
    guide = guide_p.read_text() if guide_p.exists() else ""
    plans: list[str] = []
    for i in ids:
        parts.append(f"## Stage {i}")
        obj = js_object(spec, i)
        parts.append(
            "From `docs/pipeline-v2.html` (Steps, outputs and overlays):\n" + fenced(obj, "js")
            if obj
            else f"No `{i}` entry found in docs/pipeline-v2.html."
        )
        dec = decisions(spec, i)
        if dec:
            parts.append("From `docs/pipeline-v2.html` Decisions (tags stripped):\n" + "\n".join(f"- {d}" for d in dec))
        g = guide_section(guide, i)
        parts.append(
            "From `.claude/skills/verify/features/stage-guide.md`:\n" + fenced(g, "markdown")
            if g
            else f"`.claude/skills/verify/features/stage-guide.md` has no `## {i} ·` heading."
        )
        for name, members in PLAN_MD.items():
            if i in members and name not in plans:
                plans.append(name)
    for name in plans:
        p = repo / ".scratch/plan" / name
        parts.append(f"## Plan: .scratch/plan/{name}\n" + (fenced(p.read_text(), "markdown") if p.exists() else "(file missing)"))
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--diff", required=True)
    ap.add_argument("--item", required=True)
    ap.add_argument("--prior")
    ap.add_argument("--deep", choices=["yes", "no"], default="no")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    repo = Path(a.repo)
    diff = Path(a.diff).read_text()
    item = Path(a.item).read_text().strip()
    template = (Path(__file__).resolve().parent.parent / "reviewer.md").read_text()
    prior = Path(a.prior).read_text().strip() if a.prior else ""
    values = {
        "REPO": str(repo.resolve()),
        "ITEM": item or "(no plan item given)",
        "DIFF": fenced(diff, "diff") if diff.strip() else "(empty diff)",
        "SPEC": spec_context(repo, changed_files(diff)),
        "CLAUDE_MD": fenced((repo / "CLAUDE.md").read_text(), "markdown"),
        "PRIOR": prior if prior else "(none: this is a full review)",
        "DEPTH": DEEP_TEXT if a.deep == "yes" else NOT_DEEP_TEXT,
    }
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), template)  # one pass: values are never rescanned
    Path(a.out).write_text(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
