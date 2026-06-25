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
- **Best Practice artifacts (BP-NNN)** — domain-specific best practices as first-class SpecFlow artifacts, agent-generated and traceable
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
- **Generic best-practice fallback** — agent generates domain BPs from its own knowledge; no API key required
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

## v1.10.0

Focus: **a "deployed-and-observed" memory class (ops pack) and auto-adaptive artifact guidance.**

- **Ops pack (RUN/MONITOR)** — a fifth memory class for live operations, alongside spec/work/review/research. **RUN** freezes a deployment at deploy-time (`deployed_ref`, `environment`, satisfying which REQ/ARCH/EXPT); **MONITOR** is an append-only timestamped observation journal (`metrics`, `signals`, `health`, `captures`). Domain-neutral schemas (`category: ops`) — drift/latency/sensor specifics live in per-domain maps, never the core. Reuses frozen link roles (`derives_from`/`belongs_to`/`informs`); no new roles. New `specflow-ops` skill (deploy + observe flows). See **D-21**.
- **Positioning — complement, not replacement.** RUN/MONITOR are a governance ledger / chain of custody that sits *above* the MLOps/GitOps toolchain: `deployed_ref` points at an MLflow / W&B / ArgoCD identifier; MONITOR records decision-grade observations, not the raw telemetry firehose. SpecFlow adds the *why-it's-live* and *what-we-did-about-it* those tools are weak on.
- **Auto-adaptive concept→artifact maps** — per-domain checklists (`quant.md`, `ml.md`) open with a Concept→Artifact Map; `discover`/`plan` surface it so "REQ vs STORY vs autoresearch goal vs RUN" is answered at decision time with the *why*. Packs contribute their own rows (autoresearch→COMP/EXPT; ops→RUN/MONITOR).
- **`specflow domain suggest`** — extensible signal→domain detection from dependency manifests (quant/ml seeded); pure read, never silently sets.
- **Pack-state-aware `brief --next`** — an optional second advisory line when an active subsystem has an actionable state (a running LOOP; a breached or unobserved live RUN).
- **Communication pack enriched** — `tldr-communication` 1.0.0→1.1.0: action-first directive (reader-model + constraints + rules + pre-send check), behaviourally framed, source credited; opt-in only, baseline context untouched.
- **Flowchart + discoverability** — `docs/lifecycle.md` flowchart (mermaid + ASCII) now shows the optional autoresearch/ops extensions and the EXPT→RUN→MONITOR→retrain loop; README gains an Ops section; `ops` added to `--preset` help.
- **+32 tests (553 total)**, live↔ship skill/checklist parity confirmed.

## v1.9.6

Focus: **functional briefing, multi-agent framing, routing, and batch approval** (shipped; CHANGELOG/ROADMAP backfilled in v1.10.0).

## v1.9.5

Focus: **source-scope engine, `.gitignore` respect, and quality-of-life fixes.**

- **Source-scope engine** — `scan_source_files` uses `git ls-files` (tracked ∪ untracked-not-ignored) inside work trees, with an opt-in `source_scope` config block (`include` allowlist bypassing the extension heuristic, `exclude` denylist, additive `extensions`). Orphan-meter denominator clamped to the scanned scope so coverage stays ≤100%. `adopt status` surfaces how "source" was scoped.
- **`create` stdin-hang guard** — `select.select(..., 0.0)` prevents blocking on a non-tty-but-idle stdin pipe. Duplicate-warning crash fix (`NameError: YELLOW`).
- **`detect` exit-code contract** — orphan findings now return 0 (informational), matching the documented promise.
- **`status` single discovery** — `discover_artifacts()` called once and passed to all helpers (5× → 1× scan).
- **Config cleanup** — removed unused `impact_analysis` keys, added `learning`/`lint`/`source_scope` defaults, fixed variable shadow.
- **ANSI standardization** — raw escape sequences replaced with `specflow.lib.display` constants across 8 commands.
- **`learning.py` public API** — internal helpers made public; all consumers updated.
- **Domain constants deduplicated** — new `lib/domain_constants.py` replaces inline copies.
- **`execute` trigger narrowing** — "DEFAULT for any code change" → "implementation path for planned stories".
- **Platform repositioning** — first-class Claude Code + OpenCode; OpenCode marked `preferred: true`.
- **Skill best-practices steps** — artifact-review, audit, change-impact-review, ship get a "Load Best Practices" step; ship adds thinking-technique lenses.
- **Schema sync + verification-gate + discover TT recording** — folded from v1.9.4 (schema `id_format` widened project-wide, execute verification-gate delta moved inside Step 6, discover records thinking techniques on REQs).
- **521 tests passing**, artifact-lint PASS (62 warnings), skill-template parity confirmed.

## v1.9.4

Focus: **data safety and CI hardening.**

- **`rebuild-index` fingerprint source-of-truth** — `create_artifact()` now writes `fingerprint` into `.md` frontmatter (not just `_index.yaml`), so fingerprints survive `rebuild_index()`. `rebuild_index()` warns before dropping index entries or erasing fingerprints instead of doing it silently. Root cause: `_render_artifact_file()` never received the computed fingerprint; `update_artifact()` already did this correctly.
- **`pytest` job in CI** — dogfood `.github/workflows/specflow.yml` now runs `uv run pytest tests/` as a blocking gate. GitHub Actions adapter includes `pytest` as an available `ci.operations` key for new projects.
- **Schema id\_format widening — project + skill-doc sync** — the `\d{3}`→`\d{3,5}` widening had only landed in shipped `templates/schemas/`. Regenerated the project's own `.specflow/schema/` from templates (it was a fossil — 10 files still `\d{3}`, three at `\d{3,4}`, only `story.yaml` current) and fixed the live `pack-author` reference doc that lagged its own template. Only `id_format` had drifted. Exposed a systemic gap (see Future).
- **Verification-gate step ordering** — the execute skill's verification-gate delta now runs *inside* Step 6 (Validation) before the exit/handoff message, instead of as an orphan "Step 6.5" placed after it; the exit message now reports the delta. The `AGENTS.md` / `agent-context.md` Evidence bullet was tightened to match sibling altitude.
- **`thinking_techniques` recorded at discovery** — the discover skill now records the lenses actually applied to each REQ via `update --thinking-techniques` (the plan skill already did this for ARCH/DDD). Closes the disconnect where the challenge step ran but left the field empty, inviting cosmetic backfill to satisfy lint.

## v1.9.1

Focus: **disciplined relationships — vocabulary stays frozen, drift gets named.**

- **Role normalizer** (`lib/role_normalize.py`) — `artifact-lint` turns the silent "Unknown link role" warning into a direction-aware suggestion: same-direction synonyms (`validates`→`validated_by`, `extends`→`refined_by`), inverse roles (`superseded_by`→author `supersedes`, or query `specflow trace`), and lifecycle "roles" that are really statuses (`cancels`→`status: cancelled`). Still a warning, never a blocker — accounting, not policing.
- **Terminal lifecycle statuses** — `cancelled` (terminated, no replacement) and `deprecated` (discouraged) added to requirement/architecture/detailed-design/story schemas; `cancelled` added to decision alongside the existing `superseded`. Gives "this artifact is dead" a real home instead of invented `cancelled_by` roles.
- **Backlink guidance** — `specflow trace` already walks upstream *and* downstream; documented as the answer to "what supersedes/implements/refines X?" so nobody hand-authors inverse roles. Link-role and architecture docs updated; resolved the `mitigates`/`satisfies` doc-vs-schema mismatch (pack-contributed, noted as such).
- **Design record (D-18)** — the link-role vocabulary is frozen and behavior-paired; inverses are queries, lifecycle is status, near-misses get normalized not blessed. The durable answer to "should we add 8 roles?" (no).

## v1.9.0

Focus: **self-contained engine — full retirement of external LLM use.**

- **Zero external API calls** — removed `call_llm`, `LLMConfig`, the OpenRouter client, and the Pass-2 workflow from `lib/ci.py`; SpecFlow now ships no LLM client of its own. All intelligence comes from the host harness (Claude Code, Codex, OpenCode, …); the deterministic/ALM lane runs with no agent and no API key.
- **Thinking techniques → prompt generators** — `build_prompt → TechniquePrompt`; `artifact-review --depth deep` emits the full system+user prompt for the host agent to apply.
- **CI fully self-contained** — workflow generator, static template, and dogfood `.github` workflow drop the Pass-2 job and `OPENROUTER_API_KEY` secret.
- **Removed:** `specflow handbook` command (+ `lib/handbook.py`, `lib/best_practices.py`), `artifact-review --fast`, the `ci.llm` config block. `artifact-lint --method llm` deprecated (falls through to programmatic). BPs are now first-class `BP-NNN` artifacts authored by the agent during discover/plan.
- **Orphan-code traceability lens** — `project-audit` (full mode) now flags source files not traced to any STORY/REQ via `output_files`, distinguishing "tracking not adopted" (info) from "files slipped through" (warn). Surfaced in the audit skill + docs alongside `specflow detect orphan-code --retro-link`.
- **Consistency** — installed skills (`.claude/skills`) reconciled byte-for-byte with shipped templates; "LLM-judged" → "agent-judged" terminology unified; docs "local check vs. agent review" spectrum guide added.

> Deferred: **auto-capture of `output_files` during execute/`done`** — the higher-value half of orphan-code traceability (makes detection actually fire). Held back as its own change because it's a behavior change to the execute path with real edge cases (renames, deletes, multi-story files). See *v1.x (Future)*.

## v1.8.0

Focus: **SpecFlow-as-memory, the suspect → DEF pipeline, and risk-proportional approval gates.**

- **`specflow brief`** — one-call deterministic recall digest (phase, inventory by category/status, open suspects, next wave, recent changes), so a fresh agent reconstructs project state in one command instead of a six-command ritual. Four-axis memory model (semantic/episodic/temporal/relational) documented in the always-loaded context.
- **Suspect → DEF pipeline** — `specflow defect-from-suspect <ID> --req <REQ>` creates a fully-traceable, indexed defect (`fails_to_meet` → REQ, `exposed_by` → suspect) from a suspect-flagged artifact; the helper now routes through `create_artifact` rather than a hand-rolled writer.
- **Risk-proportional approval gates** — per-change Risk Profile (reversibility, blast radius via `specflow change-impact`, AI confidence) and tiers (0 light / 1 normal / 2 stop) in the approval-presentation format; "no self-approval" enforced and scoped to the agent; discover lean path reconciled to confirm rather than silently auto-approve.
- **Spec-approval enforcement** (partial delivery of the planned *Stale Code Detection / Semantic Drift*) — new `story-linkage` lint and a now-blocking status-cascade check ("STORY beyond draft linked to a draft spec"), wired into the planning-to-executing gate.
- **Two ways to drive, one engine** — dual-mode positioning (AI-first default + standalone ALM, no API key) with a two-lane lifecycle flowchart (Mermaid + ASCII).

> Deferred from the original v1.8.0 plan: cost/token observability (`--dry-run` on fan-out skills + `.specflow/telemetry/`), the synthesis conflict-resolution rubric, the `specflow autoresearch review` dashboard, and proactive dogfooding enforcement. The full semantic-drift "stale on upstream change" lint remains partially open (suspect flags already cover ARCH/REQ modification; the explicit lint is future work).

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

- **Auto-capture `output_files` on execute/`done`** — record the source files a story produced as it's implemented, so `detect orphan-code` and `source-drift` work without manual `--retro-link`. The detection + audit surfacing shipped in v1.9.0; this is the capture half. Needs care around renames, deletions, and files shared across stories.
- **Continued skill ↔ template reconciliation / prompt tuning** — v1.9.0 made `.claude/skills` and `templates/skills/shared` byte-identical (richer-wins). Future skill-prompt edits should update both trees together (mirror live→ship); revisit if prompts need deeper tuning.
- **Schema sync for initialized projects** — template `schema/*.yaml` edits don't propagate to an existing project's `.specflow/schema/`; the only re-sync path today is `init --force` (which does far more than schemas). Surfaced in v1.9.4 when the `id_format` widening had not reached the dogfood project. Sequenced plan:
  1. **Drift lint (do first, low-risk)** — an `artifact-lint` check (`--type schema-drift`) that compares each `.specflow/schema/*.yaml` against the installed package template and *warns* on divergence. Non-destructive: surfaces staleness without touching files. Add a test.
  2. **`specflow sync-schema` (medium)** — explicit re-copy of templates into `.specflow/schema/` with `--dry-run`/diff preview. **Must preserve intentional per-project customizations** (e.g. custom `allowed_status`, extra fields) — a project owning/editing its own schema is a deliberate feature, so this cannot be a blind overwrite. Likely a field-level merge or a confirm-per-file flow.
  3. **Runtime read (large, maybe never)** — load schemas from the package at runtime and keep `.specflow/schema/` for overrides only. Most correct long-term, but an architectural shift.
  - *Related:* the same "duplicated value, no sync" shape caused the `pyproject.toml`↔`__init__.py` version drift fixed in v1.9.4; consider single-sourcing the version via `importlib.metadata` so it can't recur.
- **Ops adapter — monitoring → MONITOR ingestion** *(from v1.10.0 review)* — a webhook/CLI bridge that turns a monitoring-tool breach (Evidently / Arize / Prometheus alert / ArgoCD OutOfSync) into a `flagged` MONITOR via `specflow create --type monitor`. The CLI already *is* the API; this is the missing glue that plugs SpecFlow into a real MLOps/GitOps loop without manual entry. Belongs with the `specflow-adapter` family.
- **RUN deployment bill-of-materials** *(from v1.10.0 review)* — `deployed_ref` is single-valued; real deployments are a bundle (model + feature pipeline + config + infra revision). Handled today via multiple `derives_from` links, but a first-class multi-component reference (or a typed `components` list) would make "what exactly is live?" lossless.
- **RUN rollback / supersede link role** *(from v1.10.0 review)* — promotion/rollback is modelled today as a new RUN `derives_from` the prior + `retired` status, which can't distinguish a forward step from a rollback. Add a `supersedes`/`rolls_back_to` role only if `specflow trace` proves the ambiguity is real (per the D-18 frozen-vocabulary discipline).
- **`specflow packs` discovery command** *(from v1.10.0 review)* — list available + installed packs from the CLI (and a parallel mention in the init skill), so packs are discoverable without grepping docs or `--preset` help. Replaces hardcoding example pack names in help strings.
- **`brief --next` deployed-but-unobserved RUN** *(from v1.10.0 review)* — the unobserved-RUN note only fires for `status: live`; a RUN sitting in the `deployed` entry-state with no MONITOR is silently ignored. Fine today (the skill creates `--status live`), but a latent blind spot worth closing when ops sees real use.
- **Getting-started ops walkthrough** *(from v1.10.0 review)* — `docs/getting-started.md` has no hands-on ops/`domain suggest` path; the lifecycle flowchart now shows the loop but there's no tutorial for it.
- **Product variant management** — tag-based product line engineering for multi-trim / multi-variant projects
- **FMEA / risk analysis** — hazard, safety-goal, and risk-control artifact types via industry packs
- **REST API** — programmatic access for custom toolchain integration
- **Static HTML export** — `specflow export --html` for zero-dependency dashboard generation
- **Multi-pack aggregated compliance** — unified compliance view across all installed standards
- **Adoption pack (`/specflow-adopt`)** — bring an existing codebase into SpecFlow: inventory → backfill ARCH/DDD/REQ/DEC (tagged `backfilled`) → cut an as-built baseline → retro-link existing code → hand off to the normal lifecycle. ARCH-per-component code-linking via `output_files` globs, zero backfilled STORYs (STORY reserved for forward action), skeleton-first strategy, `specflow adopt status` completeness view (coverage %, per-ARCH boundary dashboard, per-artifact depth/gaps/drift). Incremental/resumable, conflict-surfacing, zero new Python. Opt-in pack (`/specflow-init --preset adoption`); greenfield projects don't need it. Implemented; see D-19 and D-20.

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
