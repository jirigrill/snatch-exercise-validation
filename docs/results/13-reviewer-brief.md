# Reviewer brief: are the snatch phase marks right? (#13)

Self-contained instructions for an independent reviewer (agent or coach). No prior context needed.

## Task

An automatic method marks four events per rep on side-on phone videos of a snatch. Judge each mark from the images: **accept**, or **correct** (say which frame you would pick, and why). Also tick which near-side joints are really visible.

## Material (repo root = `snatch-excercise-validation/`)

- Sheets: `prototype/out/review13/<clip>_rep<k>.jpg` (6 reps: 4581 r1, 4583 r1, 4584 r1+r2, 4587 r1+r2). Columns = setup, transition, catch, lockout. Rows = 0.1 s before the event, **the marked event frame**, 0.1 s after. Cyan lines = near-side skeleton (lifter's right, nearest the camera), green ellipse and red dot = plate outline and hub.
- Form to fill in: `prototype/out/review13/checklist.md` (verdict per phase, visibility ticks).
- Numbers: `prototype/out/review13/literature_check.md`. Do not let these replace looking at the images.
- Video is 240 fps, so 0.1 s = 24 frames.

## What each event should look like

Terms follow Baumann 1988 / Harbili 2012 (`docs/papers/`). Phases are determined by the change in direction of the knee angle and the bar height.

| Event | Meaning | What you should see on the marked frame |
|---|---|---|
| setup | Start of the pull: bar leaves the floor | Bar at or just off the floor, hips low, back flat, arms straight. Bar not yet moving up noticeably. Row 3 (+0.1 s) shows the bar clearly higher. |
| transition | End of first pull / start of second pull ("double knee bend") | Bar around mid-thigh to knee height, knees have just re-bent (shins moved forward again), torso still inclined. Just before the explosive extension. Row 3 shows the body extending upward. |
| catch | Lifter received the bar overhead in the squat | Bar overhead, arms locked, lifter at or near the bottom of the squat. Row 1 shows the bar still rising or the body dropping under it. |
| lockout | Standing up, bar overhead, stable | Lifter fully upright, knees and hips extended, arms locked overhead. |

Reference values from the papers: the knee re-bends about 7–12° in the transition; bar height at end of first pull about 0.50 m; first pull about 0.42 s, second pull about 0.31 s (elite 69 kg lifters, so slower here is not an error).

## Known doubts to look at

- **setup:** our first pull measures 0.53–0.61 s vs 0.42 s in the literature, so setup may be marked before the bar actually leaves the floor. Compare the row 1 and row 2 frames: is the bar already moving in row 2?
- **catch:** it is later than the end of the second pull in the literature. Say whether the frame is the bottom of the squat, or still on the way down or up.
- Pixel scale assumes 450 mm plates (unverified); ignore metre values.

## Visibility ticks

On the **middle row** frame only. For shoulder, elbow, wrist, hip, knee, ankle of the near side: tick if you can actually see the joint. Behind the plate, behind the other limb, or out of frame = not visible. Judge the image, not the drawn skeleton dot.

## Output

Fill `checklist.md` and add a short list: per rep and phase, accept or correct with the frame you'd choose (±frames at 240 fps), plus any systematic bias (for example "setup is always about 0.1 s early"). Say how sure you are. If the images are too small to judge, say so.

## Caveat

#13 asks for the developer's own verdict. An outside review is input to that verdict, not a replacement for it.
