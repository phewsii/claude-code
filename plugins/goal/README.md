# goal

Give Claude a goal, and it keeps working until the goal is **verifiably** done.

```bash
/goal Add rate limiting to the public API --verify "npm test" --max-iterations 30
```

- **Runs until done.** A Stop hook keeps the session going and feeds the remaining work back to Claude each round.
- **Tracks progress.** The goal, its success-criteria checklist and a progress log live in `.claude/goal.local.md`, so they survive restarts and compaction.
- **Verifies completion.** When Claude says `<goal-complete>`, the hook checks that every criterion is ticked and that `--verify` exits 0. If either check fails, Claude has to keep working.
- **Stays on track.** Each prompt gets a short reminder of the goal, and the full goal is re-added after resume or compaction.
- **Honest exit.** If Claude is stuck on something only you can fix, it says `<goal-blocked>reason</goal-blocked>` and the goal pauses. Claude never has to lie to stop.

## Commands

| | |
|---|---|
| `/goal <objective> [--criteria TEXT]... [--verify CMD] [--max-iterations N] [--force]` | Start a goal (default cap: 20 rounds, `0` = unlimited) |
| `/goal` / `/goal status` | Show the goal, progress and iteration count |
| `/goal pause` · `/goal resume` | Pause, or resume (also resets the iteration count) |
| `/goal clear` | Delete the goal |

Without `--criteria`, Claude writes 3–7 verifiable criteria before it starts. Finished goals are archived to `.claude/goals/`. A goal belongs to the session that first works on it, so other sessions in the same repo aren't pulled into it.

## vs. ralph-wiggum

Ralph sends the same prompt back every round and stops on a string match. `/goal` keeps a structured checklist that changes as work happens, and only accepts completion after the checks pass.

See [SPEC.md](./SPEC.md) for the state-file contract and the Stop hook's decision table.

Requires `jq` and `perl`.
