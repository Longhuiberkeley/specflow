# Protocol Integrations

Maps every producer-consumer relationship across SpecFlow's autoresearch protocols and core specflow skills. When a protocol says "read X" or "feeds into Y," this file says where X comes from and where Y goes.

## Core SpecFlow → Autoresearch

| Core produces | Autoresearch consumes | When | How |
|---------------|----------------------|------|-----|
| `specflow-discover` (REQ artifacts) | COMP setup (`competition-setup-protocol.md`) | During competition creation | User's requirements inform COMP `goals`, `success_criteria`, and `constraints` |
| `specflow-execute` (implementation) | COMP pre-work (data prep, env setup) | Before first LOOP | Engineering prep (download data, set up verify script, configure environment) goes through core SpecFlow, NOT LOOP |
| `specflow-plan` (ARCH/DDD artifacts) | COMP infrastructure design | During competition setup | Architecture for the verify pipeline, data storage, and experiment infrastructure |
| `specflow-adapter` (CI, hooks) | LOOP execution environment | Before first LOOP | Pre-commit hooks, CI validation of EXPT artifacts |

## Autoresearch Internal

### COMP → LOOP

| COMP field | LOOP consumes | Protocol |
|------------|---------------|----------|
| `COMP.goals` | Phase 2a (hypothesis formulation), Phase 2b (metric-goal alignment check) | `autonomous-loop-protocol.md` |
| `COMP.theses` | Phase 2a (RQ-thesis-goal chain) | `autonomous-loop-protocol.md` |
| `COMP.constraints` | Phase 2a (guard conditions) | `autonomous-loop-protocol.md` |
| `COMP.pre_check_command` | Phase 0.5 (per-iteration pre-check) | `autonomous-loop-protocol.md` |
| `COMP.post_check_command` | Phase 6.5 (post-check after verify) | `autonomous-loop-protocol.md` |
| `COMP.noise_characterization` | Phase 5 (noise strategy selection) | `noise-handling-protocol.md` |
| `COMP.domain` | Phase 0.6 (domain-specific EDA checks), Phase 2 (methodology BP selection) | `autonomous-loop-protocol.md`, `methodology-handbook.md` |

### LOOP → LOOP (cross-loop learning)

| Prior LOOP produces | Next LOOP consumes | Protocol |
|---------------------|-------------------|----------|
| `LOOP.lessons_learned` | Step 0b (prior-LOOP review) | `autonomous-loop-protocol.md` |
| `LOOP.looplevel_findings` | Step 0b, Phase 2c (pick next change) | `autonomous-loop-protocol.md` |
| `LOOP.condensation_brief_10/20/...` | Step 0b (read trajectory midpoints) | `autonomous-loop-protocol.md` |
| `LOOP.termination_suggestions` | Step 0b, Phase 2a (next LOOP's direction) | `autonomous-loop-protocol.md` |
| `LOOP.best_metric` | New LOOP baseline | `autonomous-loop-protocol.md` |
| `LOOP.eda_summary` | Phase 0.6 skip rule | `autonomous-loop-protocol.md` |

### LOOP → EXPT

| LOOP field | EXPT consumes | Protocol |
|------------|---------------|----------|
| `LOOP.active_research_questions` | Phase 2a (hypothesis-RQ linkage) | `autonomous-loop-protocol.md` |
| `LOOP.budget` | Phase 1 Step 4 (budget check) | `autonomous-loop-protocol.md` |
| `LOOP.iteration_count` | Phase 7 (update running totals) | `autonomous-loop-protocol.md` |

### EXPT → FIND

| EXPT field | FIND consumes | Protocol |
|------------|---------------|----------|
| `EXPT.metric_value` | Aggregation (best, delta, trends) | `finding-generation-protocol.md` |
| `EXPT.change_category` | Grouping, per-category analysis | `finding-generation-protocol.md` |
| `EXPT.hypothesis` + `hypothesis_outcome` | `what_worked` / `what_failed` authoring | `finding-generation-protocol.md` |
| `EXPT.failure_analysis` | `what_failed` root cause classification | `finding-generation-protocol.md` |
| `EXPT.design_quality` | Confidence calibration, evidence weighting | `finding-generation-protocol.md`, Phase 6.6 |
| `EXPT.lesson_extracted` | Cross-EXPT pattern detection | `finding-generation-protocol.md` |
| `EXPT.auxiliary_metrics` | Auxiliary Metric Synthesis | `finding-generation-protocol.md` |
| `EXPT.auxiliary_signal` | Buried signal detection | `finding-generation-protocol.md` |
| `EXPT.crash_telemetry` | Pre-recovery knowledge extraction | `crash-recovery-protocol.md`, Phase 6.6 |
| `EXPT.parameters` + `EXPT.sweep_results` | Reproducibility, parameter sensitivity analysis | `finding-generation-protocol.md` |
| `EXPT.diversity_metrics` | Family grouping, leaderboard ranking | `competition-setup-protocol.md` |

### FIND → LOOP (feedback cycle)

| FIND field | Next LOOP consumes | Protocol |
|------------|-------------------|----------|
| `FIND.what_worked` | Phase 2c (exploit successes) | `autonomous-loop-protocol.md` |
| `FIND.what_failed` | Phase 2c (avoid repeats), Phase 2a (don't re-test falsified theses) | `autonomous-loop-protocol.md` |
| `FIND.next_steps` | Step 0b, Phase 2c (direction guidance) | `autonomous-loop-protocol.md` |
| `FIND.confidence` | Cross-loop synthesis triggers | `finding-generation-protocol.md` |
| `FIND.deployability` | Phase 6.5 post-check weighting | `autonomous-loop-protocol.md` |
| `FIND.safety_assessment` | Safety-critical domain gates | `finding-generation-protocol.md` |

## Protocol-Specific Dependencies

### Finding Generation Protocol

| Section | Depends on | Protocol file |
|---------|-----------|---------------|
| Cross-EXPT Pattern Detection | Phase 6.6 (design_quality scores, lesson_extracted) | `autonomous-loop-protocol.md` |
| Auxiliary Metric Synthesis | Phase 7 (auxiliary_metrics logging) | `autonomous-loop-protocol.md` |
| Cross-Loop Synthesis | Prior FINDs, LOOP post-mortem data | `finding-generation-protocol.md`, `autonomous-loop-protocol.md` |
| Mandatory Cross-Loop Triggers | LOOP count, FIND age, cumulative EXPT count | `autonomous-loop-protocol.md` |

### Noise Handling Protocol

| Section | Depends on | Protocol file |
|---------|-----------|---------------|
| EXPT Validity Gate | Phase 6.6 (design_quality scoring) | `autonomous-loop-protocol.md` |
| Noise Strategy Selection | COMP.noise_characterization | `competition-setup-protocol.md` |

### Crash Recovery Protocol

| Section | Depends on | Protocol file |
|---------|-----------|---------------|
| Pre-Recovery Telemetry | Phase 6.6 (crash_telemetry field) | `autonomous-loop-protocol.md` |
| Session Crash Recovery | Phase 0 precondition checks | `autonomous-loop-protocol.md` |

### Methodology Handbook

| BP | Enforced by | Protocol file |
|----|------------|---------------|
| BP-01 (EDA Before Modeling) | Phase 0.6 (mandatory) | `autonomous-loop-protocol.md` |
| BP-02..BP-09 (advisory) | Phase 2 (consulted during ideation) | `autonomous-loop-protocol.md` |
| BP-08 (Characterize Noise) | COMP setup noise probe, Phase 5 noise strategy | `noise-handling-protocol.md`, `competition-setup-protocol.md` |

## Skill-to-Protocol Mapping

| Skill step | Primary protocol reference | Supporting references |
|------------|---------------------------|----------------------|
| `/specflow-autoresearch` Step 0 (setup) | `competition-setup-protocol.md` | `methodology-handbook.md` |
| `/specflow-autoresearch` Step 1 (plan LOOP) | `autonomous-loop-protocol.md` (Phase 0, 0.5, 0.6, Step 0b) | `crash-recovery-protocol.md` |
| `/specflow-autoresearch` Step 2 (run LOOP) | `autonomous-loop-protocol.md` (Phase 1-8) | `explore-exploit-protocol.md`, `noise-handling-protocol.md` |
| `/specflow-autoresearch` Step 3 (review) | `finding-generation-protocol.md` | `autonomous-loop-protocol.md` (FIND Authoring, LOOP post-mortem) |
| `/specflow-autoresearch:delegate-review` | `finding-generation-protocol.md` | (subagent pattern) |

## Cross-Cutting Concerns

| Concern | Protocol files involved | Integration point |
|---------|------------------------|-------------------|
| Knowledge preservation across LOOPs | `autonomous-loop-protocol.md` (Step 0b, LOOP post-mortem, Phase 8 condensation), `finding-generation-protocol.md` (cross-loop synthesis) | Step 0b reads LOOP post-mortem + condensation briefs; cross-loop synthesis reads FINDs across LOOPs |
| Data quality assurance | `autonomous-loop-protocol.md` (Phase 0.6 EDA, Phase 0.5 pre-check, Phase 2d premise check), `noise-handling-protocol.md` (validity gate) | Phase 0.6 runs once at loop start; Phase 0.5 runs per-iteration; Phase 2d per-EXPT checks should consult Phase 0.6 results (e.g., stationarity check in 2d is answered by 0.6); noise validity gate runs per-EXPT |
| Metric integrity | `autonomous-loop-protocol.md` (Phase 2b, Phase 5, Phase 6.5), `noise-handling-protocol.md` | Phase 2b checks metric-goal alignment; Phase 5 handles noise; Phase 6.5 grades post-check severity |
| Failure learning | `autonomous-loop-protocol.md` (Phase 6.6, Phase 7 failure_analysis), `crash-recovery-protocol.md` (pre-recovery telemetry), `finding-generation-protocol.md` (what_failed authoring) | Phase 6.6 extracts lessons; crash telemetry captures partial results; FIND authoring synthesizes into what_failed |
