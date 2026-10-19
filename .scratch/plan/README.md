# Pipeline v2: plan

Spec: `docs/pipeline-v2.html`. Stage details: `B-front.md`, `C-skeleton.md`, `D-judge.md`.

New session: "Do the next unchecked item in .scratch/plan/README.md."

Goal: pipeline v2 judges every labelled clip as labels.csv says (S8 at 100 % agreement), each stage checked on the test clips. Each item says how it moves toward this.

## Checklist
- [x] P0 test clips T1–T7 (#51)
- [x] A runner, stage contract, S−1 probe, S0 athlete store (#50)
- [x] B prep: frame times, Halpe-26 + facing, cut-clip fix (#52)
- [x] S1 person: B-front.md. Done: person.npz + 1_person.mp4 on T1. (#54)
- [x] S4 pose, exit 8: B-front.md. Whole clip for now (no attempt windows yet; calibrate C2 always poses the whole clip). Done: 4_pose.mp4 looks right on T1. Facing in facing.json, side derived. (#55)
- [x] C3 calibrate: C-skeleton.md. Done: bar-only clip → skeleton.json; run_clip.sh uses it instead of the `{}` placeholder; S4 missing side → exit 2 (B-front.md). Knee length table only, no wrist offset (wrist under the plate can't be checked on a loaded clip; revisit if S7/S8 need a wrist angle).
- [x] S2 plate, exits 4/6: B-front.md (#63). Done: plate outputs on T1, exit 6 on a bar-only clip. Tests: apply the CLAUDE.md test rule to test_plate.py (keep R1–R5, delete what the clip now covers).
- [x] S3 attempts: B-front.md. S4 then poses attempt windows ± 1 s only (calibrate stays whole clip). Done: attempts.json rep count = find_reps on T1–T7 (1 each; T5 stops at S2). T7 (standup) = 1 attempt by the spec's knee gate, a failed one for S8 (`no_overhead`); decided in #67, CLAUDE.md + test-clips.md updated. #67 also adds T8 (2 attempts) and moves S5's standing window from the padding to every posed frame (C-skeleton.md). Open from it: zero attempts has no stop rule (S4 crashes, exit 1); scripts/find_reps.py + reps.find_lifts/find_pose_* are v1-only, delete with run_all.sh (S9).
- [x] Remove v1 (scripts, run_all.sh, v1 parts of reps, spread/phases/angles, studies; HALPE26 → pose.py): B-milestone.md, item 0. Drops the old T6 item (B2 settles T6's count; with B moved after D, labels.csv does). (#68: sagittal_angles moved to skeleton.py (C3 uses it); v1 cross-clip results in out/ deleted; spec + CLAUDE.md check 3 updated. S6 restores its studies code from git 6469c5b.) Follow-up #69: frames() stop, no more ffmpeg Broken pipe.
- [ ] S5 scale, exit 5: C-skeleton.md.
- [ ] S6 fill: C-skeleton.md. Done: filled knee matches 36-skeleton-fill. From C3 (#56): test "behind the plate" with the real S2 plate track, check airborne frames (shank reads +6 % on toes, f1695–1698 on T5).
- [ ] Milestone C: T1–T8 vs main.
- [ ] labels.csv: D-judge.md.
- [ ] S7 angles + events: D-judge.md. Written from scratch (angles.py, phases.py and their tests deleted with v1).
- [ ] S8 judge: D-judge.md. Thresholds from the spec / lifting rules, not fitted to the test clips (else S4 errors get absorbed and feasibility looks better than it is). Done: agreement vs labels.csv reported.
- [ ] S9 findings contract + report + delete run_all.sh: D-judge.md.
- [ ] Milestone D: all labelled clips end-to-end. For each disagreement with labels.csv: which stage's output was wrong (first guess, by eye). Decides feasibility: requirements met → build the full app; not met → Milestone B.
- [ ] Milestone B (only if D misses the goal): failure analysis, B-milestone.md (B1 marking tool + pilot, B2 blind marking + eye review, B3 human check), scoped to the clips and stages behind D's disagreements instead of all of T1–T8. Answers: would making those stages precise reach the goal? Moved after D on 2026-10-19 (pipeline first, to learn whether the requirements are reachable at all).

Workflow follow-ups (from #63: ~20 min of reruns the cache could have served, ~10 min waiting on an already finished job):
- [x] (#63) CLAUDE.md, Workflow: every pipeline run goes through the verify entry point (`run_clip.sh`), never a hand-run `pipeline.py`, so it gets the cache and the checks. Reuse a result only when its key says the inputs and code it depends on are unchanged; anything the change touches reruns, and no check is skipped for speed. Subagent briefs say how to verify through it, and keep a unit on the critical path in one agent instead of splitting off work that has to wait for it. Wait on a background job's own completion notice, not a process poll.
- [x] (#63) Stage cache: one stage with the same key gives the same outputs whichever stage list ran it (analyze or `--calibrate`), so store and restore it under that key regardless of the list. Today only `STAGES` is cached, so a clip's shared stages computed by one list rerun in the other. Check: the fresh audit (`VERIFY_NO_CACHE=1`) still matches what the cache restores, for every stage of both lists.

Todo: run S1 ∥ S2 in parallel (optional, sequential for now; also in stages/__init__.py).

Notes: detector exit crash (`recursive_mutex lock failed`) seen once; retry is OK, fix only if it recurs. Later: chase T2 catch timing in phase detection. `pv2/l-logic` may help S8.

## Rules
See `CLAUDE.md` in the repo root.
