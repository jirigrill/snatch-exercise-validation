"""Run the pipeline-v2 stages on one clip (docs/pipeline-v2.html).

    uv run scripts/pipeline.py clip.MOV --athlete jiri [--height 1.80] [--only S-1 | --from S-1] [--force]
    uv run scripts/pipeline.py --calibrate bar.MOV --athlete jiri

After a run where S8 and S9 ran: report.json (key_angles per border and joint: deg + source seen / filled / hidden;
elbow hidden = wrist_hidden, hip/knee hidden = S6 hidden at that joint, as S8 reads them) and overlay.mp4.
Every non-calibrate run first deletes report.json, overlay.mp4 and overlay.json, so a run that stops leaves none.
"""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from snatch.pose import HALPE26, SIDE_OF
from snatch.stage import Context, run_stages
from snatch.stages import CALIBRATE, STAGES


def _radius(s: str) -> tuple[int, int]:
    try:
        lo, hi = (int(v) for v in s.split(":"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a:b, got {s!r}") from None
    return lo, hi


def parse(argv: list[str] | None = None) -> tuple[Context, argparse.Namespace]:
    names = list(dict.fromkeys(s.name for s in STAGES + CALIBRATE))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", type=Path, nargs="?")
    ap.add_argument("--calibrate", type=Path, metavar="BAR.MOV", help="calibrate the skeleton from a bar-only clip")
    ap.add_argument("--athlete", required=True)
    ap.add_argument("--height", type=float, help="athlete height in m, stored in athlete.json")
    ap.add_argument("--out", type=Path, help="default out/<clip stem>")
    ap.add_argument("--athletes", type=Path, default=Path("athletes"), help="athlete profiles root")
    pick = ap.add_mutually_exclusive_group()
    pick.add_argument("--only", choices=names, help="run this stage alone, always")
    pick.add_argument("--from", dest="start", choices=names, help="rerun this stage and every later one")
    ap.add_argument("--force", action="store_true", help="ignore the hashes")
    ap.add_argument("--load", type=float, help="kg on the bar incl. the bar, else from the filename")
    ap.add_argument("--intended", choices=("squat", "power", "muscle"), help="intended snatch type for S8")
    ap.add_argument("--radius", type=_radius, help="plate radius range in px, a:b")
    args = ap.parse_args(argv)
    if (args.clip is None) == (args.calibrate is None):
        ap.error("give one clip: <clip.MOV> or --calibrate <bar.MOV>")
    clip = args.calibrate or args.clip
    stages = CALIBRATE if args.calibrate else STAGES
    pick = args.only or args.start
    if pick and pick not in [s.name for s in stages]:
        ap.error(f"{pick} is not a stage of {'--calibrate' if args.calibrate else 'an analyze run'}")

    params = {"athlete": args.athlete, "height": args.height, "load": args.load, "intended": args.intended,
              "radius": args.radius, "calibrate": args.calibrate is not None}
    return Context(clip, args.out or Path("out") / clip.stem, params, athletes=args.athletes), args


KEY_BORDERS = ("liftoff", "full_extension", "bar_peak", "bar_lowest", "standing")
KEY_JOINTS = ("knee", "hip", "elbow")


def angle_source(row: dict, joint: str, pose_hidden: np.ndarray, side: str) -> str:
    """key_angles source at one angles.csv row, on the signals S8 uses: elbow hidden when wrist_hidden (judge.py),
    hip/knee hidden when S6's pose.npz `hidden` is set at that near joint (stages/judge.py leg_unsure);
    else filled when <joint>_filled, else seen."""
    if joint == "elbow":
        hid = row["wrist_hidden"] == "1"
    else:
        hid = bool(pose_hidden[int(row["frame"]), HALPE26[f"{side}_{joint}"]])
    return "hidden" if hid else "filled" if row[f"{joint}_filled"] == "1" else "seen"


def final_label(judged: dict, found: dict) -> str:
    """D-judge.md "Report": a completed lift is completed_clean without an error finding, else completed_with_errors;
    failed / unknown as S8 judged."""
    if judged["lift_result"] != "completed":
        return judged["lift_result"]
    return "completed_with_errors" if any(f["severity"] == "error" for f in found["findings"]) else "completed_clean"


def report(ctx: Context) -> dict | None:
    """report.json (D-judge.md "Report"): one record per attempt S8 judged; None when S8 or S9 has not run."""
    out = ctx.out
    if not (out / "judgement.json").is_file() or not (out / "findings.json").is_file():
        return None
    judged = json.loads((out / "judgement.json").read_text())["attempts"]
    phases = {p["attempt"]: p for p in json.loads((out / "phases.json").read_text())["attempts"]}
    found = {f["attempt"]: f for f in json.loads((out / "findings.json").read_text())["attempts"]}
    warnings = json.loads((out / "clip.json").read_text()).get("warnings", [])
    with (out / "angles.csv").open() as f:
        rows = {int(r["frame"]): r for r in csv.DictReader(f)}
    side = SIDE_OF[json.loads((out / "facing.json").read_text())["facing"]]
    pose_hidden = np.asarray(np.load(out / "pose.npz")["hidden"], bool)
    recs = []
    for j in judged:
        p = phases[j["attempt"]]
        key: dict[str, dict | None] = {}
        for b in KEY_BORDERS:
            r = rows.get(p["borders"][b]["frame"]) if p["borders"].get(b) else None
            key[b] = None if r is None else {
                n: {"deg": float(r[n]), "source": angle_source(r, n, pose_hidden, side)} for n in KEY_JOINTS}
        recs.append(dict(clip=ctx.clip.stem, attempt=j["attempt"], final_label=final_label(j, found[j["attempt"]]), reason=j["reason"],
                         performed_type=j["performed_type"], intended_type=j["intended_type"],
                         phases=dict(borders=p["borders"], phases=p["phases"], bar_overhead=p["bar_overhead"]),
                         key_angles=key, metrics=found[j["attempt"]]["metrics"],
                         findings=found[j["attempt"]]["findings"], warnings=warnings))
    return dict(attempts=recs)


def stacked_overlay(out: Path) -> None:
    """overlay.mp4: the .mp4 overlays the STAGES declare and that exist, one after another in stage order, each fitted
    into 1920x1080. overlay.json records each layer's path and sha256; re-rendered when that set differs (content
    hashes, not mtimes, since cp -R does not keep mtimes)."""
    layers = [out / o for s in STAGES for o in s.outputs
              if o.startswith("overlays/") and o.endswith(".mp4") and (out / o).is_file()]
    dst, side = out / "overlay.mp4", out / "overlay.json"
    if not layers:
        return
    key = [dict(path=str(p.relative_to(out)), size=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in layers]
    if dst.is_file() and side.is_file() and json.loads(side.read_text()) == key:
        return
    args = [a for p in layers for a in ("-i", str(p))]
    scaled = "".join(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1,setsar=1,fps=30[v{i}];" for i in range(len(layers)))
    cat = "".join(f"[v{i}]" for i in range(len(layers))) + f"concat=n={len(layers)}:v=1:a=0[v]"
    tmp = out / "overlay.tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", scaled + cat, "-map", "[v]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp)], check=True)
    tmp.replace(dst)
    side.write_text(json.dumps(key, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    ctx, args = parse(argv)
    if not args.calibrate:  # a rerun that stops must not leave the last run's report behind
        for n in ("report.json", "overlay.mp4", "overlay.json"):
            (ctx.out / n).unlink(missing_ok=True)
    code = run_stages(CALIBRATE if args.calibrate else STAGES, ctx, only=args.only, start=args.start, force=args.force)
    if code == 0 and not args.calibrate:
        rep = report(ctx)
        if rep is not None:
            (ctx.out / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
            stacked_overlay(ctx.out)
    return code


if __name__ == "__main__":
    sys.exit(main())
