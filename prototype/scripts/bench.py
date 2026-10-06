"""Time YOLOX-x detector and RTMPose-x separately, per execution provider.

Recorded result (2026-10-01, M4): YOLOX-x fails on CoreML (static output
shape rank mismatch), so the detector must run on CPU.
"""

import sys
import time

from snatch.person import load_detector
from snatch.pose import load_model
from snatch.video import frames, probe

clip = sys.argv[1]
info = probe(clip)
imgs = [f.copy() for i, f in enumerate(frames(clip, info))
        if i >= 1800 and i % 20 == 0 and i < 2000]


def timed(fn, n):
    out = fn()  # warm-up
    t0 = time.time()
    for _ in range(n):
        out = fn()
    return (time.time() - t0) / n, out


det = load_detector()
t_det, boxes = timed(lambda: det(imgs[0]), 5)
print("det cpu", round(t_det, 3), "s/frame", boxes)

for device in ("cpu", "mps"):
    try:
        pose = load_model(device)
        t, (kps, scores) = timed(lambda: pose(imgs[0], bboxes=list(boxes)), 10)
        provider = pose.session.get_providers()[0]  # type: ignore[attr-defined]
        print("pose", device, provider, round(t, 3), "s/frame", kps.shape)
    except Exception as e:
        print("pose", device, "FAILED", repr(e)[:300])
