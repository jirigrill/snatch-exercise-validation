# Frame-rate estimate (#30): difference from 240 fps vs rep-to-rep spread

6 reps from 20261001_3_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_4_jiri_v1_powersnatch_5kg_1rep_success_0deg, 20261001_5_jiri_v1_powersnatch_5kg_2rep_success_0deg, 20261001_8_jiri_v2_powersnatch_5kg_2rep_success_0deg. Δ = lower rate − 240 fps, same rep. SD = rep-to-rep SD at 240 fps (phase marks: of the event's time after the rep's overhead start). Bias = mean Δ; median and max |Δ| over all reps and start offsets, detected reps only; offset 0 = the ladder file. ratio = max |Δ| / SD. A rep not detected at all makes the marker unusable (snatch.markers.verdict). Group verdict = most common marker verdict (plurality).

## 120 fps (2 offsets × 6 reps)

| marker | unit | SD 240 | bias | median \|Δ\| | max \|Δ\| | max \|Δ\| off 0 | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| setup | ms | 52 | 2 | 4 | 8 | 8 | 0.16 | usable |
| hip at setup | ° | 3.9 | -0.1 | 0.1 | 0.5 | 0.2 | 0.12 | usable |
| knee at setup | ° | 3.9 | 0.1 | 0.4 | 1.3 | 0.7 | 0.32 | usable |
| elbow at setup | ° | 1.9 | 0.0 | 0.1 | 0.2 | 0.1 | 0.10 | usable |
| trunk at setup | ° | 2.3 | 0.0 | 0.3 | 0.5 | 0.4 | 0.20 | usable |
| transition | ms | 26 | -2 | 4 | 8 | 8 | 0.32 | usable |
| hip at transition | ° | 2.5 | -0.7 | 0.9 | 3.3 | 3.3 | 1.35 | unusable |
| knee at transition | ° | 3.1 | 0.0 | 0.1 | 0.2 | 0.2 | 0.07 | usable |
| elbow at transition | ° | 4.2 | 0.4 | 0.4 | 2.6 | 2.6 | 0.62 | marginal |
| trunk at transition | ° | 1.4 | 0.5 | 0.9 | 2.3 | 2.3 | 1.72 | unusable |
| catch | ms | 69 | 9 | 23 | 104 | 104 | 1.50 | unusable |
| hip at catch | ° | 3.2 | 0.3 | 0.5 | 1.9 | 1.8 | 0.60 | marginal |
| knee at catch | ° | 5.2 | 0.1 | 0.1 | 0.9 | 0.8 | 0.17 | usable |
| elbow at catch | ° | 3.9 | 0.1 | 0.6 | 6.8 | 6.8 | 1.76 | unusable |
| trunk at catch | ° | 1.6 | -0.1 | 0.2 | 1.2 | 0.8 | 0.70 | marginal |
| lockout | ms | 152 | 1 | 4 | 17 | 12 | 0.11 | usable |
| hip at lockout | ° | 2.4 | -0.1 | 0.1 | 0.6 | 0.4 | 0.25 | usable |
| knee at lockout | ° | 0.6 | 0.1 | 0.2 | 0.4 | 0.4 | 0.79 | marginal |
| elbow at lockout | ° | 5.8 | 0.0 | 0.3 | 0.8 | 0.8 | 0.14 | usable |
| trunk at lockout | ° | 2.5 | -0.0 | 0.1 | 0.5 | 0.2 | 0.21 | usable |
| B2 X1 | cm | 1.0 | 0.0 | 0.0 | 0.1 | 0.0 | 0.06 | usable |
| B3 X2 | cm | 1.6 | 0.0 | 0.0 | 0.1 | 0.1 | 0.08 | usable |
| B4 Xloop | cm | 2.5 | 0.1 | 0.3 | 0.4 | 0.4 | 0.15 | usable |
| B5 Xnet | cm | 5.9 | -0.0 | 0.1 | 0.3 | 0.1 | 0.04 | usable |
| B8 drop | cm | 1.3 | -0.0 | 0.0 | 0.1 | 0.1 | 0.11 | usable |
| C1 peak bar velocity | m/s | 0.16 | -0.03 | 0.03 | 0.05 | 0.05 | 0.30 | usable |
| D4 turnover (to lowest bar velocity) | ms | 55 | 23 | 13 | 79 | 79 | 1.44 | unusable |
| D4 turnover (to bar catch), alt. | ms | 48 | 16 | 12 | 87 | 87 | 1.83 | unusable |

## 60 fps (4 offsets × 6 reps)

| marker | unit | SD 240 | bias | median \|Δ\| | max \|Δ\| | max \|Δ\| off 0 | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| setup | ms | 52 | 11 | 12 | 21 | 17 | 0.40 | usable |
| hip at setup | ° | 3.9 | -0.3 | 0.3 | 1.5 | 0.5 | 0.39 | usable |
| knee at setup | ° | 3.9 | 0.5 | 0.7 | 3.3 | 1.0 | 0.83 | marginal |
| elbow at setup | ° | 1.9 | 0.2 | 0.2 | 1.3 | 0.6 | 0.72 | marginal |
| trunk at setup | ° | 2.3 | 0.3 | 0.3 | 1.0 | 0.5 | 0.43 | usable |
| transition | ms | 26 | -2 | 4 | 17 | 8 | 0.64 | marginal |
| hip at transition | ° | 2.5 | -0.7 | 1.6 | 6.7 | 3.3 | 2.72 | unusable |
| knee at transition | ° | 3.1 | 0.1 | 0.1 | 0.5 | 0.4 | 0.16 | usable |
| elbow at transition | ° | 4.2 | 0.4 | 1.3 | 5.1 | 2.4 | 1.22 | unusable |
| trunk at transition | ° | 1.4 | 0.6 | 1.1 | 4.5 | 2.3 | 3.30 | unusable |
| catch | ms | 69 | 28 | 23 | 171 | 96 | 2.46 | unusable |
| hip at catch | ° | 3.2 | 0.4 | 0.6 | 1.6 | 0.8 | 0.50 | marginal |
| knee at catch | ° | 5.2 | 0.1 | 0.4 | 1.5 | 1.4 | 0.30 | usable |
| elbow at catch | ° | 3.9 | 0.3 | 1.0 | 7.1 | 4.0 | 1.82 | unusable |
| trunk at catch | ° | 1.6 | -0.2 | 0.3 | 1.1 | 0.5 | 0.66 | marginal |
| lockout | ms | 152 | 5 | 4 | 25 | 12 | 0.16 | usable |
| hip at lockout | ° | 2.4 | -0.2 | 0.2 | 1.0 | 0.6 | 0.40 | usable |
| knee at lockout | ° | 0.6 | 0.3 | 0.3 | 1.2 | 1.2 | 2.15 | unusable |
| elbow at lockout | ° | 5.8 | 0.0 | 0.5 | 1.9 | 0.7 | 0.33 | usable |
| trunk at lockout | ° | 2.5 | -0.0 | 0.1 | 0.6 | 0.2 | 0.26 | usable |
| B2 X1 | cm | 1.0 | 0.0 | 0.0 | 0.2 | 0.1 | 0.20 | usable |
| B3 X2 | cm | 1.6 | -0.0 | 0.1 | 0.2 | 0.2 | 0.14 | usable |
| B4 Xloop | cm | 2.5 | 0.1 | 0.3 | 1.0 | 0.5 | 0.41 | usable |
| B5 Xnet | cm | 5.9 | -0.1 | 0.1 | 0.4 | 0.3 | 0.07 | usable |
| B8 drop | cm | 1.3 | -0.0 | 0.0 | 0.1 | 0.1 | 0.11 | usable |
| C1 peak bar velocity | m/s | 0.16 | -0.05 | 0.05 | 0.12 | 0.07 | 0.75 | marginal |
| D4 turnover (to lowest bar velocity) | ms | 55 | 26 | 31 | 162 | 125 | 2.96 | unusable |
| D4 turnover (to bar catch), alt. | ms | 48 | 18 | 21 | 129 | 108 | 2.71 | unusable |

## 30 fps (8 offsets × 6 reps)

| marker | unit | SD 240 | bias | median \|Δ\| | max \|Δ\| | max \|Δ\| off 0 | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| setup | ms | 52 | 28 | 29 | 62 | 42 | 1.19 | unusable |
| hip at setup | ° | 3.9 | -0.8 | 0.6 | 4.4 | 0.5 | 1.12 | unusable |
| knee at setup | ° | 3.9 | 1.4 | 1.6 | 6.7 | 2.6 | 1.69 | unusable |
| elbow at setup | ° | 1.9 | 0.5 | 0.5 | 3.4 | 1.0 | 1.81 | unusable |
| trunk at setup | ° | 2.3 | 0.8 | 0.9 | 2.3 | 1.7 | 1.00 | unusable |
| transition | ms | 26 | -0 | 8 | 29 (1 missing) | 25 | 1.12 | unusable |
| hip at transition | ° | 2.5 | -0.3 | 2.8 | 11.2 (1 missing) | 8.9 | 4.55 | unusable |
| knee at transition | ° | 3.1 | -0.2 | 0.7 | 2.1 (1 missing) | 2.1 | 0.68 | unusable |
| elbow at transition | ° | 4.2 | 0.2 | 2.1 | 7.5 (1 missing) | 7.5 | 1.80 | unusable |
| trunk at transition | ° | 1.4 | -0.1 | 2.2 | 7.4 (1 missing) | 6.0 | 5.43 | unusable |
| catch | ms | 69 | 25 | 50 | 167 | 58 | 2.40 | unusable |
| hip at catch | ° | 3.2 | 0.9 | 1.0 | 5.7 | 2.0 | 1.82 | unusable |
| knee at catch | ° | 5.2 | 0.5 | 0.8 | 3.6 | 3.0 | 0.70 | marginal |
| elbow at catch | ° | 3.9 | 0.1 | 1.5 | 11.6 | 2.2 | 3.01 | unusable |
| trunk at catch | ° | 1.6 | -0.5 | 0.6 | 3.2 | 1.6 | 1.93 | unusable |
| lockout | ms | 152 | 12 | 12 | 42 | 25 | 0.27 | usable |
| hip at lockout | ° | 2.4 | -0.6 | 0.6 | 2.7 | 1.7 | 1.13 | unusable |
| knee at lockout | ° | 0.6 | 0.9 | 0.7 | 3.3 | 1.2 | 5.85 | unusable |
| elbow at lockout | ° | 5.8 | 0.0 | 0.6 | 4.0 | 1.9 | 0.68 | marginal |
| trunk at lockout | ° | 2.5 | -0.1 | 0.2 | 1.4 | 0.8 | 0.56 | marginal |
| B2 X1 | cm | 1.0 | 0.1 | 0.0 | 0.5 (1 missing) | 0.2 | 0.46 | unusable |
| B3 X2 | cm | 1.6 | -0.0 | 0.1 | 0.5 (1 missing) | 0.3 | 0.34 | unusable |
| B4 Xloop | cm | 2.5 | 0.0 | 0.6 | 2.5 | 1.2 | 1.01 | unusable |
| B5 Xnet | cm | 5.9 | -0.2 | 0.2 | 0.8 | 0.5 | 0.13 | usable |
| B8 drop | cm | 1.3 | -0.1 | 0.1 | 0.3 | 0.2 | 0.22 | usable |
| C1 peak bar velocity | m/s | 0.16 | -0.07 | 0.07 | 0.14 | 0.12 | 0.88 | marginal |
| D4 turnover (to lowest bar velocity) | ms | 55 | 17 | 42 | 179 | 125 | 3.26 | unusable |
| D4 turnover (to bar catch), alt. | ms | 48 | 11 | 38 | 142 | 142 | 2.97 | unusable |

## Verdict per rate and group

| group | 120 fps | 60 fps | 30 fps |
|---|---|---|---|
| phase marks | usable | usable | unusable |
| turnover (D4) | unusable | unusable | unusable |
| peak bar velocity (C1) | usable | marginal | marginal |
| bar displacements (B2–B5, B8) | usable | usable | unusable |
| joint angles at phases | usable | usable | unusable |
