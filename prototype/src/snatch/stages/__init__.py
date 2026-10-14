from snatch.stage import Stage
from snatch.stages import athlete, calibrate, person, plate, pose, probe, side

# todo: S1 and S2 both read only the clip and could run in parallel (pipeline-v2); sequential for now
STAGES: list[Stage] = [probe.STAGE, athlete.STAGE, person.STAGE, pose.STAGE, side.STAGE, plate.STAGE]
# --calibrate: C1 = S1 and C2 = S4 on the bar-only clip, then C3 fits the skeleton
CALIBRATE: list[Stage] = [probe.STAGE, athlete.STAGE, person.STAGE, pose.STAGE, calibrate.STAGE]
