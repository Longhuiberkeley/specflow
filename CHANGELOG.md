# Changelog

All notable changes to SpecFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[1.3.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.3.0
[1.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.2.0
[1.1.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.1.0
[1.0.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.0.0
[0.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v0.2.0
