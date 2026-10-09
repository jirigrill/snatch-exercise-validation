# 11 — Snatch technique markers: what can a side-on iPhone video measure?
Ticket: [#18](https://github.com/jirigrill/snatch-exercise-validation/issues/18) · Status: feasibility map only, nothing built · Date: 2026-10-02

## Bottom line

- **45 markers** of snatch technique, from `docs/papers` and coaching sources. **26 are measurable now, 17 need more work, and 2 are not feasible** from a side-on view.
- **What is measurable now:**
  - almost the whole bar side: path type, horizontal displacements, peak height, drop, velocity and phase timing, all from the plate hub;
  - trunk angle at liftoff;
  - joint angles at the catch and lockout.
- **What needs more work:** nearly every lower-limb angle in the pull, plus every elbow marker.
  - The near plate hides the knee, hip and ankle at setup and transition, and the wrist in every frame (#12, #13, #14).
  - The usual missing part is a seen keypoint at that moment. Some markers also need a new event (end of first pull, peak extension), foot keypoints or a signed hip angle.
- **Not feasible side-on:**
  - bar–body distance, because the place where bar and body meet is inside the plate outline;
  - all frontal-plane markers.
- **The catch:** the only within-lifter success/fail differences in `docs/papers` are knee and hip angle at the end of the second pull, and centre-of-gravity speed in the catch (Mastalerz 2019).
  - Bar velocity, peak height, drop and phase durations did **not** differ.
  - So the side-on pipeline measures well the part that doesn't separate made from missed lifts. The part that does only becomes measurable with more work. That matches the note in #11.

## How to read this

**Tags.**
- **[V]** = read this session in the PDF in `docs/papers`. Page is the printed journal page, with the PDF page where they differ.
- **[S]** = taken from another repo doc (`10a`, `10b`, `05`, results docs) without re-reading the original.
- **[C]** = **coaching consensus**: a coaching text or common cue, not a measurement study. Mostly via `10b`.
- **[I]** = my inference.

**Status rule.**
- **now**: every input already exists as a pipeline field. The keypoints it needs are visible at that moment in the side-on main set (#13 visibility table). Computing it is only arithmetic or an extremum on existing fields; no new model and no new phase rule.
- **more work**: one named part is missing: a hidden keypoint, a new event, a missing input or a different model.
- **not feasible**: a single side-on 2D view can't supply it (frontal plane, far side), or the region is always hidden.

**Field shorthand.**
- `A:` = column in `prototype/out/<clip>/angles.csv`.
- `P:` = field in `plate.npz`.
- `E:` = event frame in `phases_v2.json`: `setup`, `transition`, `catch`, `lockout`, `overhead_start`, `overhead_end`. These are v2 marks, frozen and accepted in #13.
- `vy` = upward bar speed = −Δ`hub_y` · `fps` ÷ `px_per_m`, as already computed in `scripts/studies/check_phases_literature.py`.
- **bar catch** = the lowest hub point after peak height (Shah, PDF p. 8). It is **not** `E:catch`, which is the lowest hip; the two are −19…+31 frames apart (#13).
- Image axes: the lifter faces +x (camera on the lifter's right, `snatch/angles.py`), so **"toward the lifter" = −x**. y grows downward.

**Needed input shorthand.**
- **kp** = keypoints.
- **S** = side-on view: camera on the lifter's right, perpendicular, phone level.
- **scale** = `px_per_m`, valid in the plate plane (note N3).
- **fps**: only 240 is checked for the hub (#14). #15 tests joint angles at 120/60/30. The fps figures below are [I], from the arithmetic in `05`.

**Occlusion shorthand (#13, side-on main set, near side).**
- Not visible:
  - setup: wrist, knee, ankle (knee borderline);
  - transition: wrist, hip, knee;
  - catch: wrist (inside the plate outline);
  - lockout: wrist (at the rim).
- Model confidence doesn't track this: the hidden transition knee scored 0.73 (#12).
- Hub (#14):
  - side-on: found in 100% of frames, jitter 0.7–1.6 px ≈ 1–2 mm;
  - off-axis 20261001_6_jiri_v1_powersnatch_5kg_1rep_success_-30deg/20261001_7_jiri_v2_powersnatch_5kg_2rep_success_-30deg: unreliable on the floor (setup, pull, after the drop);
  - 20261001_1_jiri_v1_powersnatch_bar_1rep_success_0deg: no plate, so no hub.
- #13 checked only the four v2 events. Visibility at other moments (end of first pull, peak extension) is unchecked.

## The table

| # | Marker | Definition (what good looks like) | Source | Status | Field now / missing part | Needed input | Occlusion limit (#12, #13, #14) |
|---|---|---|---|---|---|---|---|
| **A** | **Positions and angles per phase** | | | | | | |
| A1 | Trunk angle at liftoff | Back inclination as the bar breaks the floor. Soviet norm: trunk 25–50° to the platform (≈ 40–65° from vertical). This is a between-lifter range, not a tolerance | [C] Roman, Drechsler via `10b` rows 1, 9 | **now** | `A:trunk_smooth` at `E:setup` | kp r_shoulder, r_hip · S, level · fps: #15 decides | Shoulder and hip visible at setup (#13) |
| A2 | Knee angle at liftoff | Knee included angle at the start of the lift: 70.9 ± 16.0° (men), 68.6 ± 8.4° (women). Coaching range 45–90° | [V] Harbili 2012, Table 3, p. 164; [C] `10b` rows 1–3 | **more work** | Missing: a seen near knee and ankle at liftoff. Options: foot-anchored knee row (#15), or a view that clears the plate (front-oblique, #16 note). `A:knee_smooth` exists but is a guess | kp r_hip, r_knee, r_ankle · S | Ankle hidden, knee borderline (#13). RTMPose puts the ankle on the hub; setup knee SD 9.4° on 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg (#12) |
| A3 | Hip angle at liftoff | Hip (shoulder–hip–knee) at the start. Success more likely with hip < 89.6° (one novice, 133 attempts) | [V] Mastalerz 2019, Fig. 4 caption, p. 74 (S position); [S] Ho 2011 via `10a` B7 | **more work** | Missing: a seen knee (the angle's distal point). `A:hip_smooth` exists | kp r_shoulder, r_hip, r_knee · S | Knee borderline at setup (#13) |
| A4 | Shoulders over or ahead of the bar at liftoff | Shoulder in front of the bar (+x) when the bar leaves the floor | [C] common cue; no numeric source in `10b` | **now** (px, one camera set-up) | `A:r_shoulder_x` − `P:hub_x` at `E:setup` | kp r_shoulder · hub · S, level · metres biased (N3) | Shoulder visible (#13). Hub as in shorthand; unreliable off-axis on the floor (#14) |
| A5 | Constant back angle through the first pull | Trunk angle changes little until the bar passes the knees. "Less trunk motion during the first pull is associated with lifting greater loads" | [V] Ahn & Kipp 2024, p. 18 (citing Kipp 2012); [C] `10b` row 17 | **now** | Range of `A:trunk_smooth` from `E:setup` to the frame where `P:hub_y` passes mean `A:l_knee_y`/`r_knee_y` (the knee height v2 already uses) | kp r_shoulder, r_hip, knees · hub · S, level · fps ≥ 60 [I] | End frame depends on a guessed knee height (#12, #13). Hip visibility between setup and transition is unchecked |
| A6 | Knee at end of first pull | Maximal knee extension before the re-bend: 146.8 ± 14.1° (men) vs 134.7 ± 3.6° (women), significant. Soviet norm 145–155° | [V] Harbili, Table 3, p. 164; [C] `10b` row 3 | **more work** | Missing: (1) a seen knee late in the first pull; (2) an "end of first pull" event (knee max between setup and transition). Today it is only computed ad hoc in `check_phases_literature.py` | kp r_hip, r_knee, r_ankle · S · fps ≥ 120 [I] | Knee behind the plate around the transition (#13), scored confidently while hidden (#12) |
| A7 | Knee re-bend depth (double knee bend) | Knee-angle drop from end of first pull to end of transition. "Approximately 12° in men and 7° in women" (Liu 2022: 10.0° made vs 5.4° missed, [S]). **Sources disagree on what is good.** "Executed quickly with a small knee flexion" and "minimal bending of the knees", against "deeper and faster knee flexion" for women | [V] Harbili, p. 164, 166, key points p. 169; [V] Mastalerz, p. 76; [V] Korayem 2010, p. 4–5 (simulation reproduces the double knee bend); [S] `10a` B7 | **more work** | Missing: an occlusion-robust knee at the transition (#15 behind-plate flag marks it; #16 mesh models; or another view). `A:knee_smooth` exists | kp r_hip, r_knee, r_ankle · S · fps ≥ 120: the dip lasts ~0.11 s, i.e. 3–4 frames at 30 fps [I] | Hip and knee behind the plate at the transition (#13). The v2 transition frame is itself found from this guessed knee (#12). #13 accepted all 6 marks (2 possibly 0.04–0.08 s late) |
| A8 | Hip and knee at the power position (end of transition) | Knee at end of transition 134.7 ± 7.9° (men) vs 127.3 ± 6.4° (women), significant. Coaching: knee 125–135°; ankle/knee/hip 60–70 / 120–130 / 140–150° | [V] Harbili, Table 3, p. 164; [C] `10b` rows 9, 23 | **more work** | Missing: a seen hip and knee at the transition. `A:hip_smooth`, `A:knee_smooth` at `E:transition` exist | kp r_shoulder, r_hip, r_knee, r_ankle · S · fps ≥ 120 [I] | Hip and knee behind the plate (#13) |
| A9 | Trunk upright at the transition | Torso near vertical as the second pull starts. Heavier loads may need "additional time required for the lifter to align their trunk vertically" | [C] `10b` row 17; [V] Ahn & Kipp, p. 18 | **more work** | Missing: a seen hip at the transition. `A:trunk_smooth` at `E:transition` exists | kp r_shoulder, r_hip · S, level | Hip behind the plate (#13) |
| A10 | Knee extension at end of second pull | Maximal knee extension in the second pull: 169.7 ± 3.5° (men) vs 165.3 ± 5.1° (women), significant. Knee (and hip) at position P (end of second pull) is **higher in made than missed lifts at the same load**, ≈ +4.6° digitised ([S]). It is the only significant success/fail angle | [V] Harbili, Table 3, p. 164; [V] Mastalerz, p. 72, Fig. 4 caption, p. 74; [S] `10a` B1 | **more work** | Missing: (1) a "peak extension" event (max `A:knee_smooth` between `E:transition` and `E:catch`); (2) a behind-plate check at that frame | kp r_hip, r_knee, r_ankle · S · fps ≥ 120 [I] | Not covered by #13. With the bar at ~0.9 m, the plate (r 0.225 m) sits over the hip, the angle's top point [I] |
| A11 | Hip extension at end of second pull | Hip at full extension, slightly past straight: 191.8 ± 5.9° (men), 193.0 ± 9.7° (women); P-position hip higher in made lifts | [V] Harbili, Table 3, p. 164; [V] Mastalerz, p. 72 | **more work** | Missing: (1) a **signed hip angle**. `snatch/angles.py` returns the unsigned interior angle (0–180°), so 192° would read 168° [I, from code]; (2) peak-extension event; (3) behind-plate check | kp r_shoulder, r_hip, r_knee · S · fps ≥ 120 [I] | As A10 |
| A12 | Ankle plantarflexion (triple extension) | Ankle extension: first pull 128.5 ± 6.6° (men) vs 119.6 ± 4.3° (women), significant; second pull 144.3 ± 4.3 vs 142.6 ± 8.4°. Angle uses the 5th metatarsal, malleolus and knee (p. 163) | [V] Harbili, Table 3, p. 164 | **more work** | Missing: foot keypoints. COCO-17 has no toe or heel; a body-plus-feet model is needed (rtmlib appears to ship one [I], not checked) | kp r_knee, r_ankle, toe/heel · S | Ankle hidden at setup (#13). Monocular side-view ankle R² 0.21 vs Vicon (Zhang 2027, Table 2, p. 7) |
| A13 | Arms straight during the pull | Elbows stay extended until the second pull ends (no early arm bend). No degree threshold in any source | [C] `05` fault table; [S] `10a` B7 | **more work** | Missing: elbow-to-hub angle (`A:r_shoulder_*`, `A:r_elbow_*` + `P:hub_x/hub_y`), planned as a second elbow row in #15. `A:elbow_smooth` uses the hidden wrist | kp r_shoulder, r_elbow · hub · S | Wrist hidden in every side-on frame (#13, #14). Elbow reads 164–166° at lockout with straight arms (#12). Monocular side-view elbow RMSE 27.4°, R² 0.07 (Zhang 2027, Table 2) |
| A14 | Catch depth | Knee angle and hip height in the receiving position. Power = knee ≥ 90° / thighs above parallel; squat = hips below knees | [C] `10b` rows 12, 13, 17 | **now** | `A:knee_smooth` at `E:catch`; `A:r_hip_y` vs `A:r_knee_y` at `E:catch` | kp r_hip, r_knee, r_ankle · S · fps: #15 decides | Only the wrist hidden at the catch (#13). #13: all receptions high |
| A15 | Trunk and hip at the catch | Torso upright under the bar (squat bottom: trunk 24° (21–27) from vertical) | [C] Fehér via `10b` row 10 | **now** | `A:trunk_smooth`, `A:hip_smooth` at `E:catch` | kp r_shoulder, r_hip, r_knee · S, level | Visible (#13) |
| A16 | Arms locked at catch and lockout | Elbows locked when the bar is received and held (re-bending = press-out) | [C] (IWF rule text not read, `10b` row 27) | **more work** | Missing: elbow-to-hub angle (#15) | kp r_shoulder, r_elbow · hub · S | Wrist inside the plate outline at the catch, at the rim at lockout (#13) |
| A17 | Lockout: legs straight, body upright | Standing with knees and hips extended under the bar (phase 6, "rising from the squat position"; not analysed there) | [V] Harbili, p. 163; [C] | **now** | `A:knee_smooth`, `A:hip_smooth`, `A:trunk_smooth` at `E:lockout` | kp r_shoulder, r_hip, r_knee, r_ankle · S, level | Visible except the wrist (#13). v2 defines lockout by the knee (within 5° of its maximum), so the knee value is partly fixed by definition |
| A18 | Trunk–knee coordination | Vector-coding coupling angle between trunk and knee. The pull is knee-dominated, and patterns are individual and load-dependent | [V] Ahn & Kipp, p. 16–19, Fig. 2, p. 18 | **more work** | Missing: a seen knee through the pull. `A:trunk_smooth`, `A:knee_smooth` series exist; phases from `vy` | kp r_shoulder, r_hip, r_knee, r_ankle · hub · S · fps ≥ 120 [I] | Knee hidden or guessed at setup and transition (#12, #13) |
| A19 | Joint angular velocity, second pull | Peak extension velocity, second pull: hip 330.3 ± 39.8 (men) vs 444.9 ± 74.8°/s (women), significant; knee 342.1 vs 348.8°/s. Transition knee flexion 150.3 vs 95.5°/s. Markerless systems underestimate hip/knee extension velocity by ~40% (Thiele 2024) | [V] Harbili, Table 4, p. 165; [S] #11, `10a` | **more work** | Missing: a seen hip and knee at the transition, plus differentiation of noisy keypoints. Derivatives of `A:hip_smooth`, `A:knee_smooth` | kp r_shoulder, r_hip, r_knee, r_ankle · S · fps ≥ 120 (470°/s = 3.9° per frame at 120, [S] `05`) | Hip and knee behind the plate at the transition (#13) |
| **B** | **Bar path, displacement, distance** | | | | | | |
| B1 | Bar trajectory type | Pattern of horizontal travel against a vertical line through the bar's start:<br>• Type 1: toward–away–toward, crossing the line<br>• Type 2: the same, not crossing<br>• Type 3: away–toward–away–toward<br>• Type 4: an extra away–toward<br>Type 3 is most common: 53% at the 2015 Worlds, 59% at the 2017 Pan-Ams | [V] Shah et al. (2025 data), §1.1, p. 3; Fig. 2, p. 4; §2.5, p. 7; Algorithm 1, p. 9 (after Cunanan 2020); [V] Harbili, p. 162, 167 | **now** | `P:hub_x`, `P:hub_y` from `E:setup` to bar catch; reference line x = `P:hub_x` at `E:setup` | hub · S, level: 1° of tilt ≈ 1.7 cm per metre of rise [I] · fps: 240 checked, lower untested | Hub as in shorthand (#14). Shah's own rule-based classifier got 7 of 10 right (p. 11) |
| B2 | Toward the lifter in the first pull (X1, θ1) | Largest move toward the lifter before the bar reverses: 3.56 ± 1.40 cm (men), 4.26 ± 1.25 cm (women). Shah typical range 3–10 cm; θ1 = atan(X1 / height), 5–15° | [V] Harbili, Table 5, p. 165; [V] Shah, p. 10, Table 2, p. 12 | **now** | max(`P:hub_x`[setup] − `P:hub_x`) up to the first reversal ÷ `P:px_per_m`. Built in #30 with the window ending at `E:transition`, the end of the first pull (`snatch/markers.py`) | hub · scale (450 mm plate assumed, #14) · S, level | Hub as in shorthand; on the floor this is where off-axis fails (#14) |
| B3 | Away from the lifter in the second pull (X2) | Forward travel from the X1 point to the most forward point before peak height: 2.27 ± 2.94 cm (men), 1.55 ± 4.74 cm (women). Shah 3–14 cm | [V] Harbili, Table 5, p. 165; [V] Shah, p. 10, Table 2 | **now** | `P:hub_x` between the X1 point and min `P:hub_y` ÷ `P:px_per_m` | hub · scale · S, level | Hub as in shorthand |
| B4 | Loop: back toward the lifter after peak height (Xloop) | "Horizontal displacement toward weightlifter after beginning of descent from maximum height": 3.52 ± 1.89 cm (men), 5.41 ± 4.20 cm (women). Shah 3–12 cm | [V] Harbili, Table 5, p. 165; [V] Shah, p. 10, Table 2 | **now** | `P:hub_x` from min `P:hub_y` to bar catch ÷ `P:px_per_m` | hub · scale · S, level | Hub visible overhead in all plate clips, incl. off-axis (#14) |
| B5 | Net horizontal displacement (Xnet) | Start line to the bar catch; "should be minimum". Shah typical 0–17 cm | [V] Shah, p. 10, Table 2, p. 12. Note: Table 2 shows a 23.6 cm mean against this range while the text says all values are within range | **now** | `P:hub_x`[bar catch] − `P:hub_x`[setup] ÷ `P:px_per_m` | hub · scale · S, level | Hub as in shorthand |
| B6 | Peak bar height | Harbili: 1.16 ± 0.05 m (men), 1.17 m (women). Mastalerz: 88.2 vs 87.3 cm, made = missed (n.s.). Shah: 120–145 cm or 70–85% of body height. Lower is more efficient: "minimizing … the maximum height of the barbell" | [V] Harbili, Table 5, p. 165; [V] Mastalerz, Table 2, p. 75, and p. 76; [V] Shah, Table 2, p. 12 | **now** (metres) | 0.225 m + (`P:hub_y`[setup] − min `P:hub_y`) ÷ `P:px_per_m`. At rest the bar axis sits one plate radius above the floor [I] | hub · scale · plate diameter (450 mm assumed, not measured, #14) · % of height needs the lifter's height (not recorded) | Hub visible overhead in all plate clips (#14) |
| B7 | Bar height at end of first and second pull | 0.50 / 0.49 m and 0.89 / 0.89 m (men / women) | [V] Harbili, Table 5, p. 165 | **more work** | Missing: the events "end of first pull" (A6) and "peak extension" (A10). Both are knee-angle extrema with the knee behind the plate. `P:hub_y`, `P:px_per_m` exist | hub · scale · kp knee · S | As A6, A10 |
| B8 | Drop under the bar | Peak height minus bar-catch height: 0.14 ± 0.03 m (men), 0.15 ± 0.02 m (women). Mastalerz: 10.0 vs 8.9 cm (n.s.). Shah: 6.5–25 cm, "the less the Ydrop, the better" | [V] Harbili, Table 5, p. 165; [V] Mastalerz, Table 2, p. 75; [V] Shah, p. 8, 10, Table 2 | **now** | (`P:hub_y`[bar catch] − min `P:hub_y`) ÷ `P:px_per_m` | hub · scale · S | Hub as in shorthand. Use the bar catch, not `E:catch` (#13) |
| B9 | Bar–body distance (bar close; contact at the hip) | Bar stays close to the shins and thighs and meets the hips; "a small horizontal movement is necessary for good lifting technique" (that is about displacement, not distance) | [C]; [V] Harbili, p. 167 | **not feasible** (side-on, with plates) | The region where bar and body meet is inside the plate outline at setup and transition. The hub also sits roughly half a metre nearer the camera than the body, so image distances mix depths (N3) [I]. A front-oblique view (#16 note) might see the bar against the legs; untested | — | Shin, knee and hip hidden at setup and transition (#13) |
| B10 | Bar over the base at catch and lockout | Bar over the mid-foot when received and held. Made lifts had the bar "in a less backward overhead position" (Stone 1998) | [C]; [V] Mastalerz, p. 70 (reporting Stone 1998) | **now** (px, one camera set-up) | `P:hub_x` − `A:r_ankle_x` at bar catch and `E:lockout`. Ankle stands in for mid-foot (COCO-17 has none) | hub · kp r_ankle · S, level · metres biased (N3) | Ankle visible at catch and lockout (#13) |
| **C** | **Bar and body speed** | | | | | | |
| C1 | Peak vertical bar velocity | Second pull: 1.69 ± 0.07 m/s (men) vs 1.80 ± 0.12 m/s (women), significant, attributed to the lighter load (p. 167). **No made/missed difference**: max 1.15 vs 1.16 m/s, mean 0.68 vs 0.68 m/s | [V] Harbili, Table 5, p. 165, and p. 167; [V] Mastalerz, Table 2, p. 75 | **now** | max `vy` from `P:hub_y`, `P:px_per_m`, `P:fps` | hub · scale · fps ≥ 120 (1.5 cm of travel per frame) [S] `05` | Hub as in shorthand |
| C2 | Velocity curve shape (one peak vs a dip at the transition) | "A steady increase in velocity to a single maximum value … is characteristic of better weightlifters" (two-peak curves are the other type). Model optimum: velocity "increases continuously" | [V] Harbili, p. 167 (citing Baumann 1988); [V] Korayem, p. 4 | **now** | Local minima of `vy` (from `P:hub_y`) between `E:setup` and peak `vy` | hub · scale · fps ≥ 120 [I]; smoothing changes how deep a dip looks | Hub as in shorthand |
| C3 | Body drop speed in the turnover | "Dropping the body rapidly under the bar during the turnover phase is associated with skilled-snatch performance" | [V] Ahn & Kipp, p. 19 (citing Ikeda 2012) | **now** (px/s) | Downward speed of `A:r_hip_y` between peak `vy` and `E:catch` | kp r_hip · fps ≥ 120 [I] · metres biased (N3) | Hip clear of the plate once the bar is above it [I]; not checked by #13 |
| C4 | Centre-of-gravity speed in the catch | Mean body-CG velocity higher in made lifts in all phases. Biggest gap in the catch phase: 5 cm/s, significant | [V] Mastalerz, p. 71, Fig. 3 caption, p. 73 | **more work** | Missing: a segment-mass model on COCO-17 (none in the pipeline). Far-side limbs, hands and feet are hidden, so its accuracy is unknown [I] | all kp, both sides · scale at the body plane (N3) | Far side not tracked; near wrist hidden (#13) |
| **D** | **Timing** | | | | | | |
| D1 | Liftoff to end of transition | Harbili first pull 0.546 ± 0.064 / 0.511 ± 0.042 s plus transition 0.115 / 0.108 s (men / women). Mastalerz first pull 0.42 s | [V] Harbili, Table 2, p. 164; [V] Mastalerz, p. 71 | **now** | `E:transition` − `E:setup` ÷ `P:fps` | fps (resolution 4 ms at 240, 33 ms at 30) | v2 transition is found from a guessed knee (#12); marks accepted (#13). See N8 |
| D2 | Transition duration | 0.115 ± 0.019 s (men), 0.108 ± 0.031 s (women); "should be executed quickly". Mastalerz: "rapidly executed" | [V] Harbili, Table 2, p. 164, and p. 166; [V] Mastalerz, p. 76 | **more work** | Missing: an end-of-first-pull event (knee max; A6) | kp knee · fps ≥ 120: 0.11 s is 3–4 frames at 30 fps [I] | Knee behind the plate (#13) |
| D3 | Second pull duration | Harbili 0.133 / 0.153 s (to max extension); Mastalerz 0.31 s; Ahn & Kipp: the pull ends at peak bar velocity | [V] Harbili, Table 2; [V] Mastalerz, p. 71; [V] Ahn & Kipp, p. 17 | **now** (to peak bar velocity) | `E:transition` → frame of peak `vy` (`P:hub_y`). Harbili's end point (max extension) needs A10's event | hub · fps ≥ 120 [I] | As D1 |
| D4 | Turnover: how fast the lifter gets under the bar | Harbili 0.235 ± 0.016 / 0.235 ± 0.019 s; Mastalerz 0.28 s; Ahn & Kipp: peak to lowest bar velocity, 27.6 ± 1.5% of the lift | [V] Harbili, Table 2, p. 164; [V] Mastalerz, p. 71; [V] Ahn & Kipp, p. 17 | **now** | Peak `vy` → min `vy`, or → bar catch, from `P:hub_y` | hub · fps ≥ 120 [I] | Hub visible overhead (#14) |
| D5 | Catch phase duration | Harbili 0.324 / 0.355 s; Mastalerz 0.24 s (made) vs 0.26 s (missed); Ahn & Kipp: min bar velocity → zero, 17.5 ± 3.3% | [V] Harbili, Table 2; [V] Mastalerz, p. 71; [V] Ahn & Kipp, p. 17 | **now** | min `vy` → first `vy` ≈ 0 after it, from `P:hub_y` | hub · fps | Hub visible (#14) |
| D6 | Phase shares of the lift | Pull 54.9 ± 1.9%, turnover 27.6 ± 1.5%, catch 17.5 ± 3.3%; the pull lengthens as load rises. The pull starts at a bar velocity ≥ 0.03 m/s | [V] Ahn & Kipp, p. 17–18 | **now** | `vy` thresholds on `P:hub_y` (they used hand markers for bar velocity) | hub · scale · fps | The hub's speed SD at rest is 15 px/s ≈ 0.02 m/s (#14), close to the 0.03 m/s start threshold [I] |
| D7 | Recovery: catch to lockout | Time to stand up with the bar. Phase 6 in Harbili, not analysed; no values in `docs/papers` | [V] Harbili, p. 163 | **now** | `E:lockout` − `E:catch` ÷ `P:fps` | fps | Knee-defined lockout (A17) |
| **E** | **Catch and stability** | | | | | | |
| E1 | Bar brought to rest after the catch | Bar's downward motion stopped quickly, with little extra dip. The catch phase ends at zero bar velocity, as lifters "decelerate and stop the barbell's downward motion" | [V] Ahn & Kipp, p. 17, 19; [C] | **now** | Extra fall of `P:hub_y` and time to `vy` ≈ 0 after the bar catch | hub · scale · fps | Hub visible overhead (#14) |
| E2 | Bar travel overhead during recovery | Bar stays over the base while the lifter stands; no chasing forward or back | [C]; [V] Mastalerz, p. 70 (Stone 1998) | **now** | Range of `P:hub_x` from bar catch to `E:lockout` ÷ `P:px_per_m` | hub · scale · S, level | Hub visible (#14) |
| E3 | Overhead stability at lockout | Bar motionless overhead. Bar sway only; joint-level wobble (elbow) is not measurable, wrist hidden (`05`) | [C] (IWF rule not read) | **now** (bar only) | SD of `P:hub_x`, `P:hub_y` from `E:lockout` to `E:overhead_end` | hub · scale | Hub visible (#14). Reference: the hub sways 3.5 cm while standing with the bar at the hips in 20261001_2_jiri_v1_standup_5kg_1rep_success_0deg (#14) |
| E4 | Foot travel: jump forward or back | Feet land about where they started (fore–aft); big jumps point to a bar-path or balance problem | [C] `05` fault table | **more work** | Missing: a seen foot before liftoff. #15's foot-anchor check finds such a frame or reports "not possible"; toe/heel keypoints would track the foot itself. `A:r_ankle_x` exists | kp r_ankle (better toe/heel) · S | Ankle hidden at setup (#13) |
| E5 | Frontal-plane markers | Stance and catch width, knee valgus in the catch, bar level left–right, grip symmetry | [C]; [S] `05` (single-view frontal knee r = 0.20) | **not feasible** (side-on) | Frontal plane. The far plate and far limbs are behind the lifter | — | Far side never visible side-on |

## Notes

- **N1. Angle conventions differ from the papers.**
  - Harbili and Mastalerz digitise 3D from two cameras at 45° to the sagittal plane (50 Hz, 4 Hz filter: Harbili p. 163, Mastalerz p. 70). Their hip can exceed 180°.
  - Our angles are 2D, near side, interior (0–180°), with the trunk from vertical. Soviet texts give the trunk "to the platform" (`10b`).
  - Literature values are for orientation only. Within-lifter differences are the use #11 is built for.
- **N2. Where "the bar" is measured.**
  - Harbili and Mastalerz digitise the hand (medial side) as the bar point (Harbili p. 163, Mastalerz p. 70).
  - Shah tracks the barbell and scales by the plate's diameter (§2.4, p. 7).
  - We track the near plate's hub, which is the bar axis. That is closer to the bar than the hand, and the hand is hidden anyway (#11, #14).
- **N3. Scale holds only in the plate plane [I].**
  - `px_per_m` comes from the plate's outline, so it holds for points at the plate's depth. All bar-only markers (B1–B8, C1–C2, D, E1–E3) are fine.
  - Body keypoints sit roughly half a metre farther from the camera. Converting body distances with `px_per_m` makes them too small, by the ratio of camera-to-body to camera-to-plate distance. Camera distance is not recorded.
  - Hub-to-body offsets (A4, B10) also carry parallax that depends on where in the frame the lift happens.
  - With a fixed tripod and the same spot on the platform, both biases stay constant, so comparing reps in pixels is fine. Comparing to literature in metres is not.
- **N4. The phone is assumed level (#12) but not checked.**
  - A 1° tilt moves the hub's x by ~1.7 cm per metre of rise [I]. That is the same size as X1/X2 (2–4 cm, Harbili Table 5).
  - Within one tripod set-up it is a constant bias. Across sessions it isn't. The trunk angle has the same issue.
- **N5. Frame rate.**
  - The hub has only been checked at 240 fps (#14). #15 tests joint angles on the 120/60/30 ladder; no ticket tests the bar markers on the ladder. A subsampling estimate (#30, `docs/results/30-fps-estimate.md`) keeps the bar displacements and C1 usable at 120 fps; D4 and the catch mark fail at every rate.
  - Shah used a GoPro at 3.35 m in 4K and notes that a camera ≥ 20° above the lateral line breaks the method (p. 5, p. 13).
- **N6. Monocular accuracy and repeatability from `docs/papers` (not the snatch).**
  - Zhang 2027 (MediaPipe, one iPhone side-on at ~90°, 60 Hz, symmetric 10 kg box lift; Table 2, p. 7). RMSE vs Vicon (R²):
    - trunk 9.9° (0.85)
    - knee 18.5° (0.88)
    - hip 28.6° (0.87)
    - shoulder 16.8° (0.83)
    - elbow 27.4° (0.07)
    - ankle 18.3° (0.21)
  - High R² with high RMSE means the shape is tracked with an offset, which cancels in within-lifter comparison. The elbow and ankle shapes are not tracked at all.
  - Kanko 2020 (Theia3D, 8 cameras, 60 Hz, gait; p. 8–9): trial-to-trial variability averaged 2.2°, "likely caused by the markerless motion capture algorithm which uses a frame-by-frame approach".
  - Neither paper is a snatch or a single camera with plates in front of the legs.
- **N7. What separates made from missed lifts.**
  - Mastalerz (14 elite women, same load) found significant differences only in knee and hip angle at P (end of second pull: p. 72, p. 77) and in CG speed (p. 71).
  - Bar velocities, peak height, drop and phase durations did not differ (Table 2, p. 71, 75).
  - In this table those are A10, A11 and C4, all "more work". Harbili and Mastalerz also disagree on whether the re-bend should be small or deep (A7).
  - Ahn & Kipp found coordination patterns individual to each lifter (p. 19), which supports comparing a lifter with themselves rather than with a norm.
- **N8. Correction to `docs/results/13-phase-check.md` (not edited).**
  - #13 compares liftoff→transition (0.53–0.61 s) with "0.42 s for elite lifters in Baumann 1988 / Harbili 2012".
  - The 0.42 s figure is Mastalerz's first pull (p. 71). Harbili's first pull is 0.546 / 0.511 s (Table 2), and liftoff→transition spans Harbili's first pull **plus** transition (0.661 / 0.619 s).
  - By that measure these lifts are shorter off the floor than Harbili's, not slower. No phase mark is affected.

## What this doc leaves untouched

- **Nothing was built or run.** The fields named in the table already exist.
- **No #11 threshold, #15 rule, phase rule or clip role was touched.**
  - The X = 10° band, the 3/5° bands, phase definitions v1 and v2, and the clip roles in `docs/clip-log.md` are all unchanged.
  - The new events the table proposes (end of first pull, peak extension, peak bar velocity, bar catch) would sit on top of the v2 marks and would not move any of them.
- **No across-rep spread was computed**, so nothing from #15 is seen early.

## Gaps

- **Thiele 2024**, the only markerless snatch validation, is not in `docs/papers`. Its numbers here come via `10a` and #11.
- Gourgoulis 2009, Liu 2022 and Cunanan 2020 (the trajectory-type survey Shah relies on) are also not in `docs/papers`.
- **Coaching markers A4, B9, B10 and E2–E4 have no measured norm** in any source read. They are common cues only.
- **Visibility at the moments between the four v2 events** (end of first pull, peak extension, turnover) was never checked. A10, A11, A19 and C3 depend on it.
- **Shah's validation is weak**: 10 videos, 7 of 10 types correct, and a Table 2 inconsistency (B5). It shows the trajectory types and variables are defined, not that they are measured well.
- **Plate diameter** (450 mm) and **phone level** are unmeasured assumptions. Every metre value and every horizontal marker depends on them.
