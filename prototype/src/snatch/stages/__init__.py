from snatch.stage import Stage
from snatch.stages import athlete, person, probe

# todo: S1 and S3 both read only the clip and could run in parallel (pipeline-v2); sequential for now
STAGES: list[Stage] = [probe.STAGE, athlete.STAGE, person.STAGE]
