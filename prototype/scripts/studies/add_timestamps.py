"""Add real frame times `t` to the per-frame npz files saved before they had them.

usage: uv run python scripts/studies/add_timestamps.py [out/<clip> ...]   (default: every out/<clip>
           with a ../vids/<clip>.MOV)
rewrites out/<clip>/{person,raw_pose*,plate}.npz with `t` (s, snatch.video.timestamps)
       added; every other array is kept as it is. Files that already have `t` are skipped.

The 2026-10-05 clips are tagged 240 fps but drop frames (~200 fps on average), so
frame / fps is not the time there; analyze.py and compare_phases.py read `t`.
"""

import sys
from pathlib import Path

import numpy as np

from snatch.video import timestamps

dirs = [Path(a) for a in sys.argv[1:]] or sorted(p for p in Path("out").iterdir() if p.is_dir())
for d in dirs:
    mov = Path("../vids") / f"{d.name}.MOV"
    files = [f for f in [d / "person.npz", d / "plate.npz", *sorted(d.glob("raw_pose*.npz"))]
             if f.exists() and not f.name.endswith("_partial.npz")]
    if not mov.exists() or not files:
        continue
    t = timestamps(str(mov))
    rate = (len(t) - 1) / t[-1]
    for f in files:
        with np.load(f, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        if "t" in arrays:
            continue
        n = len(next(arrays[k] for k in ("keypoints", "bbox", "hub_y") if k in arrays))
        assert n == len(t), f"{f}: {n} frames, video has {len(t)}"
        np.savez_compressed(f, allow_pickle=False, **arrays, t=t)
        print(f"{f}: t added ({rate:.1f} fps on average)", flush=True)
