"""Print what is inside a .npz file (raw_pose.npz, plate.npz, ...).

usage: uv run python scripts/show_npz.py out/<clip>/plate.npz            one line per array
       uv run python scripts/show_npz.py out/<clip>/plate.npz hub_y      values of one array
       uv run python scripts/show_npz.py out/<clip>/raw_pose.npz keypoints 1000:1010
reads  the .npz file; writes nothing
"""

import sys

import numpy as np

np.set_printoptions(precision=2, suppress=True, linewidth=120, threshold=200)

data = np.load(sys.argv[1])
if len(sys.argv) == 2:
    width = max(map(len, data.files))
    for k in data.files:
        a = data[k]
        line = f"{k:<{width}}  {str(a.dtype):<8} {str(a.shape):<16}"
        if a.ndim == 0:
            line += f" = {a.item()!r}"[:100]
        elif a.size and a.dtype.kind in "fiub":
            x = a.astype(float)
            ok = ~np.isnan(x)
            line += f" min {np.nanmin(x):.4g}  max {np.nanmax(x):.4g}" if ok.any() else " all NaN"
            if not ok.all():
                line += f"  NaN {1 - ok.mean():.1%}"
        print(line)
else:
    a = data[sys.argv[2]]
    if len(sys.argv) > 3:
        start, end = (int(x) if x else None for x in sys.argv[3].split(":"))
        rows = range(*slice(start, end).indices(len(a)))
        for i in rows:
            print(i, a[i] if a.ndim < 3 else "\n" + str(a[i]))
    else:
        print(a.item() if a.ndim == 0 else a)
