# Crash Recovery — Invariants

Consult during Phase 0 (detecting prior-session crash state) and Phase 5 (verify
command failures). Routine keep/discard decisions stay in
`autonomous-loop-protocol.md`.

## Within an iteration (verify failures)

| Failure | Action |
|---------|--------|
| Syntax error | Fix immediately; not a separate iteration |
| Runtime error | Attempt fix (max 3), then move on |
| OOM / resource exhaustion | Revert, try a smaller variant |
| Hang | Kill at timeout, revert, avoid that approach |
| External dependency failure | Skip, log, different approach |

## Session crash (agent died mid-iteration)

**Telemetry before recovery.** Before reverting anything, capture what the partial state teaches: last successful step, the crash signature (error, data size, iteration), any partial results, and `crash_telemetry` on a `crashed` EXPT if one was started. Keep it under a minute — capture, don't deep-dive. Even crashed EXPTs produce knowledge.

Then apply exactly one recovery rule:

| State found | Meaning | Recovery |
|------------|---------|----------|
| Dirty working tree | Crashed during Modify, never verified | `git checkout -- <in-scope files>`; resume at Phase 1 |
| Last commit `experiment(…)` with no matching EXPT | Crashed after Commit, before Log | `safe_revert()` (revert, else `git reset --hard HEAD~1`); resume at Phase 1 |
| Clean tree + last commit has its EXPT | Crashed after Log | Nothing to recover; resume normally |

## Stuck (>5 consecutive discards)

Category switch is mandatory (see the stuck rule in `autonomous-loop-protocol.md`
Phase 8): re-read the code, FINDs, and agenda; try the opposite or a radical
change. At 10 discards: `specflow update LOOP-NNN --status plateaued`, author
FINDs from what was learned, and ask the user to extend with a different mode or
rework the COMP.
