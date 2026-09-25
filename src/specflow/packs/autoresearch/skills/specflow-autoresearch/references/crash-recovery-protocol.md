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

## Evidence-free streaks — reassess, don't switch by count

REQ-043: there is no mandatory category switch and no count-based stop. When a
line stops producing new evidence (its last three attempts carry no anchored,
distinct `research_progress` and no measured improvement), reassess: re-read the
code, FINDs, and agenda; record what the streak taught (`research_progress` /
`failure_analysis` / `hypothesis_outcome` — negative memory the next LOOP can
read); then choose the next formulation or set the direction's `priority`
(`deprioritize` / `revisit`). Picking B does not require proving A impossible.
Counts never close a direction; budget still bounds the LOOP. If the budget
ends without progress, propose `plateaued` and let the user decide the next
move (extend with a different mode, rework the COMP, or park the direction).
Crashed runs may be `invalid` instruments: record the teardown as
`failure_analysis`, not as evidence against the hypothesis.
