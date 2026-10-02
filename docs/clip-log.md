# Clip log — repeatability prototype (#11)

Originals in `vids/` (gitignored, never edited). All: HEVC, 1920x1080, 240 fps, rotation tag -90 (portrait). Camera on lifter's right side. Load for plate clips: bar + 5 kg plate each side.

| Clip | View | Reps | Load | Frames | Duration | Session* | Variant† | Role |
|---|---|---|---|---|---|---|---|---|
| IMG_4578 | side | 1 | bar only | 2943 | 12.3 s | hoodie | power | baseline (no occlusion); contains standing hold (static-pose proxy) |
| IMG_4579 | side | 0 (pull to standing hold, no snatch) | bar + 5 kg | 2553 | 10.6 s | hoodie | — (no snatch) | **static-pose clip**: standing hold, bar at hips, plates (same occlusion as main set) |
| IMG_4581 | side | 1 | bar + 5 kg | 2498 | 10.4 s | hoodie | power | main set |
| IMG_4583 | side | 1 | bar + 5 kg | 2644 | 11.0 s | hoodie | power | main set |
| IMG_4584 | side | 2 | bar + 5 kg | 3953 | 16.5 s | hoodie | power ×2 | main set |
| IMG_4587 | side | 2 | bar + 5 kg | 3837 | 16.0 s | grey tee | power ×2 | main set |
| IMG_4585 | off-axis (right-back) | 1 | bar + 5 kg | 2455 | 10.2 s | hoodie | power | degraded |
| IMG_4586 | off-axis (right-back) | 2 | bar + 5 kg | 4180 | 17.4 s | grey tee | power ×2 | degraded |

\*Session inferred from clothing/lighting (hoodie vs grey tee; 4586/4585 skylight lighting, exposure shift mid-4586). Confirm.

†Variant from visual check of 0.25 s frame sheets (agent, 2026-10-01), **confirmed by the lifter 2026-10-02**: every rep has a knee dip under the bar but no deep squat catch. The pipeline also reports knee angle at the catch per rep (4584: 107°, 102°). Spread is only computed within one variant — mixed variants would inflate the catch SD with technique, not model, variation.

Pooled reps: main set 6 side-on plate reps; degraded 3 off-axis plate reps; baseline 1 bar-only rep.

## Model scope
All candidate pose models are run on these clips to compare performance, including ones whose licences block commercial use (see `research/09-pose-model-licensing.md`). Blocked-model results are research-only and must be labelled as such.

## Known limits
- No dedicated static standing clip. Best proxy: standing hold in 4579 (plates, same session): **1.43 s, 344 frames, f1147–f1490** (hub height within 2 cm; see `results/14-ladder-and-plate.md`). Secondary: 4578 (bar only), overhead lockout holds (quasi-static, includes real sway).
- Main set mixes two sessions (hoodie / grey tee).
- n = 6 reps: clear pass/fail only, not close calls.
- Near plate occludes lower legs at setup/pull in side-on plate clips.
