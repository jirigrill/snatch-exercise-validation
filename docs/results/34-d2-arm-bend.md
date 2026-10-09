# 34 — D2: early arm bend from the side-on view

Ticket: [#22](https://github.com/jirigrill/snatch-exercise-validation/issues/22). Rule (`../recording-protocol.md` § Spike session): **D2 go** if the 2D shoulder-to-hub distance separates bent-arm and straight-arm reps beyond rep-to-rep spread. Run 2026-10-09 on the spike session (2026-10-07, `vids/spike/`), side-on 0°, camera on the right.

**Verdict: provisional go.** Early arm bend stays on the cause list, but the evidence is thin.
- **Best signal:** the shoulder-to-hub distance with the bar at the knee, divided by the same distance at liftoff (`rel@knee`). Bent reps 0.828–0.846; all 9 straight reps 0.857–0.886 (SD 0.010). The ranges don't overlap (gap 0.011, about 0.6 cm), and Cohen's d is −2.9.
- **Specificity:** the other deliberate faults stay inside the straight range on `rel@knee`: bar far from the body 0.856–0.865, behind the bar 0.869–0.888. The raw cm distance (`d_cm@knee`) also separates the bent reps, but it flags behind-the-bar reps too, so the ratio is the one to use.
- **Weak points:**
  - Only **2 bent reps**, against 9 straight ones.
  - The margin is about the size of the rep-to-rep SD.
  - The bend was deliberate and exaggerated.
  - **In `_10_` the bar never went overhead** (see below), so these were pulls to face height, not snatches.
- **What would make it a firm go:** ≥5 alternated bent and straight reps at one load, all taken overhead, as the protocol asked.

## Data

| Group | Clip | Load | Reps used |
|---|---|---|---|
| straight30 | `20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right` | 30 kg | 3 |
| bent30 | `20261007_10_jiri_v3_powersnatch_10kg_3rep_fail-bend-elbows_0deg_right` | 30 kg | **2 of 3** |
| straight25 | `20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right` | 25 kg | 3 |
| straight27 | `20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right` | 27.5 kg | 3 |
| farbody25 | `20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right` | 25 kg | 3 |
| behindbar25 | `20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right` | 25 kg | 3 |

**`_10_` has no overhead phase.** Each rep's hub peaks at nose height: its highest point is 10 px above the nose, against ~190 px in `_9_`. A 5 fps sheet shows the bar reach the face and come straight back down. The lifter confirmed it (2026-10-09): the bar stopped at face height and was never locked out. The log row is now `miss_deliberate` / `no_turnover`. So v1 and v2 rep finding (overhead run ≥ 0.25 s above the nose) found 0 reps, and the body-height analysis found no lockout frames. `arm_bend.py` now falls back to the hub passing the **shoulders** as the rep anchor when no overhead run exists (column `anchor`). That still brackets the pull (liftoff → bar at hip), which is all D2 uses. With this anchor, 2 of the 3 reps are found. The middle rep (~f2900) doesn't stay above the shoulders for 0.25 s.

## Method

`snatch/armbend.py`, `scripts/studies/arm_bend.py`:
- **Near side:** the right shoulder, elbow and wrist, smoothed.
- **Hub:** from `plate.npz`. Side-on, the near wrist sits inside the plate outline in every pull frame (`36-skeleton-fill.md`), so the hub stands in for the hand.
- **Events per v2 rep:**
  - liftoff (setup);
  - first frame with the hub above the near knee (`knee`);
  - first frame with the hub above the near hip (`hip`);
  - v2 transition, when it is detected.
- **Signals:**
  - `d_cm`: shoulder-to-hub distance, scaled in the plate plane. The shoulder is ~0.7 m deeper, so this is not a true arm length. It is still consistent within one camera set-up.
  - `rel`: `d_cm` divided by `d_cm` at liftoff. It is scale-free, and it removes set-up and camera differences, e.g. the moved tripod for `_11_`/`_12_`.
  - `elbow_hub_deg`: the shoulder–elbow–hub angle.
  - `elbow_deg`: the shoulder–elbow–wrist angle. The wrist is RTMPose's guess behind the plate.

## Results (per rep)

| Group | rep | rel@knee | d_cm@knee | rel@hip | elbow–hub ° @hip | elbow–wrist ° @knee |
|---|---|---|---|---|---|---|
| straight30 | 1 / 2 / 3 | 0.871 / 0.886 / 0.867 | 53.1 / 54.8 / 53.7 | 0.733 / 0.719 / 0.702 | 166 / 176 / 175 | 174 / 174 / 180 |
| straight25 | 1 / 2 / 3 | 0.867 / 0.857 / 0.858 | 53.3 / 53.2 / 53.3 | 0.699 / 0.682 / 0.686 | 163 / 174 / 178 | 178 / 178 / 180 |
| straight27 | 1 / 2 / 3 | 0.860 / 0.862 / 0.882 | 53.0 / 53.2 / 54.4 | 0.711 / 0.714 / 0.716 | 164 / 168 / 166 | 177 / 177 / 177 |
| **bent30** | 1 / 2 | **0.846 / 0.828** | **51.3 / 50.1** | 0.702 / 0.670 | 163 / 157 | **169 / 167** |
| farbody25 | 1 / 2 / 3 | 0.865 / 0.856 / 0.858 | 53.1 / 52.6 / 53.4 | 0.712 / 0.714 / 0.703 | 164 / 172 / 168 | 175 / 170 / 169 |
| behindbar25 | 1 / 2 / 3 | 0.888 / 0.879 / 0.869 | 52.6 / 52.4 / 50.7 | 0.704 / 0.712 / 0.705 | 155 / 159 / 154 | 178 / 168 / 166 |

Separation against all 9 straight reps (gap > 0 means no overlap):

| Signal | bent30 d / gap | farbody25 gap | behindbar25 gap | Use |
|---|---|---|---|---|
| `rel@knee` | −2.9 / **+0.011** | −0.007 (overlap) | −0.017 (overlap) | **yes: separates and is specific** |
| `d_cm@knee` | −4.4 / +1.7 cm | −0.4 cm | **+0.4 cm** (false flag) | no |
| `elbow_deg@knee` | −4.6 / +4.9° | −1.0° | −3.4° | second signal; uses the guessed wrist |
| `rel@hip`, `elbow_hub_deg@hip` | overlap | overlap | behind the bar flags at the hip | no: by the hip the straight reps also bend (the second pull starts) |

- **The bend shows in the first pull, by the time the bar reaches the knee.** By the hip, every rep's elbow angle has opened up and the groups overlap.
- **Visual check:** `out/<clip>/arm_bend_sheet.jpg` for `_9_` and `_10_`. At the knee, the bend is hard to see by eye in a 2D side view: the elbow moves partly toward the camera. That is consistent with the small 2–3 cm difference.

## Caveats

- n = 2 bent against 9 straight reps, one lifter, one session; whole sets, not alternated reps. Load differs between the straight sets (25–30 kg). `rel` was flat across them (0.857–0.886).
- The bent reps were not completed snatches (no overhead phase). In a real snatch, the speed and bar path after the knee differ, but the window that separates the groups (liftoff → knee) is the same in both.
- The threshold that separates bent from straight (~0.85) comes from these 11 reps. It is not validated.

## Reproduce

```
cd prototype
uv run python scripts/studies/arm_bend.py straight30=out/20261007_9_jiri_v3_powersnatch_10kg_3rep_success_0deg_right \
  bent30=out/20261007_10_jiri_v3_powersnatch_10kg_3rep_fail-bend-elbows_0deg_right \
  straight25=out/20261007_3_jiri_v3_powersnatch_5kg_3rep_success_0deg_right \
  straight27=out/20261007_8_jiri_v3_powersnatch_7-5kg_3rep_success_0deg_right \
  farbody25=out/20261007_11_jiri_v3_powersnatch_5kg_3rep_fail-far-from-body_0deg_right \
  behindbar25=out/20261007_12_jiri_v3_powersnatch_5kg_3rep_fail-behind-bar_0deg_right
# writes out/d2_arm_bend/{reps.csv,summary.md,curves.png}, out/<clip>/arm_bend.{json} and arm_bend_sheet.jpg
```
