#!/bin/bash
# Full-page PNG of a local HTML page (a /show-me:show-me explainer), for the PR: GitHub shows
# no HTML and the repo is private, so the PR gets the picture, not a link.
# usage: .claude/skills/verify/scripts/screenshot.sh <page.html> <evidence_root>/explain.png
# Uses the installed Google Chrome (playwright --channel chrome); no browser download.
# publish_evidence.sh puts every image at the top of <evidence_root> under "Explainer".
set -e
[ -f "$1" ] && [ -n "$2" ] || { echo 'FAIL: usage: screenshot.sh <page.html> <out.png>'; exit 1; }
page=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
playwright screenshot --channel chrome --full-page --viewport-size=1280,800 --wait-for-timeout=1500 "file://$page" "$2" >/dev/null
echo "screenshot: $2"
