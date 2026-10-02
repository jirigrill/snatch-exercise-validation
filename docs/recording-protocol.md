# Recording protocol: made vs missed sensitivity set (#20)

Written 2026-10-02, **before any clip in this set exists**. Purpose: enough heavy snatches, with honest made/missed labels, to test whether any measurable marker from `research/11-technique-markers.md` separates a lifter's made and missed lifts beyond normal rep-to-rep spread. Nothing here changes the #11 clip set, its roles or its rule.

## Target

| Item | Per lifter | Why |
|---|---|---|
| Lifts | 25–40 snatches, over 3–5 sessions | Enough made lifts to estimate normal spread at each load |
| Misses | **at least 8**, ideally 12+ | Fewer than 8 and the test can only report "too few" |
| Load | 70–95% of current 1RM; most lifts 85–95% | Misses cluster at heavy loads; the load effect must be modelled, so light lifts are needed too |
| Lifters | 1 minimum, 2 preferred | One lifter answers "does it work for this person"; two show whether it repeats |
| Variant | **One variant per lifter**, squat snatch preferred | The #11 set is power snatches only; variants are never pooled (same as `clip-log.md`) |

Don't chase misses: lift normally at heavy loads and take the misses that come. Deliberate misses don't count as misses. Log them as `miss_deliberate` and leave them out of the analysis.

## Camera set-up (same every session)

1. Phone: iPhone 15 Pro, **240 fps** slow-motion, 1080p. Downsampling to lower rates is done afterwards if #15 allows it. Recording at a lower rate can't be undone.
2. Tripod, **camera on the lifter's right**, lens axis perpendicular to the bar (side-on, as in the main set). No off-axis takes in this set.
3. Lens at about hip height. Measure the distance from the lens to the bar's start line, then write it down and keep it the same every session.
4. Phone **level**: use the camera's level indicator. A 1° tilt shifts the bar by about 1.7 cm per metre of rise (marker doc N4).
5. Frame: the whole lifter and the near plate stay in frame from setup to lockout, with headroom above the bar at full lockout and floor below the feet.
6. Near side: the **outermost large plate must be a 450 mm bumper** (scale assumption in `plate.npz`). Change plates go inside the bumpers. Collars should be a plain colour.
7. Lighting: steady. Avoid a skylight or window behind the lifter, which caused the exposure shift in 4586. Keep the background uncluttered and no one else in frame.
8. Don't move the tripod during a session. If it gets bumped, re-level it and log a note.

## Per lift

- **One snatch per clip.** Start recording before the setup and stop after the bar is set down.
- Fill in the log row **straight after the lift, before watching the video**. The lifter's own call comes first; the "made" label follows the rule below, not the lifter's feeling.

## Log (one row per clip)

Keep this in `docs/sensitivity-log.csv`. It is created with the first session and filled in at the gym.

| Column | Values |
|---|---|
| `clip` | iPhone file number, e.g. `IMG_4712` |
| `date`, `session` | date; session id (S1, S2 …) |
| `lifter` | L1, L2 (no names) |
| `bodyweight_kg` | at the session |
| `load_kg`, `pct_1rm` | bar + plates; percentage of the lifter's current best snatch (state which 1RM in the session note) |
| `attempt_in_session` | 1, 2, 3 … (fatigue) |
| `variant` | `squat` / `power` |
| `result` | `made` / `miss` / `miss_deliberate` |
| `miss_type` | `forward` (bar dropped in front) / `behind` (bar dropped behind) / `pressout` / `no_turnover` (the bar never gets overhead) / `other` (write it in the notes); blank if made |
| `self_rating` | lifter's feel, 1–5, given **before** watching the video |
| `notes` | anything unusual: foot slip, camera bumped, someone in frame |

**Made rule:** the bar is caught overhead with locked arms, held stable at lockout and set down under control, with no press-out. A press-out is logged as `miss` with type `pressout`, even if the lifter stands up with it. This is a fixed rule, so it doesn't depend on the lifter's feel. `self_rating` is recorded separately to check how often the lifter's own feel disagrees with it.

## Exclusions (only for technical reasons)

A clip is excluded only for one of these reasons, and the decision is logged **before any marker values are seen**:

- the lifter or the near plate goes out of frame;
- the plate is not tracked (no hub);
- the camera moved;
- another person blocks the lifter;
- the file is corrupt.

Never exclude a clip because of how its numbers look.

## Storage

Store the originals in `vids/sensitivity/` (gitignored, never edited), with the same naming as `vids/`. Commit only the log and the session notes.
