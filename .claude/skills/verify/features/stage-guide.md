# Stage guide

What each pipeline stage does and what to look for in its images. `publish_evidence.sh` copies a stage's section
(heading = the comment's title, body as is) into the PR comment under that stage, so the reader reads it next to the
images. One `## <stage name> · <title>` section per stage; the stage name is the key (`snatch.stages`). Keep the first
line `What it does: …` (one plain sentence) and one bullet per image stem under `What to look for:`. A new stage adds its
section here (the publish script fails on a shown stage without one).

`<name>_sheet.jpg` = 8 evenly spaced frames of `overlays/<name>.mp4`. `<name>_worst.jpg` = the frames the stage scores
worst on (from `<name>.worst`: line 1 clip frames, line 2 by what, line 3 each one's frame in the mp4); picked only among
the frames the overlay draws (every 4th), so the label on the image is the frame on line 1. Evenly spaced frames miss the
frames where a stage is wrong (#56: the airborne f1695-1698 never showed up), so sheets.md names every worst frame and
says what is wrong or right there.

## S-1 · Probe the clip
What it does: reads the clip's size, frame rate and every frame's time, and stops when the clip is unusable.
What to look for:
- `0_clip_sheet`: 6 frames of the clip, in order. The lifter is in view, upright, from the side; no black or frozen frames.

## S0 · Check the athlete
What it does: checks the athlete has a height and a leg skeleton before any heavy stage runs (no images).
What to look for:
- Nothing to see; the stage writes no file. A stop here is exit 7 (no height) or 2 (no skeleton).

## S1 · Find the lifter
What it does: draws a box around the lifter on every frame (the detector runs every few frames, the frames between are interpolated).
What to look for:
- `1_person_sheet`: the box sits on the lifter in every phase; thick = detected, thin = interpolated, red = across a detection the detector missed.
- `1_person_worst`: the detector runs that missed the lifter (only when there are any). Say what the box does on each.

## S2 · Track the plate
What it does: follows the near plate's rim and hub on every frame and checks the track (found on most of the lift, size steady).
What to look for:
- `plate_check`: zoomed crops around the plate at about 18 frames. The ring must sit on the rim: green = fitted outline, yellow = the Hough circle itself (fit failed), red dot = hub.
- `bar_path`: left, the hub path over the first frame (colour = time); right, hub y and x over time. One smooth path, no jumps.
- `2_plate_sheet`: outline on the plate rim; green = the sanity check passed, orange = not; the trail = hub over the last 0.5 s.
- `2_plate_worst`: the frames where px_per_m is farthest from its median (or no plate inside the moving span). The ring should still sit on the rim; say if not.

## S3 · Find the attempts
What it does: cuts the clip into attempts from the hub's height above the floor (a pull that took the hub up to the athlete's knee height counts).
What to look for:
- `attempts`: hub height over time with the red knee gate, orange candidate line and blue rest line. Attempts green (dot = peak, must clear the red gate), window padding grey, not_a_pull orange, key frames as `f<frame>` lines; liftoff and floor lines sit on the blue rest line.
- `3_attempts_sheet`: banner "Attempt k of n" inside an attempt, other frames dimmed, plate ring + hub, hub height above the floor.
- `3_attempts_worst`: the key frames of every attempt: liftoff and back on the floor (hub about 0.23 m = plate radius), peak (must clear the knee gate), and the highest not_a_pull's peak.

## S4 · Pose the lifter
What it does: finds the lifter's body keypoints on the frames of the attempt windows and which way they face (which leg is the near one).
What to look for:
- `4_pose_sheet`: skeleton on the lifter inside the attempt windows only; the near leg green on a right-facing clip.
- `4_pose_worst`: the lowest near-knee scores among posed frames. Say whether the skeleton is right or off (plate in front of the knee is expected).

## side · Near-side check
What it does: checks the athlete has a skeleton for the side the clip was filmed from (no images).
What to look for:
- Nothing to see; a clip filmed from the other side than the calibration stops here with exit 2.

## S5 · Scale the leg skeleton
What it does: measures how much bigger or smaller the athlete's legs look in this clip than in the calibration (one factor per clip, plus a thigh and a shank multiplier on it), from frames where the hip, knee and ankle are visible.
What to look for:
- `5_scale`: up to three frames used (first, middle, last) with the near leg hip-knee-ankle in green, and for the standing method the measured hip-ankle line in yellow; the title gives factor, method and frame count. The green leg must sit on the real leg, the yellow line must be straight.
- `scale.json` (no image): `factor`, `method` (standing, visible_knee, none), `n_frames`, `spread`; `thigh_factor` and `shank_factor` are multipliers on the scaled table's thigh and shank, 1.0 = the table as is; `segment_frames` / `segment_source` = frames used for them. Method none = no usable frame (the plate covers the hip), factor null.

## S6 · Fill the hidden knee
What it does: where the plate hides the near knee, replaces RTMPose's guess with a knee rebuilt from the hip, the ankle and the athlete's calibrated leg lengths (scaled by S5).
What to look for:
- `6_filled_sheet`: zoomed on the attempt windows. Grey = RTMPose's near leg (dot at its knee), purple = the filled knee with its thigh and shank, yellow-orange ring = a hidden joint that was not filled, white = the rest of the skeleton (the far leg is not drawn), green = plate outline. Where the plate covers the knee, purple should sit where a knee plausibly is, with a bend that fits the pose; grey wanders there.
- `6_filled_worst`: the frames the stage scores worst on (see `6_filled.worst` for the criterion). Say per frame whether the purple knee is plausible.

## S7 · Angles and phases
What it does: per attempt, smooths the near side, computes hip, knee and elbow angles, and marks 7 borders that cut the attempt into 8 phases (starting_position, first_pull, transition, second_pull, turnover, catch, recovery, hold). Rules: `docs/results/37-s7-phases.md`. A border it cannot find is null; no bar_overhead (hub above the nose for >= 0.25 s) = a failed pull, so bar_lowest and standing are null.
What to look for:
- `7_phases_sheet`: zoomed on the attempt windows, near-side skeleton, plate and hub trail; the top-left text gives attempt, phase name and hip/knee/elbow; an orange banner names a border on its frame. Liftoff = the bar just leaving the floor; full_extension = the legs straight at the top of the pull; bar_peak = the hub at its top after that; bar_lowest = the hub at the bottom of the catch; standing = upright under the bar.
- `angles.png`: per attempt hip (blue), knee (green), elbow (purple) in degrees, hub height (orange, right axis), dashed line + label per border, phases shaded, red bar at the bottom = the S6-filled knee. Borders must sit at the knee peak (full_extension), a knee dip (deepest_rebend), the hub's top (bar_peak) and dip (bar_lowest).
- `phase_sheet.jpg` (no worst sheet): one row per attempt, one tile per border in order (liftoff, first_knee_max, deepest_rebend, full_extension, bar_peak, bar_lowest, standing), "none" = null. The yellow line is shoulder-hip-knee-ankle, the red dot the hub; `grabs/` holds the full-size tiles.
- `phases.json` / `angles.csv` (no image): borders as {frame, t, filled, hidden}; `bar_overhead` {start, end}; csv: one row per posed frame, `*_filled` = S6 mask, `wrist_hidden` = wrist inside the plate outline. A null `deepest_rebend` / `first_knee_max` is allowed (no >= 3 deg re-bend); null `bar_overhead` is right on T3 and T7 only. The `hold` phase ends where the hub falls > 5 cm below its median since standing (else at the bar_overhead end).

## S8 · Judge
What it does: per attempt, reads S7's borders and phases and gives performed_type (muscle / power / squat / unknown), intended_type (+ source) and lift_result (completed / failed / unknown + reason). Checks in order: no_overhead, elbow_unlocked (elbow < 165° on hold frames with the wrist seen), no_standup (no S7 standing), hold_short (S7 hold < 0.5 s), type_mismatch, low_confidence (no fail but a check unsure). Rules: `.scratch/plan/D-judge.md`.
What to look for:
- `judgement_sheet.jpg`: one row per attempt, tiles at bar_lowest, standing, mid-hold, bar_overhead end; grey tile = that border is null. The verdict banner is green COMPLETED, red FAILED + reason or grey UNKNOWN; each check's value / threshold is listed; the yellow WORST mark is the deciding frame of a check. Say if the verdict matches what the tiles show (arms, legs, catch depth).
- `8_judgement` overlay: type + verdict at the end of each attempt.
- `judgement.json` (no image): `checks{}` per attempt with value, threshold, unit, pass / fail / unsure / skipped, frames; `evidence_frames` = the deciding check's frames. On the test clips the elbow check is unsure on every hold (wrist under the plate), so completed lifts come out unknown: low_confidence.

## S9 · Bar-path metrics (+ report)
What it does: per attempt, 6 measurements of the plate hub path on S7's borders (no thresholds yet): pull1_away_cm (max forward drift liftoff→first_knee_max), pull2_toward_cm (max sweep back first_knee_max→full_extension), loop_away_cm (max forward full_extension→bar_lowest), peak_height_pct (hub rise liftoff→bar_peak, % of athlete height), drop_under_cm (bar_peak→bar_lowest drop), catch_x_cm (hub x bar_lowest − liftoff). x + = away from the lifter (facing.json). cm via the window's median plate px_per_m. Rules: `.scratch/plan/D-judge.md` "S9 findings".
What to look for:
- `findings_sheet.jpg`: one row per attempt, the liftoff frame cropped to the hub path, the path coloured by S7 phase, each metric a numbered arrow (horizontal for x metrics at the `@` frame's height, vertical for the two height metrics) with its value; right tile lists all 6 with frames or the missing borders. Say if each arrow starts and ends where the path is at those borders.
- `findings.json` / `report.json` (no image): null metric = `missing` names the absent borders (T1/T3/T7: no first_knee_max → 1–2 null; T3/T7: no bar_overhead → 4–6 null). report.json final_label/reason = judgement.json.
- `overlay.mp4`: all stage overlays one after another (1080p, 30 fps).

## C3 · Fit the leg skeleton
What it does: measures the athlete's leg lengths against hip-ankle distance on the bar-only clip and stores them as the skeleton, then rebuilds the knee from them as a self-test.
What to look for:
- `calibration_overlay_sheet`: green = RTMPose (smoothed, as fitted), magenta = the same pose with the near knee rebuilt wherever the leg is bent enough (a bar-only clip has no plate). Magenta should cover green; red border = more than 20 px apart.
- `calibration_overlay_worst`: the rebuilt knee farthest from RTMPose's. Say how far and why.
- `calibration.json` (no image): the rebuilt knee's median offset in the bent-leg frames must be under 10 px.
