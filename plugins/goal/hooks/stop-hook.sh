#!/bin/bash
# Goal Stop hook: keep Claude working until the goal is verifiably complete.
# Decision table: see SPEC.md. Never traps the user on corrupt state.
set -uo pipefail
source "${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/scripts/lib.sh"

HOOK_INPUT=$(cat)
[[ -f "$GOAL_FILE" ]] || exit 0
[[ "$(fm_get status)" == "active" ]] || exit 0

warn_and_release() {
  echo "⚠️  Goal: $1 — pausing goal so you aren't trapped. Fix $GOAL_FILE and run /goal resume." >&2
  fm_set status paused 2>/dev/null
  exit 0
}

ITERATION=$(fm_get iteration)
MAX_ITERATIONS=$(fm_get max_iterations)
is_uint "$ITERATION" || warn_and_release "'iteration' is not a number (got '$ITERATION')"
is_uint "$MAX_ITERATIONS" || warn_and_release "'max_iterations' is not a number (got '$MAX_ITERATIONS')"

# --- session binding: only the owning session is driven by the goal ---
SESSION_ID=$(printf '%s' "$HOOK_INPUT" | jq -r '.session_id // ""')
BOUND=$(fm_get_str session_id)
if [[ -n "$BOUND" && -n "$SESSION_ID" && "$BOUND" != "$SESSION_ID" ]]; then
  exit 0
fi
[[ -z "$BOUND" && -n "$SESSION_ID" ]] && fm_set session_id "$(json_str "$SESSION_ID")"

# --- last assistant text ---
LAST_TEXT=$(printf '%s' "$HOOK_INPUT" | jq -r '.last_assistant_message // empty' 2>/dev/null)
if [[ -z "$LAST_TEXT" ]]; then
  TRANSCRIPT=$(printf '%s' "$HOOK_INPUT" | jq -r '.transcript_path // ""')
  if [[ -f "$TRANSCRIPT" ]]; then
    # Last assistant entry that actually has text (entries may be tool_use only).
    LAST_TEXT=$(tail -n 400 "$TRANSCRIPT" | jq -rs '
      [ .[] | select(.message.role? == "assistant")
            | [ .message.content[]? | select(.type == "text") | .text ] | join("\n")
            | select(length > 0) ] | last // ""' 2>/dev/null || true)
  fi
fi

block() {  # block REASON SYSTEM_MSG
  jq -n --arg r "$1" --arg m "$2" '{decision: "block", reason: $r, systemMessage: $m}'
  exit 0
}

# --- honest escape hatch ---
BLOCKED_REASON=$(printf '%s' "$LAST_TEXT" | perl -0777 -ne 'if (/<goal-blocked>(.*?)<\/goal-blocked>/s) { $r=$1; $r =~ s/\s+/ /g; $r =~ s/^ | $//g; print $r }' 2>/dev/null)
if [[ -n "$BLOCKED_REASON" ]]; then
  fm_set status paused
  log_append "Blocked: $BLOCKED_REASON"
  jq -n --arg m "⏸️  Goal paused — Claude reported a blocker: $BLOCKED_REASON. Unblock it, then /goal resume." '{systemMessage: $m}'
  exit 0
fi

# --- completion claim: verify gates ---
if printf '%s' "$LAST_TEXT" | grep -q '<goal-complete>'; then
  UNCHECKED=$(goal_unchecked)
  if [[ -n "$UNCHECKED" ]]; then
    log_append "Completion rejected: unchecked criteria."
    block "Your <goal-complete> claim was REJECTED: these success criteria are not checked off in $GOAL_FILE:

$UNCHECKED

Either finish them (then tick them with [x] and log the evidence), or, if a criterion is wrong, explain why in the progress log and fix it. Then claim completion again." \
      "🎯 Goal: completion rejected — unchecked criteria remain"
  fi

  VERIFY=$(fm_get_str verify_command)
  if [[ -n "$VERIFY" ]]; then
    VERIFY_OUT=$(cd "${CLAUDE_PROJECT_DIR:-.}" && bash -c "$VERIFY" 2>&1)
    VERIFY_RC=$?
    if [[ $VERIFY_RC -ne 0 ]]; then
      log_append "Completion rejected: verify command exited $VERIFY_RC."
      block "Your <goal-complete> claim was REJECTED: the verify command failed (exit $VERIFY_RC).

\$ $VERIFY
$(printf '%s\n' "$VERIFY_OUT" | tail -n 60)

Fix the failures, untick any criteria that are not actually met, and try again." \
        "🎯 Goal: completion rejected — verify command failed (exit $VERIFY_RC)"
    fi
  fi

  fm_set status complete
  log_append "Goal complete (verified after $ITERATION continuation rounds)."
  DEST=$(archive_goal)
  jq -n --arg m "✅ Goal achieved and verified. Archived to $DEST" '{systemMessage: $m}'
  exit 0
fi

# --- safety cap ---
if [[ $MAX_ITERATIONS -gt 0 && $ITERATION -ge $MAX_ITERATIONS ]]; then
  fm_set status paused
  log_append "Paused: reached max iterations ($MAX_ITERATIONS)."
  jq -n --arg m "🛑 Goal paused after $MAX_ITERATIONS iterations without verified completion. Review $GOAL_FILE, then /goal resume." '{systemMessage: $m}'
  exit 0
fi

# --- keep going ---
NEXT=$((ITERATION + 1))
fm_set iteration "$NEXT"
CAP=$([[ $MAX_ITERATIONS -gt 0 ]] && echo "$MAX_ITERATIONS" || echo "∞")

block "Continue working toward your active goal (iteration $NEXT/$CAP). Current goal file ($GOAL_FILE):

$(goal_body)

Protocol:
1. Pick the next unchecked criterion and make concrete progress on it.
2. After real progress, tick criteria you have VERIFIED ([x]) and append a one-line entry with evidence to the Progress log.
3. When every criterion is ticked and verified, output <goal-complete> (the hook will re-check criteria$([[ -n "$(fm_get_str verify_command)" ]] && echo ' and run the verify command')).
4. If you truly cannot proceed without the user (missing access, a decision only they can make), output <goal-blocked>short reason</goal-blocked>. Never claim completion falsely." \
  "🎯 Goal iteration $NEXT/$CAP — $(goal_objective | cut -c1-80)"
