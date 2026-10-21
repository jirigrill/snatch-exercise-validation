"""Contact sheets of raw clip frames, each cell labelled with its frame index.

For blind marking (e.g. phase borders) without seeing any pipeline output.
Frames are decoded with snatch.video.frames, so the labels equal the pipeline's
frame indices.

Run from prototype/:
  uv run python ../.claude/skills/verify/scripts/mark_strips.py CLIP.MOV \
      --start 250 --end 330 --step 4 --out DIR [--crop x0,y0,x1,y1] \
      [--cols 4] [--rows 3] [--cell-width 480] [--times frame_times.npy]
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from snatch import video


def label(cell: np.ndarray, text: str) -> None:
    scale = max(0.8, cell.shape[1] / 400)
    th = max(2, round(scale * 2))
    (w, h), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, th)
    cv2.rectangle(cell, (0, 0), (w + 12, h + base + 12), (0, 0, 0), -1)
    cv2.putText(cell, text, (6, h + 6), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), th, cv2.LINE_AA)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip")
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True, help="exclusive")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--crop", help="x0,y0,x1,y1 in rotated-frame pixels")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cell-width", type=int, default=480)
    ap.add_argument("--times", help="frame_times.npy: time in s per frame")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    times = np.load(a.times) if a.times else None
    crop = [int(v) for v in a.crop.split(",")] if a.crop else None
    wanted = set(range(a.start, a.end, a.step))
    per = a.cols * a.rows
    cells: list[tuple[int, np.ndarray]] = []
    written: list[Path] = []

    def flush() -> None:
        if not cells:
            return
        h, w = cells[0][1].shape[:2]
        sheet = np.zeros((h * a.rows, w * a.cols, 3), np.uint8)
        for i, (_, c) in enumerate(cells):
            r, k = divmod(i, a.cols)
            sheet[r * h:(r + 1) * h, k * w:(k + 1) * w] = c
        p = out / f"strip_{cells[0][0]}-{cells[-1][0]}.jpg"
        cv2.imwrite(str(p), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
        written.append(p)
        cells.clear()

    for i, fr in enumerate(video.frames(a.clip, stop=a.end)):
        if i not in wanted:
            continue
        if crop:
            x0, y0, x1, y1 = crop
            fr = fr[y0:y1, x0:x1]
        scale = a.cell_width / fr.shape[1]
        cell = cv2.resize(fr, (a.cell_width, round(fr.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        text = f"f{i}" + (f"  {times[i]:.3f}s" if times is not None and i < len(times) else "")
        label(cell, text)
        cells.append((i, cell))
        if len(cells) == per:
            flush()
    flush()
    for p in written:
        print(p)


if __name__ == "__main__":
    main()
