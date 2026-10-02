#!/bin/bash
# /goal entry point: set | status | pause | resume | clear | help
set -euo pipefail
source "$(dirname "$0")/lib.sh"

usage() {
  cat <<'HELP'
/goal — goal-driven autonomous work

USAGE
  /goal <objective> [--criteria TEXT]... [--verify CMD] [--max-iterations N] [--force]
  /goal [status]      Show the active goal and progress
  /goal pause         Pause (Claude may stop; nothing is lost)
  /goal resume        Resume a paused goal in this session
  /goal clear         Delete the goal without archiving
  /goal help          This help

OPTIONS
  --criteria TEXT       A verifiable success criterion (repeatable). If omitted,
                        Claude writes 3-7 criteria itself before starting.
  --verify CMD          Shell command that must exit 0 before the goal can complete
                        (e.g. "npm test", "pytest -q && ruff check .")
  --max-iterations N    Pause after N continuation rounds (default 20, 0 = unlimited)
  --force               Replace an existing active goal

HOW IT ENDS
  Claude outputs <goal-complete> -> hook checks every criterion is ticked and the
  verify command passes. Fails -> keeps working. Passes -> goal archived to
  .claude/goals/.
  Claude outputs <goal-blocked>reason</goal-blocked> -> goal paused for you.

EXAMPLES
  /goal Add OAuth login with Google --verify "npm test" --max-iterations 30
  /goal Get the build green --criteria "make build exits 0" --criteria "no new warnings"
HELP
}

show_status() {
  if [[ ! -f "$GOAL_FILE" ]]; then
    echo "No goal set. Start one with: /goal <objective>"
    return 0
  fi
  local done total
  done=$(goal_count '^[[:space:]]*[-*] \\[[xX]\\]')
  total=$(( done + $(goal_count '^[[:space:]]*[-*] \\[ \\]') ))
  local max; max=$(fm_get max_iterations)
  echo "🎯 Goal status: $(fm_get status) | iteration $(fm_get iteration)/$([[ "$max" == 0 ]] && echo ∞ || echo "$max") | criteria $done/$total"
  local v; v=$(fm_get_str verify_command)
  echo "   Verify: ${v:-none}"
  echo "   File:   $GOAL_FILE"
  echo
  goal_body
}

cmd="${1:-status}"
case "$cmd" in
  help|-h|--help) usage; exit 0 ;;
  status) show_status; exit 0 ;;
  pause|resume|clear)
    if [[ ! -f "$GOAL_FILE" ]]; then echo "No goal set."; exit 0; fi
    case "$cmd" in
      pause)  fm_set status paused; log_append "Paused by user."; echo "⏸️  Goal paused. Resume with /goal resume." ;;
      resume) fm_set status active; fm_set session_id '""'; fm_set iteration 0; log_append "Resumed by user."
              echo "▶️  Goal resumed (iteration counter reset)."; echo; show_status ;;
      clear)  rm -f "$GOAL_FILE"; echo "🗑️  Goal cleared." ;;
    esac
    exit 0 ;;
esac

# --- set a new goal ---
OBJ_PARTS=()
CRITERIA=()
VERIFY=""
MAX_ITERATIONS=20
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --criteria)
      [[ -n "${2:-}" ]] || { echo "❌ --criteria needs text" >&2; exit 1; }
      CRITERIA+=("$2"); shift 2 ;;
    --verify)
      [[ -n "${2:-}" ]] || { echo "❌ --verify needs a command" >&2; exit 1; }
      VERIFY="$2"; shift 2 ;;
    --max-iterations)
      is_uint "${2:-}" || { echo "❌ --max-iterations must be a non-negative integer, got: '${2:-}'" >&2; exit 1; }
      MAX_ITERATIONS="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) OBJ_PARTS+=("$1"); shift ;;
  esac
done

OBJECTIVE="${OBJ_PARTS[*]:-}"
[[ -n "$OBJECTIVE" ]] || { echo "❌ No objective given." >&2; echo >&2; usage >&2; exit 1; }

if [[ -f "$GOAL_FILE" && "$(fm_get status)" == "active" && $FORCE -eq 0 ]]; then
  echo "❌ A goal is already active: $(goal_objective)" >&2
  echo "   Use /goal clear, /goal pause, or pass --force to replace it." >&2
  exit 1
fi

mkdir -p "$GOAL_DIR"
{
  echo "---"
  echo "status: active"
  echo "iteration: 0"
  echo "max_iterations: $MAX_ITERATIONS"
  echo "verify_command: $(json_str "$VERIFY")"
  echo 'session_id: ""'
  echo "started_at: \"$(now_utc)\""
  echo "---"
  echo
  echo "# Goal"
  echo
  echo "$OBJECTIVE"
  echo
  echo "## Success criteria"
  echo
  if [[ ${#CRITERIA[@]} -eq 0 ]]; then
    echo "- [ ] (define 3-7 concrete, verifiable criteria — replace this line)"
  else
    for c in "${CRITERIA[@]}"; do echo "- [ ] $c"; done
  fi
  echo
  echo "## Progress log"
  echo
  echo "- $(now_utc) — Goal set."
} > "$GOAL_FILE"

echo "🎯 GOAL SET"
echo
show_status
