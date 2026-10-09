# Plate and bar-path tracking

## Sub-features
- Near-plate circle/ellipse fit per frame -> plate.npz, plate.csv
- Check image with outline + hub at ~18 frames -> plate_check.jpg
- Bar path plot -> bar_path.png; `--overlay` -> overlay_plate.mp4

## How to get to it (user POV)
Run after pose; the hub height defines phases v2 and the bar path.

## Driving it with the shell harness
```
cd prototype && uv run python scripts/track_plate.py <clip> <out> [ellipse] [--radius LO:HI]
```
Proof: log ends `status ok (vertical travel ~1.7 m)` (clip-dependent) and `found N/N frames`; open plate_check.jpg: outline on the near plate in every tile, hub at plate centre.

## Gotchas
- Off-axis clips (30deg/45deg) need `ellipse`; 4 m clips need `--radius 70:140`, else it follows medicine balls or the dumbbell rack.
- Bar-only clips have no plate: don't run.
- `status` other than ok means the plate check failed; phases fall back to v1.
