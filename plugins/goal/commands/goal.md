---
description: "Set, check, pause, resume, or clear a verified goal that Claude works on until done"
argument-hint: "<objective> [--criteria TEXT]... [--verify CMD] [--max-iterations N] | status | pause | resume | clear | help"
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/goal.sh:*)", "Read(.claude/goal.local.md)", "Edit(.claude/goal.local.md)"]
hide-from-slash-command-tool: "true"
---

# /goal

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/goal.sh" $ARGUMENTS
```

Act on the output above:

- **If it does NOT start with "🎯 GOAL SET"** (status, pause, resume, clear, help, or an error): relay it to the user concisely and stop. If it says the goal was resumed, continue working on it per the protocol below.

- **If it starts with "🎯 GOAL SET"**, you are now working on a goal. The goal lives in `.claude/goal.local.md`; you own the body of that file (never edit its `---` frontmatter).

  1. **Sharpen the criteria first.** If the Success criteria section still has the placeholder line, replace it with 3–7 concrete, independently verifiable criteria (a command that passes, a behavior you can demonstrate, a file that exists). If criteria were given, keep them; add missing obvious ones (e.g. "existing tests still pass") only if clearly implied.
  2. **Plan briefly**, then work. Make real, incremental progress each turn.
  3. **Track progress honestly.** Tick a criterion `[x]` only after you have verified it, and append a one-line entry with the evidence to the Progress log.
  4. **Before claiming completion**, use the `goal-verifier` agent (if available) to independently check the work against every criterion, and fix what it finds.
  5. **Finish** by outputting `<goal-complete>`. A Stop hook will reject the claim if any criterion is unticked or the verify command fails, and you'll keep going.
  6. **If genuinely blocked** on something only the user can provide, output `<goal-blocked>short reason</goal-blocked>` to pause the goal.

  CRITICAL: Never tick a criterion or output `<goal-complete>` unless it is genuinely true. Being stuck or having run for a long time is not a reason to claim completion — use `<goal-blocked>` instead.
