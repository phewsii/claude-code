#!/bin/bash
# Shared helpers for the goal plugin. Source, don't execute.
# Portable: bash 3.2 + BSD/GNU userland. Requires jq.

GOAL_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude"
GOAL_FILE="$GOAL_DIR/goal.local.md"
GOAL_ARCHIVE_DIR="$GOAL_DIR/goals"

now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Print the frontmatter block (without the --- delimiters).
fm_block() {
  awk 'NR==1 && $0=="---" {inside=1; next} inside && $0=="---" {exit} inside {print}' "$GOAL_FILE"
}

# fm_get KEY -> raw value (string after "KEY: ").
fm_get() {
  fm_block | awk -v k="$1" 'index($0, k ": ") == 1 {print substr($0, length(k) + 3); exit}'
}

# fm_get_str KEY -> decoded JSON string value.
fm_get_str() {
  local raw
  raw=$(fm_get "$1")
  [[ -z "$raw" ]] && return 0
  printf '%s' "$raw" | jq -r '.' 2>/dev/null || printf '%s' "$raw"
}

# fm_set KEY RAW_VALUE -> rewrite one frontmatter key atomically.
fm_set() {
  local tmp="$GOAL_FILE.tmp.$$"
  awk -v k="$1" -v v="$2" '
    NR==1 && $0=="---" {inside=1; print; next}
    inside && $0=="---" {inside=0; print; next}
    inside && index($0, k ": ") == 1 {print k ": " v; next}
    {print}
  ' "$GOAL_FILE" > "$tmp" && mv "$tmp" "$GOAL_FILE"
}

# json_str VALUE -> JSON-encoded string, safe as a YAML double-quoted scalar.
json_str() { printf '%s' "$1" | jq -Rs '.'; }

# Body (everything after the closing frontmatter delimiter).
goal_body() { awk '/^---$/ && c<2 {c++; next} c>=2' "$GOAL_FILE"; }

# First non-empty line of the objective section.
goal_objective() {
  goal_body | awk '/^# Goal/ {g=1; next} g && /^## / {exit} g && NF {print; exit}'
}

# Unchecked criteria lines within the Success criteria section.
goal_unchecked() {
  goal_body | awk '/^## Success criteria/ {s=1; next} s && /^## / {exit} s && /^[[:space:]]*[-*] \[ \]/ {print}'
}

goal_count() {
  goal_body | awk -v pat="$1" '/^## Success criteria/ {s=1; next} s && /^## / {exit} s && $0 ~ pat {n++} END {print n+0}'
}

# Append a line to the Progress log (end of file).
log_append() { printf -- '- %s — %s\n' "$(now_utc)" "$1" >> "$GOAL_FILE"; }

archive_goal() {
  mkdir -p "$GOAL_ARCHIVE_DIR"
  local slug
  slug=$(goal_objective | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | cut -c1-40 | sed 's/^-*//; s/-*$//')
  local dest="$GOAL_ARCHIVE_DIR/$(date -u +%Y%m%dT%H%M%SZ)-${slug:-goal}.md"
  mv "$GOAL_FILE" "$dest"
  printf '%s' "$dest"
}

is_uint() { [[ "$1" =~ ^[0-9]+$ ]]; }
