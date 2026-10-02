#!/bin/bash
# Re-injects the active goal into context.
#   reminder: short line every prompt (UserPromptSubmit)
#   full:     whole goal file after resume/compaction (SessionStart)
set -uo pipefail
source "${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/scripts/lib.sh"

cat >/dev/null  # drain hook input
[[ -f "$GOAL_FILE" ]] || exit 0
STATUS=$(fm_get status)
[[ "$STATUS" == "active" || "$STATUS" == "paused" ]] || exit 0

if [[ "${1:-reminder}" == "full" ]]; then
  echo "🎯 You have a $STATUS goal tracked in $GOAL_FILE (context was restored, so here it is in full):"
  echo
  goal_body
  echo
  echo "Keep the file up to date: tick verified criteria, log progress. Finish with <goal-complete>, or <goal-blocked>reason</goal-blocked> if you need the user."
else
  NEXT=$(goal_unchecked | head -n 1 | sed 's/^[[:space:]]*[-*] \[ \] //')
  echo "🎯 Active goal ($STATUS): $(goal_objective | cut -c1-160)${NEXT:+ | Next unchecked criterion: $NEXT} | State: $GOAL_FILE"
  [[ "$STATUS" == "paused" ]] && echo "   (Goal is paused — only work on it if the user asks; they can run /goal resume.)"
fi
exit 0
