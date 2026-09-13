# Protocol Integrations — Invariants

Consult when a hand-off crosses protocols (FIND→REQ promotion, COMP fields
flowing into LOOP ideation, core artifacts feeding a COMP). Who produces and
consumes what: each protocol file owns its own rules; this map only prevents
orphaned hand-offs. Field-level detail lives in the owning file.

## Autoresearch → Core SpecFlow (promotion)

Research output is not a dead end — deployable results carry traceability back
into core artifacts:

| Produces | Consumes | How |
|----------|----------|-----|
| `FIND` (`deployability: deployable`, `confidence` ≥ medium) | `/specflow-discover` → new **REQ** | REQ linked `derives_from` the FIND; `what_worked` + parent LOOP's `best_metric` copied into rationale/AC |
| Winning `EXPT` (post-check pass) | ops **RUN** (if the ops pack is installed) | RUN `derives_from` the EXPT (and the generalizing FIND) |
| Confirmed but exploratory FIND | next LOOP's `knowledge_input` | No promotion; accumulated knowledge |

This promotion is the research-side mirror of the Permanence Test — see SKILL.md
§ "Promote Research Output" for the recipe.

## Core SpecFlow → Autoresearch

REQ content informs COMP `goals`/`success_criteria`/`constraints` (discover);
ARCH/DDD shape the verify pipeline and experiment infrastructure (plan);
engineering prep (data download, env setup) goes through core execute/plan, never
inside a LOOP iteration; CI/hooks from adapter validate EXPT artifacts.

## Internal field flow (owner in parentheses)

- **COMP → LOOP** (autonomous-loop-protocol.md): `goals`/`theses`/`constraints` → hypothesis framing; `pre_check_command`/`post_check_command` → per-iteration guards and deploy-fit grading; `noise_characterization` → noise strategy (noise-handling-protocol.md); `domain` → EDA deltas, checklist, methodology lens; `custom_categories` → the active category set.
- **LOOP → EXPT** (autonomous-loop-protocol.md): `active_research_questions` → hypothesis linkage; `budget` → termination + surprise allocation.
- **EXPT → FIND** (finding-generation-protocol.md): `metric_value`/`change_category` → grouping; `hypothesis`+`hypothesis_outcome`, `failure_analysis`, `design_quality`, `auxiliary_metrics`, `crash_telemetry` → `what_worked`/`what_failed` authoring and confidence calibration.
- **FIND → LOOP** (autonomous-loop-protocol.md): `what_worked`/`what_failed`/`next_steps` → ideation; `confidence` → synthesis triggers; `deployability` → post-check weighting.
- **LOOP → next LOOP** (autonomous-loop-protocol.md): `lessons_learned`, `looplevel_findings`, condensation briefs, `termination_suggestions`, `best_metric` baseline, `eda_summary` skip rule, `research_agenda` inheritance + re-rank.

## Skill-to-protocol routing

| Skill step | Primary reference |
|------------|-------------------|
| Setup (no COMP) | `competition-setup-protocol.md` |
| Plan LOOP | `autonomous-loop-protocol.md` (+ `crash-recovery-protocol.md`) |
| Run LOOP | `autonomous-loop-protocol.md` (+ `explore-exploit-protocol.md`, `noise-handling-protocol.md`) |
| Review / delegate-review | `finding-generation-protocol.md` |
