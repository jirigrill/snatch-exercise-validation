# Recording protocol: made vs missed sensitivity set (#20)

Written 2026-10-02, **before any clip in this set exists**. Purpose: enough heavy snatches, with honest made/missed labels, to test whether any measurable marker from `research/11-technique-markers.md` separates a lifter's made and missed lifts beyond normal rep-to-rep spread. Nothing here changes the #11 clip set, its roles or its rule.

Updated 2026-10-05 after `research/12-feasibility-grill.md`. This set is now also **gate 1 (D3)**, the go/no-go test for the whole app: two coaches label every miss blind, and the app's causes are scored against their labels. Before this set is recorded, the spike session below (D1, D2) fixes the camera view and the final cause list.

## Target

| Item | Per lifter | Why |
|---|---|---|
| Lifts | 25–40 snatches, over 3–5 sessions | Enough made lifts to estimate normal spread at each load |
| Misses | **at least 8**, ideally 12+ | Fewer than 8 and the test can only report "too few". Gate 1 needs 2 × 8 = 16 in total |
| Load | 70–95% of current 1RM; most lifts 85–95% | Misses cluster at heavy loads; the load effect must be modelled, so light lifts are needed too |
| Lifters | **2** for gate 1 (1 is enough for the marker test alone) | One lifter answers "does it work for this person"; two show whether it repeats |
| Variant | **Squat snatch from the floor only** (the spike session may use power snatches) | The app's scope is the full snatch (`research/12-feasibility-grill.md`). The #11 set is power snatches only; variants are never pooled (same as `clip-log.md`) |

Don't chase misses: lift normally at heavy loads and take the misses that come. Deliberate misses don't count as misses. Log them as `miss_deliberate` and leave them out of the analysis.

## Camera set-up (same every session)

1. Phone: iPhone 15 Pro, **240 fps** slow-motion, 1080p. Downsampling to lower rates is done afterwards if #15 allows it. Recording at a lower rate can't be undone.
2. Tripod, **camera on the lifter's right**. The view is the one that wins the spike (D1): side-on (lens axis along the bar, as in the main set) unless an oblique view passes. Use **one view for the whole set**; never mix views.
3. Lens at about hip height, **D = 4 m from the bar centre**, aimed at the bar centre. Set the position with the 5 m tape as in § Positioning the camera. Mark the tripod feet with tape and keep the same spot every session.
4. Phone **level**: use the camera's level indicator. A 1° tilt shifts the bar by about 1.7 cm per metre of rise (marker doc N4).
5. Frame: the whole lifter and the near plate stay in frame from setup to lockout, with headroom above the bar at full lockout and floor below the feet.
6. Near side: the **outermost large plate must be a 450 mm bumper** (scale assumption in `plate.npz`). Change plates go inside the bumpers. Collars should be a plain colour.
7. Lighting: steady. Avoid a skylight or window behind the lifter, which caused the exposure shift in 4586. Keep the background uncluttered and no one else in frame.
8. Don't move the tripod during a session. If it gets bumped, re-level it and log a note.

## Positioning the camera (5 m tape, no protractor)

1. Tape-mark the bar centre and a line along the bar's axis on the platform. Also tape-mark the lifter's foot position.
2. **Side-on mark:** on the bar-axis line, extended to the lifter's right, 4 m from the bar centre.
3. **Oblique mark:** the point that is 4 m from the bar centre **and** at the chord distance from the side-on mark, on the lifter's front side:

| Angle | Chord from the side-on mark |
|---|---|
| 30° | 2.07 m |
| 45° | 3.06 m |

±5° is enough. The real angle is measured afterwards from the plate ellipse (axis ratio ≈ cos of the viewing angle). What matters is that the spot can be repeated.

## Spike session (D1 view, D2 arm bend), before the gate set

One phone, one session, a light to moderate load (the same load for all sets). Power snatches are fine here: D1 and D2 test the pull, which is nearly the same in both variants. The deep squat catch is tested in the gate set.

- **D1 views:** interleave sets of 3–5 reps: side → 30° → 45° → side → 30° → 45°, so fatigue spreads evenly across the views.
- **D2 arm bend:** in the side-on sets, alternate reps pulled with straight arms and reps with a deliberate early arm bend. Log which is which in `notes`.
- **Static metric test:** from each camera position, film the loaded bar standing still, then rolled a measured 50 cm along the floor, then still again. No lifter is needed.
- Log the spike clips in the same log with `session` = `SP1` and the view in `notes`. These clips are never part of the gate.

**D1 go:** an oblique view shows the near hip and knee at the transition, or the wrist in the pull, **and** the rectified hub moves 50 ± 1 cm in the static test. Otherwise side-on stays.

**D2 go:** the 2D shoulder-to-hub distance separates the bent-arm and straight-arm reps beyond rep-to-rep spread. Otherwise early arm bend leaves the cause list.

After the spike, write the chosen view and the final cause list into this file **before** the first gate session.

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

## Coach labels (gate 1)

- **Two coaches** label every lift independently: misses for the cause check, made lifts for the false-alarm check.
- Each coach sees only the video, with no app output, marker values or the other coach's labels. The lifter's log is hidden too, except `load_kg`.
- Each coach writes their own file: `docs/coach-labels-C1.csv` and `docs/coach-labels-C2.csv`.

| Column | Values |
|---|---|
| `clip` | as in the log |
| `verdict` | made lifts only: `clean` / `flawed`; blank for misses |
| `cause` | one cause from the final closed list (`research/12-feasibility-grill.md` §4), or `outside_list` / `cant_tell`; blank for a `clean` made lift |
| `cause_2` | optional second cause, same values |
| `notes` | free text |

The cause engine runs the same way on every lift, made or missed, and outputs a cause or none. Its output is produced **before** the coach files are opened, and committed first, so the scoring can't be tuned to the labels.

## Gate 1 rule (fixed in advance)

- **Coverage:** the share of misses where the app names a cause from the list.
- **Agreement:** the app's primary or second cause matches the coach's cause.
- **False alarm:** the app outputs a cause on a made lift that both coaches label `clean`. In the app, made lifts show only "deviations from your best reps", never a cause; this check makes sure those deviations aren't noise.

**Go** needs all four:
1. coverage ≥ **13/16** misses;
2. app–coach agreement ≥ coach–coach agreement;
3. agreement ≥ 80% on misses where both coaches give the same cause;
4. false alarms on ≤ 20% of the made lifts both coaches label `clean`.

**≤ 12/16 coverage, or any other condition failing, means no-go, and the project ends.** The grey zone 11–12 also counts as no-go.

Misses where the coaches disagree are reported separately as "ambiguous". With 16 misses, 13/16 is consistent with a true rate of about 57–93%: the gate catches a clear failure, it doesn't prove 80%.

## Storage

Store the originals in `vids/sensitivity/` and the spike clips in `vids/spike/` (both gitignored, never edited), with the same naming as `vids/`. Commit only the log and the session notes.
