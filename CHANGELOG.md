# Changelog

All notable changes to SpecFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.6.5] - 2026-05-30

### Highlights

- **CLI-driven instruction injection** — `specflow init` now deterministically injects the base SpecFlow context block into the platform's instruction file (AGENTS.md, CLAUDE.md, etc.) using idempotent HTML-comment sentinels. No more manual copy-paste by the agent.
- **Multi-preset support** — `--preset` accepts comma-separated packs (e.g., `--preset autoresearch,tldr-communication`). Each pack's context snippet is injected as an independent sentinel block.
- **Condensed base context** — `agent-context.md` reduced from ~90 lines to 24 lines while retaining all functional rules (V-Model, status lifecycle, traceability, cascading).

### Features

- `scaffold.inject_base_context()` — new function that reads `agent-context.md` and appends it to the instruction file with `<!-- SpecFlow section -->` sentinel markers. Handles create, append, update, and idempotent no-op.
- `scaffold._get_target_instruction_file()` — shared helper resolving the correct instruction file per platform, with CLAUDE.md/GEMINI.md fallback.
- `--preset` flag in `specflow init` now splits on commas and applies each pack sequentially.
- `inject_pack_context()` accepts `explicit_platform` parameter, fixing a timing bug on fresh repos where platform detection returned `None`.

### Changes

- `agent-context.md` trimmed from ~90 lines to 24 lines (removed redundant tables, tutorial text, docs links).
- `specflow-init` SKILL.md step 4 (manual injection) removed — the CLI now handles this deterministically.
- Base context is always injected before pack context, ensuring consistent ordering in the instruction file.

## [1.6.4] - 2026-05-29

### Highlights

- **Status cascade automation** — new `specflow cascade-status` and `specflow reconcile` commands automate the previously manual process of propagating STORY status to linked ARCH/DDD/REQ artifacts and detecting stories with implementation evidence.
- **Status-cascade lint check** — `artifact-lint` now warns when a STORY is `implemented`/`verified` but linked ARCH/DDD still sits at `approved`, catching status drift before it compounds.

### Features

- `specflow cascade-status STORY-NNN` — one-liner to propagate `implemented`/`verified` status to linked ARCH (via `guided_by`), DDD (via `specified_by`), and optionally REQ (via `--include-req`). Dry-run support with `--dry-run`.
- `specflow reconcile` — auto-detects approved stories with implementation evidence (output files on disk or git commits referencing the story ID), promotes to `implemented`, and optionally cascades. Dry-run support with `--dry-run`, cascade control with `--no-cascade`.
- `status-cascade` lint check in `artifact-lint` — warns when STORY is `implemented`/`verified` but linked ARCH/DDD is still `approved`, or when STORY is `verified` but linked REQ is still `approved`. Non-blocking (warnings only). Actionable message suggests `specflow cascade-status`.
- Both new commands registered in CLI dispatch table and help epilog (`Execute` phase).

### Fixes

- `executor.py` no longer prematurely calls `update_artifact(status="implemented")` during wave execution. Wave commit messages now say "wave N prepared" instead of claiming implementation.
- `specflow-execute` SKILL.md (both `.claude/skills/` and `templates/skills/`) Step 4 now uses `cascade-status` instead of manual per-artifact updates.
- `agent-context.md` strengthened with explicit 2-step status update instruction (update + cascade-status) for both `/specflow-execute` and ad-hoc sessions.

### Changes

- Autoresearch SKILL.md: Post-Loop section clarified that delegate-review subagent creates FINDs (not the main agent). Added lifecycle flow diagram. Updated rules.
- `docs/plan-autoresearch-integration.md`: learning flow diagram updated to reflect delegate-review subagent pattern.
- `_HELP_EPILOG` in `cli.py` updated to list `cascade-status` and `reconcile` under Execute phase.

## [1.6.0] - 2026-05-16

### Highlights

- **Autoresearch pack v0.2.0** — autonomous research loops are now harness-agnostic. Any LLM harness (Claude Code, Cursor, scripted CI) can drive the iteration loop through a single `specflow autoresearch` CLI subcommand instead of platform-specific skills.
- **Multi-criteria competitions** — competitions now support a primary metric for ranking, binary guards for hard floors, and freeform auxiliary metrics for post-hoc analysis. Documented patterns for leakage prevention and anti-gaming as recommendations, not mandates.
- **Pack context injection** — installed packs now write a sentinel-bracketed context block into the project's platform instruction file (e.g. `AGENTS.md`) on `specflow init --preset <pack>`, giving the host agent the right vocabulary without requiring per-platform skill variants.

### Features

- `specflow autoresearch plan|run|review|leaderboard` CLI subcommand (`src/specflow/commands/autoresearch.py`)
  - `plan`: prints setup-gate checklist for a competition, optional `--profile` for 3x noise variance probe
  - `run`: prints the 8-phase iteration protocol with current LOOP progress (harness drives the loop; this command does not embed a model client)
  - `review`: shows FINDs, top kept EXPTs with auxiliary metrics, and loop history
  - `leaderboard`: ranks kept EXPTs by primary metric, supports `--all` for cross-COMP view
  - Multi-COMP repos: auto-detects single active COMP, prompts when ambiguous, `--competition COMP-NNN` to disambiguate
- `auxiliary_metrics` optional field on EXPT artifacts — freeform YAML dict for post-hoc enrichment (max_drawdown, total_trades, win_rate, runtime_seconds, etc.) that does not affect the kept/discarded decision
- `inject_pack_context()` library function and `context_snippet` field in `pack.yaml` — packs declare a markdown snippet that gets injected into the platform's instruction file with idempotent sentinel markers (`<!-- pack:<name> context ... -->`)
- `instruction_file` field on all 14 platforms in `templates/platforms.yaml` — points pack context injection at the right file per harness (AGENTS.md, .cursor/rules/specflow.md, .github/copilot-instructions.md, etc.)
- "Multi-criteria competitions" section in `competition-setup-protocol.md` explains primary metric / guards / auxiliary metrics with a worked quant example and a strictness ladder
- "Leakage and Gaming" section documents read-only eval data patterns, one-number verify output, and robustness-adjusted primaries as recommendations
- Anti-gaming pointer in `autonomous-loop-protocol.md` Phase 5 + auxiliary metrics logging guidance in Phase 7 with domain-specific examples (quant, ML, NLP, systems)
- `specflow init --preset autoresearch` now writes a `<!-- pack:autoresearch context -->` block into the detected platform's instruction file
- 12 new tests in `tests/test_autoresearch_pack.py`: 7 CLI subcommand tests (`TestAutoresearchCLI`), 3 context-injection tests (`TestPackContextInjection`), 2 auxiliary-metrics schema tests

### Fixes

- `inject_pack_context()` is now actually called from `_apply_preset` in `init.py` — previously the function existed but no production code invoked it, leaving pack context injection as dead code
- `specflow autoresearch leaderboard --all --competition COMP-X` now errors out instead of silently letting `--all` win
- `src/specflow/__init__.py` `__version__` bumped from stale `1.2.0` to `1.6.0` to match `pyproject.toml`

### Documentation

- `SKILL.md` for the autoresearch skill thinned to reference CLI backends instead of inlining full protocol; safety posture, anti-patterns, principles, and rules sections preserved
- Subcommands table maps each `/specflow-autoresearch:*` skill invocation to its `specflow autoresearch <sub>` CLI backend
- Phase 7 logging examples in `autonomous-loop-protocol.md` now demonstrate `--auxiliary-metrics` JSON dict invocation

## [1.6.3] - 2026-05-25

### Highlights

- **Goal-driven research ladder** — autoresearch now treats experiments as evidence under a tiered hierarchy of Goals → Theses → Research Questions → Hypothesis → EXPT → Parameters. The ladder is walked once at LOOP creation; per-iteration the agent stays goal-mindful via a 3-question self-assessment that prevents parameter-wandering and sunk-cost on the wrong axis.
- **Protocol split** — `autonomous-loop-protocol.md` trimmed (839 → 758 lines) by extracting `noise-handling-protocol.md` (Phase 5.1 strategies) and `crash-recovery-protocol.md` (verify-failure and session-crash rules) into dedicated reference files, reducing per-iteration context tax.
- **Pre/post-EXPT mindfulness** — consolidated Phase 2d (premise check before running the EXPT) and Phase 2e (no blind parameter sweeps; collapse sweeps into one EXPT with a local script) into cleaner, less redundant rules. Dynamic post-check guidance for deep failure analysis on strongly-reasoned-but-failed EXPTs.
- **Constraints as a first-class field** — `COMP.constraints` captures forbidden data/techniques (e.g. "no pre-trained weights", "no transformers library") so the agent doesn't propose solutions that violate the user's implicit rules.

### Features

- `COMP.theses` (list of strings) — durable, cross-loop research agenda
- `LOOP.active_research_questions` (list of strings) — loop-scoped operationalization of theses
- `COMP.constraints` (string) — rules of engagement (forbidden data, libraries, techniques)
- `EXPT.research_question` (string) — links the EXPT back to the active RQ it serves
- `references/noise-handling-protocol.md` — strategy menu for volatile metrics (multi-run, confirmation, env pinning, min-delta)
- `references/crash-recovery-protocol.md` — recovery rules for verify failures and session crashes
- `competition-setup-protocol.md` Step 6.6 (constraints) and Step 6.7 (theses elicitation)
- FIND authoring template asks for the `COMP.theses` entry each finding supports, refutes, or refines — closes the evidence loop across LOOPs
- Proactive enforcement loops in `specflow-plan`, `specflow-execute`, `specflow-discover` skills — BPs are now actively audited against, not passively read; decomposition + sanity checks suggested before monolithic implementation; anti-requirements elicited during discovery

### Changes

- Phase 2a rewritten as a goal-mindfulness check (3 quick questions) rather than a full ladder rewalk per iteration — the heavy lift lives in Setup Gate
- Phase 5.1 (noise handling) and Crash Recovery sections in the main protocol replaced with one-line pointers to their dedicated reference files



### Highlights

- **7 new research thinking lenses** — `leakage_audit`, `overfitting_multiple_comparisons`, `baseline_sanity`, `distribution_shift`, `ablation_attribution`, `metric_validity`, and `reproducibility` added to the adversarial catalog. Research artifacts (COMP, LOOP, EXPT, FIND) get per-level default lens sets selected automatically by `artifact-review --depth deep`.
- **Concise prompts** — ~800 tokens saved across the 23-lens catalog by extracting repeated JSON/boilerplate into a single `_GENERIC_LENS_SUFFIX` injected at runtime.
- **Atomic EXPT logging** — `specflow autoresearch log` creates an EXPT artifact and auto-updates LOOP counters (`iteration_count`, `kept_count`, `discarded_count`, `best_metric`) in one CLI call, replacing the error-prone two-step `create` + `update` sequence.
- **Deterministic FIND drafting** — `specflow autoresearch suggest-finds` groups EXPTs by `change_category`, synthesizes `what_worked` / `what_failed` / `next_steps`, and either prints a draft or writes a FIND artifact with `--write`. Zero LLM tokens.
- **Subagent guidance in SKILL.md** — explicit instructions for spawning parallel subagents per `change_category` during FIND synthesis, and per-strategy-family in `family_of_good` competitions, to keep context windows small.

### Features

- `LENS_CATEGORIES` three-way taxonomy (`software`, `research`, `both`) with `ARTIFACT_LEVEL_DEFAULT_LENSES` mapping artifact types to appropriate lens sets
- `_prompt_for_techniques()` now detects mixed research+software artifact reviews and falls back to `both`-category lenses only, preventing `leakage_audit` from running on user stories
- `autoresearch log` CLI subcommand with `--loop`, `--status`, `--metric-value`, `--change-category`, `--summary`, `--title`, `--set KEY=VALUE`, and `--no-update-loop` flags
- `autoresearch suggest-finds` CLI subcommand with `--loop` and `--write` flags
- Passive-CLI banner on `autoresearch run` — prints a one-line reminder that the AI agent drives the loop, not the CLI
- "Coexisting with External ML Trackers" section in `competition-setup-protocol.md` — documents integration pattern with MLflow, Weights & Biases, Neptune, MLRun, etc.
- Updated `pack.yaml` `context_snippet` to advertise `log` and `suggest-finds` commands
- 13 new tests in `tests/test_autoresearch_pack.py`: 4 mixed-review / conciseness tests (`TestResearchThinkingLenses`), 4 smoke tests for `log` and `suggest-finds` (`TestAutoresearchLogAndSuggestFinds`)

### Fixes

- Mixed-artifact review bug where `artifact-review --all --depth deep` on a project with both software and research artifacts could apply research lenses to software artifacts

## [1.6.1] - 2026-05-20

### Highlights

- **Goal-driven, richer autoresearch** — experiments now carry `hypothesis` / `hypothesis_outcome`, `pre_check_command` / `post_check_command`, `objective_type` (`single_best` / `family_of_good` / `pareto_front`), and `domain`-aware auxiliary metric linting.

### Features

- Generic `--set KEY=VALUE` flag on `specflow create` and `specflow update` — JSON-aware, repeatable, enables arbitrary frontmatter fields (EXPT `metric_value`, COMP `goals`, LOOP `termination_suggestions`, etc.) without hardcoding CLI flags
- `hypothesis` and `hypothesis_outcome` (`supported` / `not_supported` / `inconclusive`) fields on `experiment.yaml`
- `pre_check_command` and `post_check_command` on `competition.yaml` with `checks` array on EXPT recording pre/verify/post pipeline results
- `objective_type` (`single_best`, `family_of_good`, `pareto_front`) and `goals` on COMP; `termination_suggestions` on LOOP for dynamic, goal-aware stopping
- `domain` field (`quant`, `ml`, `nlp`, `systems`, `safety_critical`) on COMP drives `artifact-lint` warnings when domain-recommended auxiliary metrics are missing from kept EXPTs
- `noise_characterization` on COMP stores variance-probe results
- `deployability` and `safety_assessment` fields on FIND
- `specflow autoresearch review` warns when completed LOOPs have zero FINDs or when discarded EXPTs lack `failure_analysis`
- `specflow autoresearch leaderboard --group-by model_origin` and `--show-family` for swarm/ensemble views
- `parameters`, `model_origin`, `sweep_results`, `diversity_metrics`, and `failure_analysis` fields on `experiment.yaml`

### Fixes

- `src/specflow/__init__.py` `__version__` bumped from `1.6.0` to `1.6.1` to match `pyproject.toml`

## [1.5.0] - 2026-05-07

### Highlights

- **Unified 16-lens adversarial catalog** — all 16 thinking technique lenses are now available in every lifecycle phase (discover, plan, execute, review, audit) via a shared reference catalog at `.claude/skills/specflow-references/`.
- **Thinking technique records on artifacts** — new `thinking_techniques` optional field on all 13 artifact types tracks which lenses were applied. New `--thinking-techniques` flag on `specflow update` appends techniques to any artifact.
- **Technique-to-BP feedback loop** — best-practice staleness checks now include challenge (CHL) artifacts; BP synthesis prompts inject recent adversarial findings so regenerated BPs learn from what lenses actually caught.
- **Audit technique granularity** — audit CHLs now carry per-axis technique names (`audit-horizontal`, `audit-vertical`, `audit-cross-cutting`) instead of the monolithic `project-audit`.
- **Generic lens fallback** — the 12 lenses without dedicated Python modules now run as generic LLM prompts using the shared lens catalog, making all 16 lenses runnable from the CLI.

### Features

- Shared 16-lens adversarial catalog with per-phase default sets and trigger-for-expansion guidance (`.claude/skills/specflow-references/references/adversarial-lenses.md`)
- `specflow update <ID> --thinking-techniques <comma-separated>` flag for recording techniques on artifacts (appends, deduplicates)
- New `thinking-techniques` lint check: warns on approved REQ/ARCH/DDD artifacts with no `thinking_techniques` recorded
- `_is_stale_against_evidence()` replaces `_is_stale_against_decisions()` — checks both DEC and CHL artifact mtimes against BP cache
- `_recent_chl_summaries()` injected into phase-level BP synthesis prompts so LLM can incorporate "what keeps getting caught"
- Per-skill `references/thinking-techniques.md` files replaced with pointers to shared catalog
- Technique recording instructions added to discover, plan, execute, and audit SKILL.md files
- `_DEFAULT_LEARNABLE_TECHNIQUES` expanded from 5 to 17 entries (all 16 lenses + checklist-run)
- `LENS_CATALOG` dict in `techniques/__init__.py` provides system prompts for all 16 lenses
- `ALL_LENS_NAMES` exported set for external validation of technique names

- Dedicated technique modules (devil's advocate, premortem, red/blue team, assumption surfacing) import system prompts from `LENS_CATALOG` instead of duplicating inline strings
- `_run_generic_lens()` fallback in `execute_technique()` runs catalog lenses without dedicated Python modules
- `run_subagents()` concurrency capped at `min(techniques × artifacts, 8)` to prevent thread pool explosion
- `_recent_chl_summaries()` rewritten: sorts by severity weight then recency, excludes accepted/stale/resolved CHLs, includes first 200 chars of rationale, defaults to 10 items
- `compose_review_prefix()` accepts `existing_techniques` parameter to render "Previously applied thinking techniques" section in review prompts
- `artifact_review.py` extracts `thinking_techniques` from target artifact and passes to `compose_review_prefix()`
- `build_phase_synthesis_prompt()` accepts `learned_patterns` parameter for learned PREV-*.yaml injection
- `_learned_patterns_text()` reads prevention patterns from `.specflow/checklists/learned/` and formats for BP synthesis
- `synthesize_and_cache()` now calls `_learned_patterns_text()` and passes results to phase synthesis prompt
- `update.py` validates technique names against `ALL_LENS_NAMES` (warns on unknown, still records)
- `specflow-discover` lean path records `lean_assessment` sentinel on auto-approved REQs to avoid lint warnings
- `specflow-change-impact-review` fixed wrong adversarial-lenses catalog path and added technique recording step
- All 13 artifact schemas updated with `thinking_techniques` as optional field
- `thinking_techniques` added to `known_meta` in lint validation whitelist

### Fixes

- Audit CHL artifacts now carry specific technique names (`audit-horizontal`, `audit-vertical`, `audit-cross-cutting`) instead of generic `project-audit`
- Fixed `_learned_patterns_text()` reading wrong field names from PREV-*.yaml patterns — uses `name`/`discovered_from` instead of `title`/`trigger`
- Added `lean_assessment` to `_SENTINEL_NAMES` in `update.py` to suppress spurious "Unknown technique" warning on lean-path REQs
- `ci.py` and `handbook.py` now forward `existing_techniques` to `compose_review_prefix()`, preventing duplicate findings on review passes through those code paths

### Tests

- 14 new tests in `test_best_practices.py` covering `_learned_patterns_text`, `_recent_chl_summaries`, and `compose_review_prefix` with `existing_techniques`
- 10 new tests in `test_artifact_lint.py` for thinking-techniques lint check (status filtering, type filtering, lean_assessment sentinel, implemented/verified statuses)
- 1 new test in `test_technique_fallback.py` for `run_subagents` concurrency cap
- 6 new tests in `test_challenges.py` for shared CHL creation module
- 7 new tests in `test_standards_get_clause.py` for `get_clause_by_id`
- 14 new tests in `test_reverse_impact.py` for glob matching, query/flag split, recursive propagation

## [1.4.1] - 2026-05-06

### Highlights

- **Read-only `change-impact` by default** — `specflow change-impact` no longer silently flags artifacts as suspect when displaying source-file matches; use `--flag` to opt into suspect flagging.
- **Recursive downstream propagation** — suspect flagging now propagates transitively through the full dependency chain (ARCH → DDD → UT), not just one level.
- **`**` recursive glob support** — `output_files` patterns with `**` (e.g., `src/**/*.py`) now correctly match files in nested subdirectories.
- **Converged CHL creation** — duplicated `_create_chl_artifacts` logic in `project_audit.py` and `artifact_review.py` replaced with a single shared module (`specflow/lib/challenges.py`).
- **Per-suspect resolution** — `resolve_suspect` now tracks resolution per individual suspect within an event, rather than resolving the entire event when one artifact is resolved.

### Fixes

- `reverse_impact` split into `query_reverse_impact` (pure query, no file mutation) and `flag_suspects_from_matches` (mutation only); `reverse_impact` kept as backward-compatible wrapper
- `_find_all_downstream_recursive` added for transitive suspect propagation via BFS
- `_glob_match` replaces raw `fnmatch` calls, supporting `**` recursive glob patterns with proper regex conversion including trailing/standalone `**`
- `resolve_suspect` tracks `resolved_suspects` list per impact-log event; event only resolves when all suspects are individually resolved
- Stale pseudocode in DDD-005.md ("Challenge Deduplication") updated to reflect converged implementation
- DDD-019.md updated to document `query_reverse_impact`, `flag_suspects_from_matches`, `_glob_match`, and `--flag` CLI option
- ROADMAP.md "v1.x (Future)" section cleaned — removed "Review workflow artifacts" and "Compliance evidence quality" (both shipped in v1.4.0)
- Raw ANSI escape sequences in `change_impact.py`, `project_audit.py`, and `artifact_review.py` replaced with `specflow.lib.display` constants

### Internal

- New `specflow/lib/challenges.py` — shared `create_chl_artifacts()` accepting `TechniqueFinding` objects with configurable `link_role`, `dedup`, `review_id`, and `technique_override`
- `project_audit.py` converts its `list[dict]` findings to `TechniqueFinding` and calls shared module with `link_role="refers_to"`, `dedup=True`
- `artifact_review.py` delegates to shared module with `link_role="challenges"`, `dedup=False`
- `cli.py` adds `--flag` argument to `change-impact` subcommand
- 30 new tests: 9 for glob matching (including trailing/standalone `**`), 3 for query/flag split, 2 for recursive propagation, 6 for shared challenges module, 7 for `get_clause_by_id`, 1 for zero-keyword clause edge case, 2 for trailing `**` fix

## [1.4.0] - 2026-05-05

### Highlights

- **Compliance evidence quality** — `complies_with` links now require substantive backing content. New `compliance-evidence` lint check warns when artifacts claim conformance but have a thin body or fail to reference clause keywords. Strict mode (`lint.compliance_evidence_strict: true` in config) escalates warnings to blocking errors.
- **REVIEW artifact type** — `artifact-review` now emits a `REVIEW-NNN` artifact summarizing each review pass over a target artifact. Spawned CHL findings link back to the REVIEW via `refers_to`, and the REVIEW carries the finding summary, depth, reviewers, and consensus fields. CHLs remain the per-finding record; REVIEW captures the pass.

### Features

- New `_check_compliance_evidence()` lint check in `artifact_lint.py` with `_COMPLIANCE_MIN_WORDS=50` threshold; pulls clause keywords from `standards_lib.get_clause_by_id()` and verifies at least one keyword appears in the artifact body
- New `templates/schemas/review.yaml` registering REVIEW type with statuses (open/closed), reviewer/consensus/findings/depth fields, and `review_of`/`refers_to` link roles
- `review` registered in `TYPE_TO_DIR`/`PREFIX_TO_TYPE` (`artifacts.py`); `specs/reviews/` added to scaffold `SPEC_DIRS` so `specflow init` provisions it for new projects
- `artifact-review` exposes `emit_review_pass(root, target, findings, depth)` as a public helper; legacy CHL-only path replaced with REVIEW + linked CHLs whenever there are actionable findings
- `_bootstrap_review_schema()` ensures repos that pre-date v1.4.0 get the `review.yaml` schema and `_specflow/specs/reviews/` directory copied in on first run of `artifact-review`
- `specflow status` now displays a `Reviews:` line counting REVIEW + AUD + CHL artifacts when any are present

### Internal

- 6 new unit tests in `test_artifact_lint.py` (TestCheckComplianceEvidence) covering thin-body warning, missing-keyword warning, substantive-content pass, strict-mode blocking, unresolved-clause fallback, and no-link short-circuit
- 4 new tests in `test_review_artifact.py` covering REVIEW emission, CHL backlinks, status counting, and type registration
- `CHECK_NAMES` and CLI `--type` choices both updated to include `compliance-evidence`

## [1.3.1] - 2026-05-05

### Highlights

- **Verification gap closed** — generated UT/IT/QT triplets for REQ-022..027 / ARCH-016..021 / DDD-017..021, lifting STORY test coverage from 76% to 100% (63/63) and chain coverage from 75% to 100% (69/69)
- **Decision housekeeping** — promoted all 42 draft DEC artifacts to `approved`, eliminating the long-tail housekeeping flag from project-audit

### Internal

- 17 new test artifacts: QT-023..028, IT-018..023, UT-023..027 (linked to verifying REQs/ARCHs/DDDs and to all 15 stories STORY-049..063)
- `specflow project-audit --quick` now reports 0 vertical findings on this repo's specs
- Promoted REQ-022..027 from `approved` to `implemented` (prerequisite for test-stub generation)

## [1.3.0] - 2026-05-05

### Highlights

- **Reverse impact analysis** — source code changes now map back to spec artifacts via `output_files`, closing the bidirectional traceability loop from code to specification
- **Decomposition completeness guidance** — SPIDR dimension coverage and dependency cycle detection in `artifact-lint`, plus generic best-practice fallback for offline handbook generation

### Features

- **Reverse impact engine** — `build_output_file_index()` and `reverse_impact()` in `impact.py` map changed source files to governing artifacts via literal and glob pattern matching
- **Source File Impact section** — `specflow change-impact` now includes a "Source File Impact" section listing source file changes and their associated spec artifacts
- **SPIDR coverage lint check** — `spidr-coverage` check reports when SPIDR dimensions have no stories, ensuring decomposition coverage across all five sources
- **Wave cycle detection lint check** — `wave-cycles` check detects circular dependencies between stories and flags stories with excessive dependencies (>=4)
- **DDD selection decision tree** — new reference document `references/ddd-selection.md` with a 6-question decision checklist for determining which ARCH components need DDD artifacts
- **Generic BP fallback** — bundled generic best-practice YAML templates for `plan-arc`, `plan-ddd`, and `plan-story` phases; `specflow handbook generate` now falls back to these when no LLM API key is configured instead of failing
- **Discovery challenge persistence** — discover skill Step 5 now creates DEC artifacts for dropped requirements, surfaced assumptions, and identified risks
- **Inter-REQ dependency prompting** — discover skill Step 4 explicitly asks about inter-REQ dependencies and records them as `derives_from` links
- **Domain context pass-through** — plan skill Step 2 reads domain classification and decision artifacts from discovery
- **Improved discover-to-plan handoff** — discover skill exit message explicitly lists draft REQ IDs needing approval with the exact command to run

### Documentation

- New reference: `.claude/skills/specflow-plan/references/ddd-selection.md`
- Updated: `.claude/skills/specflow-discover/SKILL.md` Steps 4, 5, 7
- Updated: `.claude/skills/specflow-plan/SKILL.md` Steps 2, 4

## [1.2.0] - 2026-05-05

### Highlights

- **Init upgrade safety** — re-running `specflow init` on an existing project now preserves config and state via merge mode; `--force` enables clean re-init with timestamped backup
- **Specification body quality enforcement** — `artifact-lint` now validates ARCH and DDD artifacts for substantive content (word counts, structural headers), REQ-to-ARCH coverage, and minimum acceptance criteria
- **Output file traceability** — new `output_files` field on ARCH/DDD/STORY schemas with filesystem existence verification and glob pattern support

### Features

- **`specflow init` merge mode** — re-initialization preserves existing config.yaml, state.yaml, and schemas; merges new defaults with user values; reports version deltas
- **`specflow init --force`** — clean re-init with timestamped backup of config, state, and schemas to `.specflow/cache/backups/`
- **Config version stamping** — `config.yaml` now includes a `version` field tracking the SpecFlow release that wrote it
- **`spec-body` lint check** — validates ARCH artifacts for 50+ words and structural headers; DDD artifacts for 100+ words and design headers
- **`output-files` lint check** — verifies that paths declared in `output_files` frontmatter exist on the filesystem; skips glob patterns
- **Extended coverage check** — `coverage` check now also verifies approved REQs have at least one ARCH linking via `derives_from`
- **Story minimum AC check** — `story-size` check warns when stories have fewer than 2 acceptance criteria
- **`output_files` field** — optional field on architecture, detailed-design, and story schemas for bidirectional file traceability
- **`specflow update --output-files`** — set, replace, or remove `output_files` on any artifact (empty string removes the field)

### Fixes

- `specflow init --force` now correctly overwrites schemas with fresh copies (previously incremental copy left stale schemas in place)
- `specflow update` error message now mentions `--output-files` as an available flag

## [1.1.0] - 2026-05-03

### Highlights

- **Domain intelligence and learning feedback** — SpecFlow now generates domain-specific best practices via LLM, learns prevention patterns from review findings, and gives users visibility into accumulated knowledge.

### Features

- **Domain best-practice synthesis** — `specflow handbook generate` creates project-level and phase-level BP guides via LLM, cached as human-editable YAML in `.specflow/cache/best-practices/`
- **Knowledge accumulation lifecycle** — blocking/warning findings from artifact reviews are automatically converted into `PREV-*.yaml` prevention patterns in `.specflow/checklists/learned/`
- **`specflow patterns` command** — inspect learned prevention patterns (`list`, `show`)
- **Per-item checklist scoping** — `applies_to.types` on individual checklist items overrides top-level filter
- **Configurable learning** — `learnable_techniques` and `max_patterns_per_session` in `config.yaml`
- **Expanded learnable techniques** — adversarial findings (devil's advocate, premortem, assumption surfacing, red/blue team) now feed into learning by default
- **`--fast` flag on `artifact-review`** — skip BP synthesis for CI, use cached best practices only
- **Auto-backup on `--overwrite`** — previous BP files are backed up before regeneration
- **`specflow done` auto-extraction** — `--auto` is now the default, extracts prevention patterns from implemented stories
- **Dual few-shot examples** — phase BP prompts include both embedded and API-service examples for quality anchoring

### Fixes

- `_learnable_techniques` is now configurable (was hardcoded to `checklist-run` only)
- `specflow done` no longer shows a dead-end "requires interactive prompts" message
- Stale version in `src/specflow/__init__.py` (was `0.1.0`, now tracks release)
- Phase prompt few-shot now shows two domain examples instead of one

### Documentation

- Added `specflow patterns` and `specflow handbook` to CLI reference
- Added `--fast` flag and `--no-auto` flag documentation
- Updated install pin in README to `v1.1.0`
- Updated ROADMAP with v1.1.0 section and v1.0.1 entries
- Updated `docs/plan.md` release table

## [1.0.1] - 2026-04-23

### Fixed

- AGENTS.md template now lists all 10 skills (was missing `/specflow-adapter`)
- AGENTS.md template now includes V-model explanation, invocation routing rules, CLI-only command references, and doc pointers for deeper context
- ROADMAP no longer lists Jira/Azure DevOps sync in both v1.x and Out of Scope
- `docs/plan.md` release table updated to reflect shipped versions

### Changed

- `/specflow-init` completion message now suggests `/specflow-adapter` for CI-first teams

## [1.0.0] - 2026-04-22

### Highlights

- First stable release. Everything since v0.2.0 plus polish, stability, and adoptability improvements.

### Features

- **Unified CLI framework** — streamlined installation path, unified adapter framework, and command renaming
- **Skill ecosystem restructuring** — collapsed 22 skills into 10 core Tier 1 conversational skills
- **Shared thinking techniques** — adversarial lenses extracted into stage-specific reference catalogs for discover, plan, and execute skills, enabling "build it right the first time" rather than post-review fixes
- **Freeform skill input** — all 10 skills accept natural language context (e.g., `/specflow-audit I'm worried about REQ coverage`) for scoped, directed workflows
- **Compliance evidence reports** (`specflow baseline create --evidence`) — generates a Markdown report with traceability matrix, test results summary, baseline diff, and per-standard coverage scores
- **Enhanced standards gap analysis** (`specflow standards gaps`) — coverage scoring (0–100%), severity-sorted gap list, rule-based remediation suggestions, `--json` flag
- **Optional artifact type schemas** (`specflow init --with-types hazard,risk,control`) — installable hazard, risk, and control artifact types
- **Compliance summary in status** — `specflow status` shows per-pack compliance scores when standards are installed
- **Continuous auditing** — project audits support conversational scope and chunked fan-out
- **Convention enforcement** — project convention checklists scaffold and enforce project structure

### Documentation

- **README rewrite** — clearer visual hierarchy, concise feature table, disambiguation section for similarly-named projects
- **AGENTS.md release process** — documented CHANGELOG, git tagging, and GitHub Release workflow
- **ROADMAP updated** — v1.0.0 reflects polish focus; deferred items and out-of-scope limits documented explicitly

### Changed

- Thinking techniques (adversarial lenses) are now woven into `/specflow-discover` and `/specflow-plan` as creation-time challenges, not limited to `/specflow-artifact-review`
- `/specflow-discover` Step 5 now challenges requirements before finalizing artifacts
- `/specflow-plan` Step 4.5 now stress-tests architecture before creating artifacts
- `/specflow-execute` now includes quick thinking checks during implementation
- Skill instruction templates rewritten and unified across all 14 AI platforms
- Documentation completely overhauled to focus on the 10-command skill surface

### Fixed

- `check_compliance()` now reports `total_clauses` consistent with the score denominator
- Project audit correctly detects ARCH and DDD refinements linked via `derives_from`
- Resolved schema and traceability gaps in self-specification artifacts

## [0.2.0] - 2025-04-21

### Added

**Slash Commands**
- `/specflow-init` — Bootstrap project with auto-detected platform, skills, and optional CI
- `/specflow-discover` — Progressive disclosure conversation for requirement capture
- `/specflow-plan` — Architecture proposal, DDD creation, SPIDR story decomposition
- `/specflow-execute` — Wave-based story implementation with status updates
- `/specflow-artifact-review` — Lint + checklists + LLM judgment + adversarial lenses
- `/specflow-change-impact-review` — Blast-radius review of unreviewed change records
- `/specflow-audit` — Full-project health review with deterministic core + adversarial wings
- `/specflow-ship` — Baseline creation, DEC trail, quick audit, advisory gate
- `/specflow-pack-author` — Standards compliance pack authoring from PDF/URL/text
- `/specflow-adapter` — CI setup, exchange (ReqIF), standards ingestion, team RBAC

**CLI Commands (30 subcommands)**
- Discover: `init`, `status`, `standards gaps`
- Plan: `create`, `update`
- Execute: `go`, `done`, `generate-tests`
- Review: `artifact-lint`, `checklist-run`, `artifact-review`, `project-audit`, `trace`
- Release: `baseline create`, `baseline diff`, `document-changes`, `change-impact`, `fingerprint-refresh`
- CI: `hook install`, `hook pre-commit`, `ci generate`, `ci-gate`
- Data: `import`, `export`
- Hygiene: `detect dead-code`, `detect similarity`, `renumber-drafts`
- Recovery: `unlock`, `locks`, `rebuild-index`, `split`, `merge`

**Validation Engine**
- Zero-token deterministic validation: schema, links, status, IDs, fingerprints, acceptance, conflicts, coverage, chain depth, quality
- Requirements quality scoring with INCOSE/EARS-based checks (ambiguity, passive voice, missing measurability, compound requirements)
- Artifact lint with `--method programmatic` (CI) and `--method llm` (AI-judged)
- Gate validation for phase transitions

**Traceability**
- V-model traceability: REQ → ARCH → DDD → UT/IT/QT
- Impact analysis with suspect flags and fingerprint-based change detection
- Enhanced trace command with chain depth reporting
- Coverage metrics: REQ coverage, story test coverage, chain completeness

**Compliance**
- Standards pack architecture with gap analysis
- ReqIF 1.2 import/export for supply-chain interchange (deterministic UUIDs)
- Immutable baselines with diff comparison
- LLM-assisted pack authoring from PDF, URL, or pasted text

**Team & Enterprise**
- Git-based RBAC with CODEOWNERS integration
- Pre-commit hooks for status transition validation
- CI gate for server-side RBAC checks
- Defect lifecycle with prevention pattern extraction
- Draft ID renumbering with cross-repo reference rewriting
- GitHub Actions CI workflow generation

**Intelligence**
- 3-tier deduplication: tag Jaccard + TF-IDF + LLM similarity
- Dead-code detection (AST-based) and similarity detection (token-based)
- Adversarial review techniques: devil's advocate, premortem, assumption surfacing, red/blue team
- V-model test stub generation with acceptance criteria extraction
- Artifact split and merge operations
- Phase closure with learned pattern extraction

**Platform Support**
- 14 AI coding platforms: Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, GitHub Copilot, Roo Code, QwenCoder, Kiro, KiloCoder, Codex, Trae, Junie
- Platform auto-detection during init
- Progressive disclosure skill architecture (SKILL.md + references/ + scripts/)

**Documentation**
- Getting started guide, lifecycle overview, command reference, CLI reference
- Architecture design reference, design decisions log
- Team setup guide, pack authoring guide, adapter authoring guide
- Skill standards document

### Changed
- Removed 8 deprecated CLI aliases in favor of unified subcommand structure
- Unified skill templates across all platforms
- Rewrote documentation for public-readiness

[1.6.4]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.6.4
[1.5.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.5.0
[1.4.1]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.4.1
[1.4.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.4.0
[1.3.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.3.0
[1.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.2.0
[1.1.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.1.0
[1.0.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.0.0
[0.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v0.2.0
