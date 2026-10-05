"""Build the 120/60/30 fps ladder for every clip and verify it frame by frame.

usage: uv run python scripts/build_ladder.py ../vids [clip ...]
writes ../vids/ladder/<clip>_<fps>fps.MOV (gitignored, next to the
       originals, which are only read), out/ladder.json
"""

import json
import sys
from pathlib import Path

from snatch.ladder import STEPS, build, frame_hashes, verify
from snatch.video import probe

vids = Path(sys.argv[1])
clips = sys.argv[2:] or sorted(p.stem for p in vids.glob("*.MOV"))
(vids / "ladder").mkdir(exist_ok=True)
report_path = Path("out/ladder.json")
report = json.loads(report_path.read_text()) if report_path.exists() else {}

for clip in clips:
    src = str(vids / f"{clip}.MOV")
    info = probe(src)
    original = frame_hashes(src)
    entry = {"frames_240": len(original), "nb_frames_tag": info.n_frames,
             "rotation": info.rotation, "rates": {}}
    for fps, step in STEPS.items():
        dst = vids / "ladder" / f"{clip}_{fps}fps.MOV"
        method, hashes = build(src, str(dst), step, original)
        built = probe(str(dst))
        entry["rates"][fps] = {
            "file": f"vids/ladder/{dst.name}", "step": step, "method": method,
            "frames": len(hashes), "expected": len(original[::step]),
            "pixel_identical": verify(original, hashes, step),
            "rotation": built.rotation, "mbytes": round(dst.stat().st_size / 1e6, 1),
        }
        print(clip, fps, entry["rates"][fps], flush=True)
    report[clip] = entry
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
