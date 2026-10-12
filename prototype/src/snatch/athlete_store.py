"""The athlete profile: athletes/<athlete>/athlete.json and skeleton.json."""

import json
import re
from pathlib import Path

ATHLETE = "athlete.json"
SKELETON = "skeleton.json"


ATHLETE_ID = re.compile(r"[A-Za-z0-9_-]+")


def path(root: Path, athlete: str, name: str) -> Path:
    if not ATHLETE_ID.fullmatch(athlete):
        raise ValueError(f"athlete id {athlete!r} must be letters, digits, _ or -")
    return root / athlete / name


def exists(root: Path, athlete: str, name: str) -> bool:
    return path(root, athlete, name).exists()


def load(root: Path, athlete: str, name: str) -> dict | None:
    p = path(root, athlete, name)
    return json.loads(p.read_text()) if p.exists() else None


def save(root: Path, athlete: str, name: str, data: dict) -> None:
    p = path(root, athlete, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(p)
