# Phase review (#13)

Phase frames are marked by definition v2 (hub height). For each event look at the middle row of the sheet (rows above/below are -0.1 s / +0.1 s for timing).

Verdict per phase: **accept**, or **correct** with the rule/frame you would use. Visibility: tick a joint only if you can really see it on the middle-row frame (behind plate / out of view = not visible). Near side = lifter's right.

## 4581_rep1  (`4581_rep1.jpg`)

| phase | frame | t (s) | verdict | corrected rule / frame | sho | elb | wri | hip | kne | ank |
|---|---|---|---|---|---|---|---|---|---|---|
| setup | 786 | 3.275 | accept | bar sleeve leaves floor ~+5…+12 f; ≤0.05 s early | [x] | [x] | [ ] | [x] | [ ] | [ ] |
| transition | 925 | 3.854 | accept | end of re-bend, bar mid/upper thigh | [x] | [x] | [ ] | [ ] | [ ] | [x] |
| catch | 1102 | 4.592 | accept | bottom of (high) receiving squat; within ~20 f of bar low | [x] | [x] | [ ] | [x] | [x] | [x] |
| lockout | 1365 | 5.688 | accept | upright, arms locked; ±0.1 s identical | [x] | [x] | [ ] | [x] | [x] | [x] |

## 4583_rep1  (`4583_rep1.jpg`)

| phase | frame | t (s) | verdict | corrected rule / frame | sho | elb | wri | hip | kne | ank |
|---|---|---|---|---|---|---|---|---|---|---|
| setup | 968 | 4.033 | accept | bar sleeve leaves floor ~+5…+12 f; ≤0.05 s early | [x] | [x] | [ ] | [x] | [ ] | [ ] |
| transition | 1114 | 4.642 | accept? | possibly ~10–20 f late: torso near vertical, peak bar speed only +25 ms after | [x] | [x] | [ ] | [ ] | [ ] | [x] |
| catch | 1285 | 5.354 | accept | bottom of (high) receiving squat; within ~20 f of bar low | [x] | [x] | [ ] | [x] | [x] | [x] |
| lockout | 1577 | 6.571 | accept | upright, arms locked; ±0.1 s identical | [x] | [x] | [ ] | [x] | [x] | [x] |

## 4584_rep1  (`4584_rep1.jpg`)

| phase | frame | t (s) | verdict | corrected rule / frame | sho | elb | wri | hip | kne | ank |
|---|---|---|---|---|---|---|---|---|---|---|
| setup | 925 | 3.854 | accept | bar sleeve leaves floor ~+5…+12 f; ≤0.05 s early | [x] | [x] | [ ] | [x] | [ ] | [ ] |
| transition | 1065 | 4.438 | accept | end of re-bend, bar mid/upper thigh | [x] | [x] | [ ] | [ ] | [ ] | [x] |
| catch | 1238 | 5.158 | accept | bottom of (high) receiving squat; within ~20 f of bar low | [x] | [x] | [ ] | [x] | [x] | [x] |
| lockout | 1471 | 6.129 | accept | upright, arms locked; ±0.1 s identical | [x] | [x] | [ ] | [x] | [x] | [x] |

## 4584_rep2  (`4584_rep2.jpg`)

| phase | frame | t (s) | verdict | corrected rule / frame | sho | elb | wri | hip | kne | ank |
|---|---|---|---|---|---|---|---|---|---|---|
| setup | 2483 | 10.346 | accept | bar sleeve leaves floor ~+5…+12 f; ≤0.05 s early | [x] | [x] | [ ] | [x] | [ ] | [ ] |
| transition | 2630 | 10.958 | accept | end of re-bend, bar mid/upper thigh | [x] | [x] | [ ] | [ ] | [ ] | [x] |
| catch | 2781 | 11.588 | accept | bottom of (high) receiving squat; within ~20 f of bar low | [x] | [x] | [ ] | [x] | [x] | [x] |
| lockout | 3010 | 12.542 | accept | upright, arms locked; ±0.1 s identical | [x] | [x] | [ ] | [x] | [x] | [x] |

## 4587_rep1  (`4587_rep1.jpg`)

| phase | frame | t (s) | verdict | corrected rule / frame | sho | elb | wri | hip | kne | ank |
|---|---|---|---|---|---|---|---|---|---|---|
| setup | 854 | 3.558 | accept | bar sleeve leaves floor ~+5…+12 f; ≤0.05 s early | [x] | [x] | [ ] | [x] | [ ] | [ ] |
| transition | 982 | 4.092 | accept? | possibly ~10 f late: torso near vertical, peak bar speed +67 ms after | [x] | [x] | [ ] | [ ] | [ ] | [x] |
| catch | 1116 | 4.650 | accept | bottom of (high) receiving squat; within ~20 f of bar low | [x] | [x] | [ ] | [x] | [x] | [x] |
| lockout | 1353 | 5.638 | accept | upright, arms locked; ±0.1 s identical | [x] | [x] | [ ] | [x] | [x] | [x] |

## 4587_rep2  (`4587_rep2.jpg`)

| phase | frame | t (s) | verdict | corrected rule / frame | sho | elb | wri | hip | kne | ank |
|---|---|---|---|---|---|---|---|---|---|---|
| setup | 2354 | 9.808 | accept | bar sleeve leaves floor ~+5…+12 f; ≤0.05 s early | [x] | [x] | [ ] | [x] | [ ] | [ ] |
| transition | 2488 | 10.367 | accept | end of re-bend, bar mid/upper thigh | [x] | [x] | [ ] | [ ] | [ ] | [x] |
| catch | 2614 | 10.892 | accept | bottom of (high) receiving squat; within ~20 f of bar low | [x] | [x] | [ ] | [x] | [x] | [x] |
| lockout | 2855 | 11.896 | accept | upright, arms locked; ±0.1 s identical | [x] | [x] | [ ] | [x] | [x] | [x] |

## Reviewer summary (outside review, AI agent; input to the developer's verdict, not a replacement)

Method: looked at all 6 sheets; for setup also zoomed plate-bottom crops (f −24/0/+12/+24/+48, clips 4581/4583/4587) and read the raw hub rise and post-peak bar low from `plate.npz` / `raw_pose.npz`.

| rep | setup | transition | catch | lockout |
|---|---|---|---|---|
| 4581 r1 | accept (bar rises >3 px at +8 f) | accept | accept (bar low f1103) | accept |
| 4583 r1 | accept (+7 f) | accept? maybe 10–20 f late | accept (bar low f1266, −19 f) | accept |
| 4584 r1 | accept (−1 f) | accept | accept (bar low f1233) | accept |
| 4584 r2 | accept (+4 f) | accept | accept (bar low f2795, +14 f) | accept |
| 4587 r1 | accept (+1 f) | accept? maybe ~10 f late | accept (bar low f1127, +11 f) | accept |
| 4587 r2 | accept (+5 f) | accept | accept (bar low f2645, +31 f) | accept |

Systematic findings:

- **setup is not 0.1 s early.** At sheet scale the bar looks still at +0.1 s, but zoomed crops show the sleeve still on the floor at the marked frame, slightly up at +12 f and clearly up (~2–3 cm hub rise) at +24 f. Hub rises >3 px within −1…+8 f of the mark. At most ~0.03 s early. The long first pull (0.53–0.61 s vs 0.42 s) comes from a slow break-off by non-elite lifters, not from the mark.
- **transition** = end of the knee re-bend (bar at mid/upper thigh, knees under the bar). Row 1 (−0.1 s) shows the end of the first pull (bar at the knee, torso inclined); row 3 shows full extension. So the mark sits at the start of the second pull, as intended. On 4583 r1 and 4587 r1 the torso already looks near vertical and peak bar speed follows only 25/67 ms later, so these two may be slightly late. Low dips (−4…−6°) make the knee minimum flat there.
- **catch** is the bottom of the receiving squat: all three rows look nearly the same (static hold), and lowest hip falls within −19…+31 f of the bar's lowest point after the turnover. All receptions are high (hips above knees, power-snatch depth). A catch later than the end of the second pull is expected (second pull → turnover → catch).
- **lockout:** fully upright with arms locked in all rows, accept. The ±0.1 s frames look the same, so the sheets can't pin the exact frame better than about ±24 f.

Visibility (same in all 6 reps):
- wrist never visible: inside the plate outline at setup, transition and catch, and at the plate rim at lockout.
- setup: ankle and knee hidden behind the plate and arm.
- transition: hip and knee behind the plate.
- otherwise visible.
- knee at setup and wrist at lockout are borderline calls.

Confidence: high for setup (zoom + data), catch and lockout. Medium for transition: the true knee minimum can't be resolved from 3 frames 24 f apart, and a 240 fps frame strip ±30 f around the mark is needed for 4583 r1 and 4587 r1. Images were big enough to judge posture, but too small for 1–2 cm bar motion without zoom.
