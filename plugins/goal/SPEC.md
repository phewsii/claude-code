# /goal — Design Spec & Work Split

Architect: Claude Code. Builders: Claude Code (core) + Codex (tests, hardening, docs).
Read this whole file before touching code. Contracts below are binding; if you need
to change one, update this file in the same commit.

## What /goal does

`/goal <objective>` turns a session into a goal-driven worker:

1. **Run until done** – a Stop hook blocks Claude from ending its turn while a goal is
   active, feeding back the goal + remaining criteria each iteration.
2. **Track progress** – goal state lives in `.claude/goal.local.md` (frontmatter +
   markdown). Claude ticks criteria and appends to a progress log. Survives restarts
   and compaction.
3. **Verify completion** – Claude claims done with `<goal-complete>`. The hook only
   accepts it if (a) every `- [ ]` criterion is checked and (b) the optional
   `--verify` command exits 0. Otherwise it blocks and returns the failures.
4. **Stay on track** – UserPromptSubmit injects a short goal reminder every prompt;
   SessionStart (resume|compact) re-injects the full goal file.

Extras (beyond the basic ask):
- **Honest escape hatch** – `<goal-blocked>reason</goal-blocked>` pauses the goal and
  lets the session stop, so Claude never has to lie to exit. The reason is logged.
- **Safety cap** – `--max-iterations` (default 20, 0 = unlimited). Hitting it pauses
  (does not delete) the goal.
- **Session binding** – the first session to hit the Stop hook owns the goal; other
  sessions in the same repo are not hijacked. `/goal resume` rebinds.
- **History** – completed goals are archived to `.claude/goals/<UTC-timestamp>-<slug>.md`.
- **Verifier agent** – `goal-verifier` subagent does a skeptical review before Claude
  claims completion (advisory; the hard gates are checkboxes + verify command).

## Commands (single entry point: `scripts/goal.sh`)

| Invocation | Effect |
|---|---|
| `/goal <objective> [--criteria TEXT]... [--verify CMD] [--max-iterations N]` | Create goal (fails if one is active unless `--force`) |
| `/goal` or `/goal status` | Print goal file + iteration summary |
| `/goal pause` | status → paused (hook lets you stop) |
| `/goal resume` | status → active, clears session binding |
| `/goal clear` | Delete goal file (no archive) |
| `/goal help` | Usage |

## State file contract: `.claude/goal.local.md`

```
---
status: active            # active | paused | complete
iteration: 0
max_iterations: 20
verify_command: "npm test"   # JSON-encoded string, "" when none
session_id: ""               # bound on first Stop
started_at: "2026-10-02T12:00:00Z"
---

# Goal

<objective text>

## Success criteria

- [ ] criterion
- [x] done criterion

## Progress log

- 2026-10-02T12:00:00Z — Goal set.
```

Rules:
- Frontmatter values are single-line. `verify_command` is a JSON string (read with `jq -r`).
- If no `--criteria` are given, the Success criteria section contains a placeholder
  line `- [ ] (define 3-7 concrete, verifiable criteria)`; Claude must replace it first.
- Claude owns the body (ticks boxes, appends log lines). Scripts own the frontmatter.

## Stop hook decision table (`hooks/stop-hook.sh`)

Input: Stop hook JSON on stdin (`session_id`, `transcript_path`, optional
`last_assistant_message`). Output: nothing (allow) or
`{"decision":"block","reason":...,"systemMessage":...}`.

1. No state file, or status != active → allow.
2. session_id bound and != input session → allow. Unbound → bind to input session.
3. Last assistant text contains `<goal-blocked>R</goal-blocked>` → status=paused,
   log "Blocked: R", allow, systemMessage explains `/goal resume`.
4. Contains `<goal-complete>`:
   - unchecked criteria present → block, list them.
   - verify_command set and exits non-zero → block with last 60 lines of output.
   - else → status=complete, log, archive to `.claude/goals/`, delete state, allow.
5. iteration >= max_iterations (max>0) → status=paused, log, allow.
6. Otherwise → iteration++, block with continuation prompt (goal file contents +
   protocol reminder).

Corrupt state (non-numeric iteration etc.) → print warning to stderr, allow (never
trap the user).

## Work split

### Claude Code (core) — DONE (smoke-tested; see PR)
- `scripts/goal.sh`, `scripts/lib.sh`
- `hooks/stop-hook.sh`, `hooks/context-hook.sh`, `hooks/hooks.json`
- `commands/goal.md`, `agents/goal-verifier.md`, plugin.json, marketplace entry

### Codex — start now, in parallel
1. **Test harness** `plugins/goal/tests/run-tests.sh` (bash, no deps beyond jq):
   build a temp dir, write a fake transcript JSONL
   (`{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"..."}]}}`),
   pipe Stop-hook JSON into `hooks/stop-hook.sh`, assert on stdout/state file.
   Cover every row of the decision table above + corrupt state + session binding
   + `goal.sh` arg parsing (quotes, colons and `"` inside `--verify`, repeated `--criteria`,
   bad `--max-iterations`). Write tests against the contract, not the implementation.
2. **Portability review**: macOS bash 3.2 + BSD sed/date compatibility of all scripts
   (no `sed -i`, no `${var,,}`, no associative arrays, no GNU-only flags). Report or fix.
3. **CI**: `.github/workflows/goal-plugin-tests.yml` running `run-tests.sh` + `shellcheck`
   on `plugins/goal/**` for PRs touching that path.
4. **README.md**: a minimal one exists — expand it (examples, writing good criteria,
   comparison with ralph-wiggum).

Branch: `claude/busy-mendel-ns2o90`. Pull before pushing; don't edit core files
without noting it here — open findings as comments in the PR instead.
