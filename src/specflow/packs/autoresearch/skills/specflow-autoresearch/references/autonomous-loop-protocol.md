# Autonomous Loop Protocol — Invariants

One iteration = ideate → modify → commit → verify → decide → log. The CLI prints
this protocol (`specflow autoresearch run`); every rule below is a hard invariant,
not a suggestion. `specflow autoresearch status` is the deterministic preflight —
exit 0 clear · 3 warns (proceed with caution) · anything else is a failure: stop
and fix it before iterating. Deeper context lives in the sibling references named
in "Consult when".

## Hard invariants

1. **Bounded budget.** A LOOP never runs without `budget`; when `iteration_count >= budget` the loop ends. No unbounded mode exists.
2. **One running LOOP per COMP.** Two LOOPs race on Phase 4 commits and destroy reconstructable history. If a LOOP is already `running`: attach, abort-then-restart, or open a separate COMP.
3. **One atomic EXPT per iteration.** The change must be describable in one sentence; if it needs "and", it is two EXPTs. Attribute every metric delta to exactly one change.
4. **Commit before verify.** Stage explicit paths, commit `experiment(<scope>): <what and why>`, then run `verify_command`. Nothing is kept unless verify exits 0 with a measurable number.
5. **Never `git add -A` (or `git add .`).** Stage explicit file paths only — `-A` stages secrets and the user's unrelated work. Never bypass a blocking hook with `--no-verify`; fix what the hook reports.
6. **Rollback prefers `git revert`.** Revert preserves the failed experiment in history (it is the loop's memory); `git reset --hard HEAD~1` only on revert conflict. Discarded and crashed EXPTs are reverted, kept ones stay.
7. **Verify stdout is one number.** Non-numeric output ⇒ `status: crashed` + revert; two consecutive extraction failures mean the verify command is broken — stop. Rich diagnostics go to disk for review, never stdout.
8. **Persist condensation briefs on the LOOP** every 10 iterations (`condensation_brief_10`, `_20`, …; ~20 lines: iteration range, kept/discarded/crashed counts, best metric + EXPT, categories that drove improvement, dead ends). Working memory is volatile; the LOOP artifact is the digest the next LOOP's review reads.
9. **A hypothesis precedes every EXPT**: one line with predicted effect and reason, tied to an `active_research_question`; log it as `hypothesis`. After verify, log `hypothesis_outcome` (`supported` / `not_supported` / `inconclusive`) regardless of keep/discard — FINDs synthesize outcomes, not metrics.
10. **Stop on goals-met or budget — nothing else.** Goals met AND post-checks healthy (≥80% pass) ⇒ `completed` early. Budget exhausted ⇒ `completed`. Plateau with goals unmet ⇒ surface the suggestion; the user decides. Loop autonomously — no per-iteration confirmations; a one-line status every ~5 iterations and a final summary suffice.
11. **Loop state lives on the LOOP artifact** (totals, best metric, agenda, coverage, stuck state). Never write `.specflow/` internals; `specflow autoresearch log` is the atomic EXPT + counters update.

## The eight phases, one line each

| Phase | Rule |
|-------|------|
| 0 Precondition | `specflow autoresearch status` green (invariant above). COMP exists, LOOP `draft`, confirmed FINDs loaded into `knowledge_input`. |
| 0.5–0.7 Prepare | COMP `pre_check_command` guards inputs per iteration. EDA once before the first iteration (ML-01; fatal data problems stop the loop; record `eda_completed` + `eda_summary`; skip only if a prior LOOP ran it on unchanged data). Record a ranked `research_agenda` on the LOOP — ≥5 directions across ≥3 `change_category` values, param tuning never top-2, ~10% surprise budget for long shots — plus `category_coverage`. Load the matching `domain-research-checklists.md` section. Quick tier (budget ≤ 5): EDA checks #1/#4 only and a 2-direction agenda, announcing quick mode. |
| 1 Review | Read confirmed FINDs, this LOOP's EXPTs, `git log`. Not the first LOOP? Also read prior `lessons_learned`, condensation briefs, and `termination_suggestions`. |
| 2 Ideate | Hypothesis first (invariant 9). Gates: **highest-impact forcing** ("the highest-impact thing is X, I am about to do Y" — justify any gap, note agenda disagreements), **category diversity** (3 consecutive same-category EXPTs blocked; 2 in explore mode; unexplored categories before piling onto explored ones), **premise + idea-diversity check** (data property, prior art incl. prior LOOPs, metric-gaming, same-approach repetition). No blind parameter sweeps — sweep locally, log one EXPT with `sweep_results`. Consult `methodology-handbook.md` for the lens matching the change and `explore-exploit-protocol.md` for mode behavior. Use the canonical `change_category` set (or `COMP.custom_categories`); never invent mid-loop aliases. |
| 3 Modify | One atomic change (invariant 3); multi-file is fine when it serves one purpose. |
| 4 Commit | Invariants 4–5. Nothing staged ⇒ log `no_op`, skip verify, next iteration. |
| 5 Verify | Invariant 7. Pre-check failure ⇒ `discarded` + `failure_stage: pre_check` without verify. Volatile metric ⇒ pick a strategy from `noise-handling-protocol.md`. COMP `guard_command` ⇒ run after verify; on failure rework the implementation (max 2 attempts), never the tests. Timeout at 2× normal ⇒ crash. |
| 6 Decide | `kept` / `discarded` / `crashed` / `no_op`, mechanically from metric + guard. Log `hypothesis_outcome` (invariant 9), `failure_analysis` on non-keeps, update the agenda direction's `status` (3+ failures ⇒ `exhausted`; improvements ⇒ `promising`). COMP `post_check_command` grades deploy-fit severity (minor / moderate / severe); severe ⇒ `deployability: not_deployable`. |
| 7 Log | `specflow autoresearch log --loop LOOP-NNN …` creates the EXPT and updates LOOP counters atomically. Title by what changed; position in `iteration`. `parameters` / `model_origin` mandatory for `model`/`params` categories; auxiliary metrics for the domain. |
| 8 Repeat / Complete | Invariants 8 and 10. Stuck (>5 consecutive discards): switch category (mandatory), re-read code, FINDs, and agenda; log `stuck_state`; at 10 recommend stopping. Then FIND authoring per `finding-generation-protocol.md` — including the LOOP post-mortem fields (`lessons_learned`, `looplevel_findings`). |

## Consult when

- Verify fails or a session died mid-iteration → `crash-recovery-protocol.md` (capture `crash_telemetry` before reverting; three recovery rules).
- Choosing or suggesting a LOOP mode → `explore-exploit-protocol.md`.
- Creating or closing a COMP → `competition-setup-protocol.md`.
- Authoring FINDs after the loop → `finding-generation-protocol.md`.
- Domain methodology during Phase 2 → `methodology-handbook.md`; ideation breadth at Phase 0.7 → `domain-research-checklists.md`.
- Split design, window advance, COMP churn rule → `rolling-evaluation.md`.
- Who produces/consumes which field → `protocol-integrations.md`.
