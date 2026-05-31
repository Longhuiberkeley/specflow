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

### Pre-Recovery Telemetry Extraction

**Before reverting or discarding anything**, extract what can be learned from the partial state. A crash is not just a failure — it's a signal about the system's boundaries.

1. **Identify what ran successfully.** Which steps completed before the crash? Read partial output files, log fragments, and git status. The last successful step is a lower bound on what works.

2. **Capture the crash signature.** What was the exact error? OOM at what data size? Timeout at what iteration count? This is telemetry for future LOOPs: "verify command fails with OOM above 500K rows" or "training loop hangs at epoch 47."

3. **Log partial results.** If the EXPT produced any output before crashing (partial metrics, intermediate checkpoints, half-written results), save them. A Sharpe of 0.5 after 200/500 epochs is not a final result, but it IS a signal — the approach may have been directionally correct but hit a resource wall.

4. **Record `crash_telemetry` on the EXPT (if one was started):**
   ```bash
   specflow create --type experiment \
     --title "[CRASHED] <original title>" \
     --status crashed \
     --set crash_telemetry="Last step: Phase 5 verify. Error: OOM at 500K rows. Partial metric: 0.5 after 200/500 epochs. git hash: abc1234."
   ```
   This telemetry is read by Phase 6.6 for lesson extraction — even crashed EXPTs produce knowledge.

5. **Only THEN apply recovery.** After telemetry is captured, proceed with the recovery rules below. The telemetry extraction should take <1 minute — don't deep-dive, just capture what's immediately visible.

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
