# Changelog

All notable changes to SpecFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-04-22

### Added

- **Compliance evidence reports** (`specflow baseline create --evidence`) — generates a Markdown report alongside the baseline with traceability matrix, test results summary, baseline diff, and per-standard coverage scores (REQ-015, STORY-046)
- **Enhanced standards gap analysis** (`specflow standards gaps`) — coverage scoring (0–100%), severity-sorted gap list with priority tiebreak, rule-based remediation suggestions per category, summary dashboard, and `--json` flag for machine-readable output (REQ-016, STORY-047)
- **Optional artifact type schemas** (`specflow init --with-types hazard,risk,control`) — installable hazard, risk, and control artifact types with domain-specific fields, V-model lifecycle, and full create/trace/lint integration (REQ-017, STORY-048)

### Fixed

- `check_compliance()` now reports `total_clauses` consistent with the score denominator (previously diverged when malformed clauses were skipped)
- Project audit correctly detects ARCH and DDD refinements linked via `derives_from` (previously only matched `refined_by`, producing 10+ false-positive "no ARCH refinement" warnings)
- Public `baseline_dir()` API replaces private `_baseline_dir()` for cross-module use by evidence report generator

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

[0.3.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v0.3.0
[0.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v0.2.0
