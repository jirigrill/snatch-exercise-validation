"""Compare the issue states in docs/STATUS.md with GitHub.

usage: python3 -I tools/check_status.py [path/to/STATUS.md]
exit 0 if every `| #N | open|closed |` row matches `gh issue`, 1 on drift.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROW = re.compile(r"^\|\s*#(\d+)\s*\|\s*(open|closed)\s*\|", re.M)


def documented(text: str) -> dict[int, str]:
    return {int(n): state for n, state in ROW.findall(text)}


def drift(doc: dict[int, str], live: dict[int, str]) -> list[str]:
    return [
        f"#{n}: STATUS.md says {state}, GitHub says {live.get(n, 'missing')}"
        for n, state in sorted(doc.items())
        if live.get(n) != state
    ]


def live_states() -> dict[int, str]:
    out = subprocess.run(
        ["gh", "issue", "list", "--state", "all", "--limit", "500", "--json", "number,state"],
        check=True, capture_output=True, text=True,
    ).stdout
    return {i["number"]: i["state"].lower() for i in json.loads(out)}


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs/STATUS.md"
    problems = drift(documented(path.read_text()), live_states())
    print("\n".join(problems) or "STATUS.md matches GitHub")
    sys.exit(1 if problems else 0)
