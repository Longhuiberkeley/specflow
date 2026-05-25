# Crash Recovery Protocol

When to read: during Phase 0 precondition checks (to detect prior-session crash state) and during Phase 5 verify (when the verify command itself fails). For routine kept/discard decisions, stay in `autonomous-loop-protocol.md`.

## Within an Iteration (verify command failures)

| Failure | Action |
|---------|--------|
| Syntax error | Fix immediately, don't count as separate iteration |
| Runtime error | Attempt fix (max 3 tries), then move on |
| Resource exhaustion (OOM) | Revert, try smaller variant |
| Infinite loop / hang | Kill after timeout, revert, avoid that approach |
| External dependency failure | Skip, log, try different approach |

## Session Crash (agent itself dies mid-iteration)

If the agent crashes, the working tree may be in a partially modified state. On the next invocation, Phase 0 precondition checks must detect this and recover before re-entering the loop.

**Recovery rules:**

```
IF working tree is dirty (changes not yet committed):
    # Agent crashed during Phase 3 (modify) — before commit
    # These changes were never verified. Discard them.
    git checkout -- <in-scope files>
    Resume loop from Phase 1

IF last commit is "experiment(...)" with no matching EXPT artifact:
    # Agent crashed after Phase 4 (commit) but before Phase 7 (log)
    # The experiment was never recorded. Revert it.
    safe_revert()
    Resume loop from Phase 1

IF working tree is clean AND last commit has a matching EXPT artifact:
    # Agent crashed after Phase 7 (log) — clean state
    # Nothing to recover. Resume normally.
    Resume loop from Phase 1
```

`safe_revert()` is defined in Phase 6 of the main protocol — it prefers `git revert` (preserves history) and falls back to `git reset --hard HEAD~1` only on conflict.

## When Stuck (>5 consecutive discards)

Not a crash, but a meta-failure mode worth recovering from:

1. Re-read ALL in-scope files from scratch
2. Re-read the competition's FINDs and the original goal
3. Review entire EXPT history for patterns
4. Try combining 2-3 previously successful changes
5. Try the OPPOSITE of what hasn't been working
6. Try a radical architectural change

If still stuck after 10 discards: stop the loop (`specflow update LOOP-NNN --status plateaued`), author FINDs from what was learned, and ask the user to either extend budget with a different mode or rework the COMP.
