# D1 views — numbers (scripts/d1_views.py)

Clips: `20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right`, `20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right`, `20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right`

## Plate

| clip | status | found % | near plate in lifts % (other) | jumps | view° rest (all p10–p90) | major tilt° | px/m | px/m CV % | hub jitter rest x/y (mm) | hub jitter in lifts x/y (mm) |
|---|---|---|---|---|---|---|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right (plate.npz) | ok | 100.0 | 100.0 (0.0) | 0 | 0.0 (0–0) | -90.0 | 429 | 1.4 | 0.1/0.2 | 0.5/0.7 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right (plate_near.npz) | near-plate prior; found 90.2% of lift fr | 46.9 | 84.0 (6.4) | 4 | 30.2 (26–38) | -18.2 | 348 | 4.7 | 7.3/8.5 | 6.7/11.7 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right (plate_near.npz) | near-plate prior; found 85.6% of lift fr | 43.2 | 84.0 (0.0) | 4 | 38.7 (23–42) | -45.7 | 400 | 8.2 | 15.8/15.9 | 22.1/20.8 |

## Near keypoints (mean over reps)

behind = % of window frames inside the plate outline; score near (far); jitter mm; swap %

### transition

| clip | shoulder | elbow | wrist | hip | knee | ankle |
|---|---|---|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | beh 0, s 0.82 (0.75), j 2.6, sw 0 | beh 0, s 0.81 (0.75), j 2.8, sw 0 | beh 100, s 0.71 (0.65), j 3.5, sw 0 | beh 25, s 0.73 (0.69), j 3.6, sw 0 | beh 81, s 0.76 (0.71), j 4.4, sw 0 | beh 0, s 0.84 (0.78), j 2.2, sw 0 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | beh 0, s 0.80 (0.83), j 3.2, sw 0 | beh 0, s 0.85 (0.90), j 3.3, sw 0 | beh 99, s 0.75 (0.88), j 5.4, sw 0 | beh 48, s 0.71 (0.73), j 6.3, sw 0 | beh 53, s 0.79 (0.85), j 4.5, sw 0 | beh 5, s 0.86 (0.87), j 3.6, sw 0 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | beh 4, s 0.82 (0.86), j 2.5, sw 0 | beh 19, s 0.90 (0.93), j 1.7, sw 0 | beh 37, s 0.88 (0.93), j 3.4, sw 0 | beh 21, s 0.75 (0.75), j 8.7, sw 0 | beh 23, s 0.85 (0.88), j 2.1, sw 0 | beh 1, s 0.88 (0.87), j 3.5, sw 0 |

### pull

| clip | shoulder | elbow | wrist | hip | knee | ankle |
|---|---|---|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | beh 0, s 0.79 (0.72), j 3.3, sw 0 | beh 0, s 0.78 (0.71), j 3.2, sw 0 | beh 100, s 0.69 (0.60), j 6.3, sw 0 | beh 26, s 0.71 (0.65), j 3.9, sw 0 | beh 57, s 0.72 (0.66), j 5.0, sw 0 | beh 22, s 0.78 (0.70), j 2.9, sw 0 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | beh 0, s 0.79 (0.82), j 2.9, sw 0 | beh 1, s 0.83 (0.90), j 3.1, sw 0 | beh 100, s 0.72 (0.88), j 7.5, sw 0 | beh 22, s 0.73 (0.71), j 9.2, sw 0 | beh 21, s 0.80 (0.85), j 3.7, sw 0 | beh 48, s 0.81 (0.86), j 5.2, sw 0 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | beh 2, s 0.82 (0.85), j 2.5, sw 0 | beh 10, s 0.89 (0.93), j 1.7, sw 0 | beh 24, s 0.87 (0.93), j 3.1, sw 0 | beh 11, s 0.76 (0.75), j 9.2, sw 0 | beh 12, s 0.85 (0.88), j 2.1, sw 0 | beh 3, s 0.88 (0.87), j 3.8, sw 0 |

### near segment length in the pull (median cm, CV %, jitter mm)

| clip | thigh | shank | upper_arm | forearm |
|---|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | 33.7, 4.9, 4.5 | 37.3, 2.5, 3.6 | 22.6, 20.0, 3.4 | 23.1, 9.3, 4.3 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | 29.0, 12.4, 8.0 | 35.8, 5.5, 4.4 | 25.6, 19.2, 2.6 | 24.6, 15.7, 5.3 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | 20.5, 20.2, 6.7 | 28.2, 4.2, 2.9 | 19.9, 11.0, 1.8 | 19.0, 9.8, 2.8 |

## Rectified bar markers (mean ± SD over reps; unrectified mean)

| clip | def | reps | peak height cm | X1 | X2 | Xloop | Xnet | drop | peak v m/s | rest spread x/y cm |
|---|---|---|---|---|---|---|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | v1/v1/v1 | 3 | 135.8 ± 2.1 | 2.4 ± nan [2.4] | 3.9 ± nan [3.9] | 11.9 ± 2.2 [11.9] | -23.3 ± 2.5 [-23.3] | 12.0 ± 3.6 | 2.71 ± 0.18 | 2.9/2.2 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | v1/v1/v1 | 3 | 147.7 ± 3.4 | 0.4 ± 0.2 [0.3] | 14.6 ± 4.9 [12.6] | 42.4 ± 24.3 [36.6] | -43.5 ± 19.9 [-37.6] | 64.1 ± 45.3 | 5.62 ± 4.17 | 7.2/0.4 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | v1/v1/v1 | 3 | 117.4 ± 38.8 | 0.3 ± nan [0.3] | 45.0 ± nan [35.2] | 22.8 ± 27.8 [17.8] | -11.1 ± 20.9 [-8.7] | 77.9 ± 38.6 | 10.39 ± 2.87 | 2.2/0.7 |

## First pull: hub x (cm from setup, rectified; [unrectified]) when the hub first reaches 25 / 50 / 75 cm above setup; mean ± SD over reps, hub found % up to there

| clip | 25 cm | 50 cm | 75 cm |
|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | -0.5 ± 0.3 [-0.5], 100% | -1.9 ± 1.6 [-1.9], 100% | -1.0 ± 1.9 [-1.0], 100% |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | +4.1 ± 1.1 [+3.5], 100% | +3.5 ± 1.4 [+3.0], 100% | +3.3 ± 1.8 [+2.8], 100% |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | +10.3 ± 11.8 [+8.0], 93% | +4.2 ± 8.3 [+3.3], 87% | +39.7 ± 5.8 [+31.0], 85% |

## Phase frames

| clip | rep | setup | hub at knee | transition | peak ext | catch | lockout |
|---|---|---|---|---|---|---|---|
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | 1 | 991 | 1070 | 1098 | 1147 | 1368 | 1672 |
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | 2 | 2935 | 3032 | None | 3085 | 3241 | 3558 |
| 20261007_4_jiri_v3_squatsnatch_5kg_3rep_success_0deg_right | 3 | 4743 | 4812 | None | 4865 | 5029 | 5360 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | 1 | 1006 | 1115 | 1130 | 1181 | 1337 | 1646 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | 2 | 2643 | 2746 | 2758 | 2802 | 2959 | 3117 |
| 20261007_6_jiri_v3_squatsnatch_5kg_3rep_success_30deg_right | 3 | 4341 | 4435 | None | 4487 | 4699 | 4970 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | 1 | 1212 | 1309 | 1347 | 1382 | 1543 | 1856 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | 2 | 2986 | 3014 | None | 3158 | 3293 | 3483 |
| 20261007_5_jiri_v3_squatsnatch_5kg_3rep_success_45deg_right | 3 | 4643 | 4736 | None | 4790 | 4923 | 5161 |
