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

## v0.3.2 (Current)

- **Prompt alignment** — updated Tier 1 slash commands (`init`, `ship`, `audit`) to leverage new `0.3.x` features (`--with-types`, `--evidence`, `standards gaps`)
- **Artifact validation fixes** — resolved schema and traceability gaps in the SpecFlow self-specification

## v0.3.1

- **Unified CLI Framework & Install UX** — streamlined installation path and tutorial, unified adapter framework, and command renaming
- **Skill Ecosystem Restructuring** — collapsed 22 skills to 8 Tier 1 conversational skills, rewrote skill prompts and documentation
- **Continuous Auditing** — added conversational scope and chunked fan-out for project audits
- **Convention Enforcement** — added project convention checklists to scaffold and enforce project structure

## v0.3.0

- **Compliance evidence reports** — `specflow baseline create --evidence` generates a Markdown report alongside the baseline with traceability matrix, test results summary, baseline diff, and per-standard coverage scores
- **Enhanced standards gap analysis** — `specflow standards gaps` now includes coverage scoring (0–100%), severity-sorted gap list with priority tiebreak, rule-based remediation suggestions per category, summary dashboard, and `--json` flag for machine-readable output
- **Optional artifact type schemas** — `specflow init --with-types hazard,risk,control` installs domain-specific artifact types (hazard, risk, control) with full create/trace/lint integration and V-model lifecycle

## v1.0.0 (Planned)

- **Review workflow artifacts** — structured `REVIEW-*` type with reviewer voting, threaded findings, and audit-grade approval evidence
- **Local visualization server** — `specflow serve` launches a dashboard at `localhost:5566` with interactive traceability graphs, coverage metrics, and baseline comparisons
- **Enhanced AI-assisted test generation** — richer UT/IT/QT stubs from REQ bodies with acceptance criteria extraction

## v1.x (Future)

- **Product variant management** — tag-based product line engineering for multi-trim / multi-variant projects
- **FMEA / risk analysis** — hazard, safety-goal, and risk-control artifact types via industry packs
- **Bidirectional Jira/Azure DevOps sync** — for teams bridging agile boards and compliance specs
- **REST API** — programmatic access for custom toolchain integration
