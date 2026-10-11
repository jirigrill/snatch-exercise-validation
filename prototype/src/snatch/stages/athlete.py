"""S0: check the athlete profile (height, skeleton) before any heavy stage.

Not hashed: it reads and writes athletes/<athlete>/, not out/<clip>/, and runs
every time. --height writes athlete.json (the latest value wins). A missing
height stops with exit 7, a missing skeleton with exit 2; both missing is one
message with exit 2. --calibrate skips the skeleton check.
"""

from datetime import datetime, timezone
from pathlib import Path

from snatch import athlete_store
from snatch.stage import Context, Stage, StageStop

NO_SKELETON_EXIT = 2
NO_HEIGHT_EXIT = 7
HEIGHT_RANGE_M = (1.40, 2.20)
KNEE_PER_HEIGHT = 0.285


def check_height(height_m: float) -> float:
    lo, hi = HEIGHT_RANGE_M
    if not lo <= height_m <= hi:
        raise ValueError(f"height {height_m} m is outside {lo:.2f} to {hi:.2f} m (cm typed as m?)")
    return height_m


def _stored_height_ok(ctx: Context, athlete: str) -> bool:
    try:
        prof = athlete_store.load(ctx.athletes, athlete, athlete_store.ATHLETE)
        check_height(float(prof["height_m"]))  # type: ignore[index]
    except (ValueError, TypeError, KeyError):
        return False
    return True


def run(ctx: Context, _tmp: Path) -> None:
    athlete = str(ctx.params["athlete"])
    height = ctx.params.get("height")
    if height is not None:
        try:
            h = check_height(float(height))
        except ValueError as e:
            raise StageStop(NO_HEIGHT_EXIT, "needs_height", str(e)) from None
        athlete_store.save(ctx.athletes, athlete, athlete_store.ATHLETE, {
            "athlete": athlete, "height_m": h, "knee_height_m": round(KNEE_PER_HEIGHT * h, 4),
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    no_height = not _stored_height_ok(ctx, athlete)
    no_skeleton = not ctx.params.get("calibrate") and not athlete_store.exists(
        ctx.athletes, athlete, athlete_store.SKELETON)
    height_msg = f"no height for {athlete}, run with --height <m>"
    skeleton_msg = (f"No skeleton for {athlete}. Record a bar-only snatch clip (no plates, same camera spot) "
                    f"and run: pipeline.py --calibrate <bar.MOV> --athlete {athlete}")
    if no_skeleton:
        reason = f"{height_msg}; {skeleton_msg}" if no_height else skeleton_msg
        raise StageStop(NO_SKELETON_EXIT, "needs_calibration", reason)
    if no_height:
        raise StageStop(NO_HEIGHT_EXIT, "needs_height", height_msg)


STAGE = Stage("S0", (), (), run, always=True)
