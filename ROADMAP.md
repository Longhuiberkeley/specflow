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

## v1.0.0 (Current)

Focus: **polish, stability, and adoptability.** Ship what we have with confidence.

- **Shared thinking techniques** — adversarial lenses extracted to a shared reference catalog, woven into discover and plan skills so requirements and architecture are challenged at creation time, not just at review time
- **Freeform skill input** — all skills accept natural language context (e.g., `/specflow-audit I'm worried about REQ coverage`) for scoped, directed workflows
- **Compliance summary in status** — `specflow status` shows per-pack compliance scores when standards are installed
- **Polished onboarding** — README rewrite with clearer visual hierarchy and disambiguation from similarly-named projects
- **Release process** — structured CHANGELOG, git tagging, and GitHub Release workflow documented in AGENTS.md
- **Test coverage boost** — expanded coverage on critical CLI paths (create, update, status, lint, audit)
- **Error message polish** — actionable CLI error messages across all commands

## v1.x (Future)

These may ship someday, but are not committed:

- **Product variant management** — tag-based product line engineering for multi-trim / multi-variant projects
- **FMEA / risk analysis** — hazard, safety-goal, and risk-control artifact types via industry packs
- **Bidirectional Jira/Azure DevOps sync** — for teams bridging agile boards and compliance specs
- **REST API** — programmatic access for custom toolchain integration
- **Static HTML export** — `specflow export --html` for zero-dependency dashboard generation
- **Review workflow artifacts** — structured `REVIEW-*` type with reviewer voting and threaded findings
- **Thinking technique records** — `thinking_techniques` field on artifacts tracking which lenses were applied
- **Multi-pack aggregated compliance** — unified compliance view across all installed standards
- **Compliance evidence quality** — validate that a `complies_with` link is backed by substantive content, not just link existence

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
