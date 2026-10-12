#!/bin/bash
# Read-only: is this checkout worth driving? Exit 0 = yes. Prints one line per check.
# usage: .claude/skills/verify/scripts/doctor.sh
root=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$root/prototype" || exit 1
bad=0
chk() { if eval "$2" >/dev/null 2>&1; then echo "ok   $1"; else echo "FAIL $1"; bad=1; return 1; fi; }
chk "uv installed"                 "command -v uv"
chk ".venv present (uv sync)"      "[ -x .venv/bin/python ]"
chk "snatch imports"               "uv run python -c 'import snatch, onnxruntime, rtmlib, cv2'"
chk "halpe26 pose model cached"    "ls ~/.cache/rtmlib/hub/checkpoints/*halpe26*.onnx" ||
  echo "     download: cd prototype && uv run python -c 'from snatch import pose; pose.load_model()'"
chk "detector model cached"        "ls ~/.cache/rtmlib/hub/checkpoints/yolox_x_*.onnx"
chk "ffprobe installed"            "command -v ffprobe"
chk "test clips T1-T7 present"     "[ \$(ls ../vids/test/T[1-7]_*_{240,60}fps.MOV | wc -l) -eq 7 ]" ||
  echo "     rebuild per .claude/skills/verify/features/test-clips.md"
chk "CoreML provider available"    "uv run python -c 'import onnxruntime as o; assert \"CoreMLExecutionProvider\" in o.get_available_providers()'"
echo "branch: $(git -C "$root" rev-parse --abbrev-ref HEAD) $(git -C "$root" rev-parse --short HEAD), dirty files: $(git -C "$root" status --porcelain | wc -l | tr -d ' ')"
exit $bad
