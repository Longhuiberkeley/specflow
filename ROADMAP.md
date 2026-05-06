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

## v1.5.0

Focus: **unified thinking technique tracking and technique-to-BP feedback loop.**

- **Unified 16-lens adversarial catalog** — all 16 thinking techniques available in every lifecycle phase via shared reference at `.claude/skills/specflow-references/`; per-phase default sets and trigger-for-expansion guidance
- **Thinking technique records on artifacts** — `thinking_techniques` optional field on all 13 artifact types; `specflow update <ID> --thinking-techniques` flag for recording; lint warns on unchallenged approved specs
- **Generic lens fallback** — the 12 lenses without Python modules now run as generic LLM prompts, making all 16 lenses runnable from the CLI
- **Technique-to-BP feedback loop** — BP staleness checks include CHL artifacts; synthesis prompts inject recent adversarial findings so BPs learn from what lenses caught
- **Audit technique granularity** — audit CHLs carry per-axis names (`audit-horizontal`, `audit-vertical`, `audit-cross-cutting`) instead of monolithic `project-audit`

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
