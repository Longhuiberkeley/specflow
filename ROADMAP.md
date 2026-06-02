# SpecFlow Roadmap

SpecFlow ships incrementally. This document tracks what shipped in each release, what's next, and the longer-term direction.

For the implementation plan (phase breakdown, dependency graph), see [docs/plan.md](docs/plan.md).

## v0.2.0

**First tagged release.** Full AI lifecycle with discovery, traceability, execution, review, and compliance.

### Slash Commands (10)

| Command | Purpose |
|---------|---------|
| `/specflow-init` | Bootstrap project, install skills, optional CI |
| `/specflow-discover` | Capture requirements through guided conversation |
| `/specflow-plan` | Break approved REQs into architecture + stories |
| `/specflow-execute` | Implement stories with test generation |
| `/specflow-artifact-review` | Quality review of specific artifacts |
| `/specflow-change-impact-review` | Blast-radius review of recent changes |
| `/specflow-audit` | Full-project periodic health check |
| `/specflow-ship` | Release: baseline + change records + audit |
| `/specflow-pack-author` | Author a standards compliance pack |
| `/specflow-adapter` | Manage CI, exchange, standards ingestion, team RBAC |

### What's Included

**Core Framework**
- Zero-token validation engine: schema, links, status, IDs, fingerprints, acceptance, conflicts, coverage, chain depth, quality
- Requirements quality scoring with INCOSE/EARS-based checks for ambiguity, passive voice, missing measurability, and compound requirements
- 14 AI coding platform support (Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, GitHub Copilot, Roo Code, QwenCoder, Kiro, KiloCoder, Codex, Trae, Junie)

**Traceability & Compliance**
- V-model traceability: REQ → ARCH → DDD → UT/IT/QT
- Impact analysis with suspect flags and fingerprint tracking
- Enhanced trace command with chain depth reporting and coverage dashboards
- Immutable baselines with diff comparison
- Standards pack architecture with gap analysis
- ReqIF 1.2 import/export for supply-chain interchange
- Coverage metrics (REQ coverage, story test coverage, chain completeness)

**Team & Enterprise**
- Git-based RBAC with pre-commit hooks and CI gate
- Defect lifecycle with prevention pattern extraction
- Draft ID renumbering with cross-repo reference rewriting
- CI workflow generation (GitHub Actions)

**Intelligence & Scaling**
- 3-tier deduplication (tag Jaccard, TF-IDF, LLM)
- Dead-code and similarity detection
- Adversarial review techniques (devil's advocate, premortem, assumption surfacing, red/blue team)
- V-model test stub generation (`specflow generate-tests`)
- Split and merge artifact operations

**Engineering**
- 30 CLI subcommands across discover, plan, execute, review, release, CI, and recovery phases
- 20+ skill reference documents for progressive disclosure
- Deterministic shell wrappers for CI/CD integration
- Artifact quality lint with regex-based checks

## v1.0.0

Focus: **polish, stability, and adoptability.** Ship what we have with confidence.

- **Shared thinking techniques** — adversarial lenses extracted to a shared reference catalog, woven into discover and plan skills so requirements and architecture are challenged at creation time, not just at review time
- **Freeform skill input** — all skills accept natural language context (e.g., `/specflow-audit I'm worried about REQ coverage`) for scoped, directed workflows
- **Compliance summary in status** — `specflow status` shows per-pack compliance scores when standards are installed
- **Polished onboarding** — README rewrite with clearer visual hierarchy and disambiguation from similarly-named projects
- **Release process** — structured CHANGELOG, git tagging, and GitHub Release workflow documented in AGENTS.md
- **Test coverage boost** — expanded coverage on critical CLI paths (create, update, status, lint, audit)
- **Error message polish** — actionable CLI error messages across all commands

## v1.0.1

- AGENTS.md template fix (missing `/specflow-adapter`, V-model docs, CLI-only references)
- `/specflow-init` completion message suggests `/specflow-adapter` for CI-first teams
- ROADMAP cleanup (duplicate Jira sync entry)

## v1.1.0

Focus: **domain intelligence and learning feedback.**

- **Domain best-practice synthesis** — project-level and phase-level BP generation via LLM, cached as human-editable YAML
- **Knowledge accumulation lifecycle** — learned prevention patterns (PREV-*.yaml) extracted from artifact reviews with blocking/warning findings
- **Per-item checklist scoping** — `applies_to.types` on individual checklist items overrides top-level filter
- **Configurable learning** — `learnable_techniques` and `max_patterns_per_session` in config.yaml
- **`specflow patterns`** — inspect learned prevention patterns (`list`, `show`)
- **`specflow handbook`** — manage domain BP cache (`generate`, `show`, `path`, `list`)
- **`--fast` flag** on `artifact-review` — skip BP synthesis for CI, use cached only
- **Auto-backup** — `--overwrite` backs up previous BP file before regenerating
- **`specflow done` auto-extraction** — `--auto` is now the default, extracts patterns from implemented stories
- **Expanded learnable techniques** — adversarial findings (devil's advocate, premortem, etc.) now feed into learning by default

## v1.2.0

Focus: **init upgrade safety, spec body quality enforcement, and output file traceability.**

## v1.4.1

Focus: **quality fixes from v1.3.0/v1.4.0 review — read-only impact reporting, recursive propagation, glob correctness, and code convergence.**

- **Read-only `change-impact`** — source-file impact section no longer silently flags artifacts; new `--flag` opt-in
- **Recursive downstream propagation** — suspect flags propagate transitively (ARCH → DDD → UT), not just one level
- **`**` recursive glob support** — `output_files` with `src/**/*.py` now correctly matches nested files
- **Converged CHL creation** — shared `specflow/lib/challenges.py` replaces duplicated logic in audit and review
- **Per-suspect resolution** — resolving one artifact no longer resolves the entire impact-log event
- **Spec and ROADMAP cleanup** — DDD-005, DDD-019 updated; shipped items removed from Future section

## v1.4.0

Focus: **compliance evidence quality and structured review artifacts.**

- **Compliance evidence quality lint** — new `compliance-evidence` check in `artifact-lint`; warns when an artifact's `complies_with` link is not backed by a substantive body (≥50 words) or fails to reference any keyword from the clause. Strict mode escalates to blocking errors via `lint.compliance_evidence_strict` config.
- **REVIEW artifact type** — new `REVIEW-NNN` schema with `reviewers`, `findings`, `consensus`, `depth`, `artifact_ref` fields; emitted by `/specflow-artifact-review` to summarize each review pass. Spawned CHLs link back via `refers_to`.
- **Status now shows reviews** — `specflow status` adds a `Reviews:` line counting REVIEW + AUD + CHL artifacts.
- **Auto-bootstrap on existing repos** — `artifact-review` copies `review.yaml` and creates `_specflow/specs/reviews/` on first invocation in repos that pre-date v1.4.0.

## v1.3.1

Focus: **verification gap closure and decision housekeeping.**

- **STORY-049..063 verified** — generated 17 UT/IT/QT artifacts (QT-023..028, IT-018..023, UT-023..027) closing the missing test pairs flagged by project-audit
- **REQ/ARCH/DDD chain coverage at 100%** — chain coverage rose from 75% to 100% (69/69); STORY test coverage rose from 76% to 100% (63/63)
- **All 42 DECs promoted** — long-tail draft decisions (DEC-001..042) advanced to `approved`
- **REQ-022..027 promoted** from `approved` to `implemented` to enable test stub generation

## v1.3.0

Focus: **reverse impact analysis, decomposition completeness guidance, and discovery-to-plan skill continuity.**

- **Reverse impact analysis** — source code changes map back to spec artifacts via `output_files`, closing the bidirectional traceability loop
- **SPIDR dimension coverage** — `artifact-lint` reports when decomposition dimensions have no stories
- **Story dependency cycle detection** — `artifact-lint` detects circular dependencies between stories during planning
- **DDD selection decision tree** — reference document with 6-question checklist for DDD artifact necessity
- **Generic best-practice fallback** — bundled generic BP templates for offline handbook generation (no API key required)
- **Discovery challenge persistence** — thinking technique results persisted as DEC artifacts for plan skill consumption
- **Inter-REQ dependency prompting** — discover skill captures requirement dependencies as `derives_from` links
- **Domain context pass-through** — plan skill reads domain classification from config and decisions from discovery
- **Improved discover-to-plan handoff** — explicit approval instructions and next-step commands in exit message

## v1.6.0

Focus: **autoresearch pack v0.2.0 — harness-agnostic research loops with multi-criteria competitions.**

- **Autoresearch CLI subcommand** — `specflow autoresearch plan|run|review|leaderboard` lets any LLM harness drive autonomous research loops without platform-specific skills; auto-detects active competition and supports `--all` cross-COMP leaderboards
- **Multi-criteria competitions** — primary metric for ranking, binary guards for hard floors, freeform `auxiliary_metrics` on EXPT artifacts for post-hoc analysis (max_drawdown, total_trades, runtime_seconds, etc.); documented anti-leakage and anti-gaming patterns as recommendations
- **Pack context injection** — packs declare `context_snippet` in `pack.yaml`; `specflow init --preset <pack>` injects a sentinel-bracketed block into the platform's instruction file (`AGENTS.md`, `.cursor/rules/specflow.md`, etc.) so host agents learn pack vocabulary without per-platform skill variants
- **Thin skill wrapper** — `SKILL.md` references CLI backends for all subcommands; safety posture, anti-patterns, and principles preserved

## v1.5.0

Focus: **unified thinking technique tracking and technique-to-BP feedback loop.**

- **Unified 16-lens adversarial catalog** — all 16 thinking techniques available in every lifecycle phase via shared reference at `.claude/skills/specflow-references/`; per-phase default sets and trigger-for-expansion guidance
- **Thinking technique records on artifacts** — `thinking_techniques` optional field on all 13 artifact types; `specflow update <ID> --thinking-techniques` flag for recording; lint warns on unchallenged approved specs
- **Generic lens fallback** — the 12 lenses without Python modules now run as generic LLM prompts, making all 16 lenses runnable from the CLI
- **Technique-to-BP feedback loop** — BP staleness checks include CHL artifacts; synthesis prompts inject recent adversarial findings so BPs learn from what lenses caught
- **Audit technique granularity** — audit CHLs carry per-axis names (`audit-horizontal`, `audit-vertical`, `audit-cross-cutting`) instead of monolithic `project-audit`

## v1.6.1

Focus: **richer experiment logging, flexible objectives, domain-aware and goal-driven autoresearch.**

- **Generic `--set KEY=VALUE` on `create`/`update`** — repeatable, JSON-aware frontmatter writes flow into `create_artifact`/`update_artifact`. This is what makes the autoresearch protocols actually runnable from the CLI (EXPT/COMP/LOOP/FIND fields like `metric_value`, `verify_command`, `goals`, `failure_analysis` are no longer hardcoded flags)
- **Goal-driven hypothesis loop** — Phase 2 ideation now reads `COMP.goals`/`success_criteria` and states a falsifiable hypothesis per experiment; `hypothesis` and `hypothesis_outcome` (supported/not_supported/inconclusive) added to `experiment.yaml`. Findings record honest outcomes (falsified / conditional / sensitive / inconclusive) instead of forcing "falsified"
- **Intent drives checks** — pre/post-checks are derived from goals: pre-check guards inputs (EDA, leakage), post-check guards deploy-fit named in `success_criteria` (a good core metric ≠ a deployable candidate)
- **Structured EXPT logging** — `parameters` (hyperparameters), `model_origin` (`pretrained`/`trained_from_scratch`/`fine_tuned`), `sweep_results` (grid-search capture), `diversity_metrics` (swarm/ensemble tracking), and `failure_analysis` (root cause on discarded EXPTs) added to `experiment.yaml`
- **Pre/post experiment checks** — `pre_check_command` and `post_check_command` on COMP; `checks` array on EXPT records pre-check / verify / post-check pipeline results per iteration
- **Flexible competition objectives** — `objective_type` (`single_best`, `family_of_good`, `pareto_front`) and `goals` on COMP; `termination_suggestions` on LOOP for dynamic, goal-oriented stopping
- **Domain awareness** — `domain` field (`quant`, `ml`, `nlp`, `systems`, `safety_critical`) on COMP drives `artifact-lint` warnings when domain-recommended auxiliary metrics are missing
- **Noise characterization persistence** — `noise_characterization` on COMP stores variance-probe results so future LOOPs know the measurement floor without re-profiling
- **Deployability and safety** — `deployability` and `safety_assessment` fields on FIND for quant and safety-critical domains
- **FIND enforcement** — `specflow autoresearch review` warns when a completed LOOP has zero FINDs or when discarded EXPTs lack `failure_analysis`
- **Leaderboard grouping** — `specflow autoresearch leaderboard --group-by model_origin` and `--show-family` for swarm/ensemble views

## v1.6.2

Focus: **experimental thinking lenses, concise context, atomic CLI sugar, and subagent guidance for autoresearch.**

- **7 new research thinking lenses** — `leakage_audit`, `overfitting_multiple_comparisons`, `baseline_sanity`, `distribution_shift`, `ablation_attribution`, `metric_validity` (in per-level defaults), `reproducibility` (optional, not in defaults); added to `LENS_CATALOG` with `LENS_CATEGORIES` tagging (software/research/both)
- **Per-level default lens sets** — COMP, LOOP, EXPT, FIND each get research-appropriate defaults that `artifact-review --depth deep` auto-selects when reviewing research artifacts
- **Mixed-artifact review guard** — `artifact-review` detects when a review batch contains both software and research artifacts and falls back to `both`-category lenses only, preventing domain mismatch
- **Concise lens prompts** — ~800 tokens saved across the 23-lens catalog by extracting repeated JSON/boilerplate into a single `_GENERIC_LENS_SUFFIX` injected at runtime
- **Static ML methodology handbook** — curated 9-BP reference (`methodology-handbook.md`) with domain-keyed applicability (quant, tabular_ml, vision, nlp); advisory-only, referenced from setup and loop protocols
- **Atomic EXPT logging** — `specflow autoresearch log` creates an EXPT artifact and auto-updates LOOP counters (`iteration_count`, `kept_count`, `discarded_count`, `best_metric`) in one CLI call
- **Deterministic FIND drafting** — `specflow autoresearch suggest-finds` groups EXPTs by `change_category`, synthesizes `what_worked` / `what_failed` / `next_steps`, and either prints a draft or writes a FIND artifact with `--write`
- **Subagent guidance in SKILL.md** — explicit instructions for spawning parallel subagents per `change_category` during FIND synthesis, and per-strategy-family in `family_of_good` competitions, to keep context windows small
- **ML tracker coexistence** — documented integration pattern with MLflow, Weights & Biases, Neptune, MLRun, etc. via "Coexisting with External ML Trackers" section in `competition-setup-protocol.md`
- **Passive-CLI banner** — `autoresearch run` prints a reminder that the AI agent drives the loop, not the CLI

## v1.7.3

Focus: **autoresearch methodology depth, escalation/permanence test, and template freshness.**

- **Autoresearch methodology depth (BP-10–22)** — expanded `methodology-handbook.md` with four new groups: validation integrity (split-first, adversarial validation, out-of-fold), statistical traps (multiple-comparisons, dimensionality/curse-of-dimensionality, distribution shift, Simpson's paradox), optimize-the-objective (eval-metric/post-processing, calibration, multi-output decomposition), and finishing moves (diverse ensembling, seed averaging, pseudo-labeling), plus a bias catalog. Added a **Kaggle transfer filter** distinguishing tactics that generalize to deployment from leaderboard-gaming that increases overfitting. Wired into the loop's EDA checks (dimensionality + adversarial validation) and Phase-2 ideation so the BPs are consulted live, not left as a dead reference. Multi-output `[x,y,z]` targets get per-component `auxiliary_metrics` discipline and per-component finding synthesis; best-of-many findings are confidence-capped until confirmed (multiple-comparisons).
- **Escalation / Permanence Test** — added a "when to escalate" heuristic to the always-loaded base context (`agent-context.md` + injected instruction block) with situational trigger wording ("when work outgrows a one-off answer"). New `specflow-execute/references/escalation-and-promotion.md` recipe (SPIKE→spec, COMP→COMP) with `derives_from` lineage; cross-linked from execute and discover; COMP-evolution guidance added to the autoresearch skill.
- **Skill template freshness fix** — synced the shipping skill templates (`src/specflow/templates/skills/shared/`) from the live dogfood layer, resolving pre-existing drift across all 10 core skills (stale descriptions, missing `ddd-selection.md`, the relocated shared `specflow-references/adversarial-lenses.md`). New `specflow init`s now ship current skills/BPs/thinking-techniques rather than stale copies.

> Deferred: an audit/lint detector that flags long-lived SPIKEs / repeated ad-hoc work that should have been promoted (a work-side complement to the v1.8.0 *Stale Code Detection* item). Also deferred: optional structured multi-output schema (typed per-component fields on COMP/EXPT) if the `component_<name>` convention proves too loose.

## v1.8.0 (Planned)

Focus: **swarm observability, synthesis conflict resolution, semantic drift detection, and human steering.**

- **Cost and Token Observability** — add `--dry-run` to multi-agent skills (e.g., `/specflow-audit`, `/specflow-plan`) to estimate token cost before fan-out. Log token/cost telemetry to `.specflow/telemetry/` for post-hoc analysis.
- **Synthesis Conflict Resolution Rubric** — introduce a rigorous conflict-resolution rubric for synthesis agents (e.g., merging parallel ARCH candidates). Mandate `ask_user` prompts when parallel seeds fundamentally diverge on core constraints.
- **Stale Code Detection (Semantic Drift)** — add a lint check that flags `implemented` or `verified` code/artifacts as "stale" when their governing upstream REQ or ARCH is modified.
- **Human-in-the-Loop Readability** — evolve `specflow autoresearch review` into a robust CLI dashboard, ensuring LOOP logs, FINDs, and EXPT rubrics remain human-readable when humans need to step in and steer the AI swarm.
- **Proactive Dogfooding Enforcement** — enforce that SpecFlow development proactive uses `/specflow-plan` and `/specflow-execute` on itself, drafting and approving DEC and ARCH artifacts *before* writing framework code.

## v1.7.1

Focus: **cross-platform skill export and dogfooding.**

- **Cross-platform skill export** — `specflow export --skills --format cursor-rules|gemini-toml|codex-agents|markdown` converts 10 SpecFlow skills to platform-specific formats
- **Dogfooding** — DEC-052..054 created retroactively for v1.6.6-v1.7.0 changes, linked to AUD-038
- **Deferred**: skill chaining, protocol compliance checks, wave parallelism → future releases

## v1.7.0

Focus: **multi-agent integration, orphan detection, and hook hardening.**

- **Multi-agent in core skills** — artifact-review: parallel adversarial lenses for deep review. Plan: parallel ARCH candidates (3 decomposition seeds). Audit: error-driven lens fan-out (2-5 agents). Change-impact: blast-radius fan-out (per-type or per-artifact)
- **Orphan code detection** — `specflow detect orphan-code` + `--retro-link` for batch retroactive traceability
- **Pre-commit hook hardened** — link integrity (blocking), schema validation (blocking), suspect flag warnings
- **RBAC pre-check in execute** — gate checks team authorization before implementation
- **Protocol integrations reference** — comprehensive producer-consumer map across all protocols
- **Deferred**: skill chaining, protocol compliance checks, cross-platform export, wave parallelism → v1.7.1

## v1.6.7

Focus: **autoresearch protocol hardening — EDA enforcement, cross-loop learning, and EXPT quality.**

- **Mandatory initial EDA** — Phase 0.6: 4 universal + domain-specific data checks run once at LOOP start; fatal problems hard-stop before any iteration
- **Prior-LOOP review** — Step 0b: reads last LOOP's full state (raw EXPTs, failure clusters, condensation briefs, trajectory) before first iteration
- **LOOP post-mortem** — `lessons_learned` + `looplevel_findings` fields capture process knowledge: ranked categories, dead ends, sensitivity discoveries, noise floor, unexplored directions
- **EXPT design quality rubric** — Phase 6.6: every EXPT rated 1-4 (Invalid→Definitive), lesson extracted regardless of outcome, auxiliary signal detection
- **Cross-EXPT pattern detection** — interaction detection (synergistic/antagonistic pairs), progression shape analysis, negative-space analysis, design quality trends
- **Auxiliary metric synthesis** — systematic correlation/trend/breakpoint analysis; mandatory cross-loop synthesis triggers (2+ LOOPs, 3+ LOOPs, stale low-confidence FINDs)
- **Graded post-check consequences** — minor/moderate/severe tiers; severe = `deployability: not_deployable`
- **Supporting protocols hardened** — noise-handling: EXPT validity gate. Crash-recovery: pre-recovery telemetry. Methodology: BP-01 mandatory

## v1.6.6

Focus: **context rebalancing, routing clarity, and drift prevention.**

- **Injected context rebalanced** — `agent-context.md` rewritten: 4:1 core-to-pack ratio (was 0.6:1), routing section declares packs as separate subsystems with anti-triggers
- **Pack context stubs** — autoresearch `context_snippet` reduced from 30 lines to 6-line routing stub; operational detail deferred to on-demand SKILL.md
- **Graduated skill triggers** — all 10 skill descriptions rewritten: execute is DEFAULT, discover bridges natural language ("add X," "build Y"), mutual anti-triggers on audit/artifact-review/change-impact-review
- **Standardized gate language** — `blocking`/`warning`/`info` severity vocabulary and articulated escape hatches on all 6 operational skills
- **Graduated obligation in execute** — 5-tier change-type table replaces binary "never skip" gate
- **Articulated escape hatches** — `AGENTS.md` L108: silent skip → articulated skip with risk statement
- **Platform-safe subagent patterns** — 5 autoresearch spawn locations guarded with "if your platform supports it" + sequential fallback paths
- **Stale docs fixed** — `specflow-init` Step 4 updated to reflect CLI auto-injection

## v1.6.4

Focus: **status cascade automation and reconciliation.**

- **Status cascade** — `specflow cascade-status STORY-NNN` propagates `implemented`/`verified` to linked ARCH/DDD (optionally REQ) in one call, replacing manual per-artifact updates
- **Reconciliation** — `specflow reconcile` auto-detects approved stories with implementation evidence (output files on disk or git commits) and promotes them to `implemented`
- **Status-cascade lint** — `artifact-lint` warns when STORY status outpaces linked ARCH/DDD status, catching drift before it compounds
- **Executor fix** — `specflow go` no longer prematurely marks artifacts as `implemented` during wave assembly
- **Execute skill update** — Step 4 uses `cascade-status` one-liner instead of manual per-artifact updates

## v1.x (Future)

These may ship someday, but are not committed:

- **Product variant management** — tag-based product line engineering for multi-trim / multi-variant projects
- **FMEA / risk analysis** — hazard, safety-goal, and risk-control artifact types via industry packs
- **REST API** — programmatic access for custom toolchain integration
- **Static HTML export** — `specflow export --html` for zero-dependency dashboard generation
- **Multi-pack aggregated compliance** — unified compliance view across all installed standards

## Out of Scope

These are explicitly **not** on the roadmap. We acknowledge the limits:

| Area | What we won't do | Why |
|------|-----------------|-----|
| Shipped compliance packs | No real ISO 26262, ASPICE, or other copyrighted standard packs | Copyright risk; "Bring-Your-Own-Standard" is the model |
| Web dashboard / server | No `specflow serve` or hosted visualization | Contradicts zero-dependency, filesystem-native philosophy |
| External integrations (Jira, Azure DevOps) | No bidirectional sync with agile boards | Complex, enterprise-specific, premature until core is solid |
| Database backend | No SQLite, PostgreSQL, or any database | The filesystem IS the database |
| Real-time collaboration | No concurrent editing, live updates | Git is the collaboration layer |
| Multi-project management | SpecFlow manages one project per repo | Cross-repo coordination is a different product |
| LLM-dependent core | All core validation remains zero-token deterministic | LLM is opt-in at the skill layer, never required for core operations |
