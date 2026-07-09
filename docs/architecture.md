# SpecFlow — Architecture

## Two-Axis Artifact Model

SpecFlow separates specification (persistent truth about what the system IS) from work (narrative context about what happened and why).

### Specification axis (V-model)

Left side describes the system. Right side verifies it. Each level pairs with its verification counterpart via `verified_by` links.

```
specs/
├── requirements/        # SWE.1: WHAT must the system do? (prefix: REQ)
├── architecture/        # SWE.2: HOW is the system structured? (prefix: ARCH)
├── detailed-design/     # SWE.3: HOW does each part work internally? (prefix: DDD)
├── unit-tests/          # SWE.4: Verifies DDD (prefix: UT)
├── integration-tests/   # SWE.5: Verifies ARCH (prefix: IT)
└── qualification-tests/ # SWE.6: Verifies REQ (prefix: QT)
```

V-model pairing:
- `REQ-001` <-> `QT-001` (verified_by)
- `ARCH-001` <-> `IT-001` (verified_by)
- `DDD-001` <-> `UT-001` (verified_by)

> **Coverage is measured two ways, by design (REQ-012).** `find_missing_v_pairs` checks the SPEC-anchored pair above (every REQ/ARCH/DDD has its QT/IT/UT). `check_coverage` checks STORY test coverage (every implemented STORY has UT+IT+QT linked). These are two distinct metrics — not a contradiction; do not "merge" them.

### Level boundary rules

| Level | Answers | Boundary test | Forbidden content |
|-------|---------|---------------|-------------------|
| REQ (system) | WHAT must the system do? | Can a non-technical stakeholder verify this? | Implementation, technology, "how" |
| ARCH (module) | HOW is the system structured? | Does this define interfaces between components? | User-facing behavior, code-level detail |
| DDD (unit) | HOW does each part work internally? | Can a developer write the code without ambiguity? | System-level concerns, user stories |

### Work axis (agile delivery + narrative)

```
work/
├── stories/       # Units of deliverable user value (prefix: STORY)
├── spikes/        # Research/investigation tasks (prefix: SPIKE)
├── decisions/     # Narrative records + ADRs (prefix: DEC)
└── defects/       # Bug tracking (prefix: DEF)
```

A story REFERENCES spec artifacts — it doesn't replace them:

```yaml
links:
  - target: REQ-001
    role: implements
  - target: ARCH-001
    role: guided_by
  - target: DDD-001
    role: specified_by
```

### Hierarchical decomposition within levels

Dot notation for within-level decomposition (max depth 3):

```
REQ-001          # Top-level: "User Authentication"
REQ-001.1        # Sub-requirement: "OAuth 2.0 Flow"
REQ-001.2        # Sub-requirement: "Session Management"
REQ-001.1.1      # Max depth: "PKCE Token Exchange"
```

Rules:
1. Maximum depth of 3 levels. Anything deeper becomes a separate artifact with a `refined_by` link.
2. Dots decompose within a level; links cross levels.
3. Children inherit parent's `type` and `tags` by default (overridable). Parent status cannot become `verified` until all children are `verified`.

## Directory Structure

Three distinct zones:

```
project/
├── .specflow/                    # Hidden: framework machinery
│   ├── config.yaml               # Framework configuration
│   ├── state.yaml                # Workflow state, current phase
│   ├── schema/                   # Artifact type definitions
│   │   ├── requirement.yaml
│   │   ├── architecture.yaml
│   │   ├── detailed-design.yaml
│   │   ├── unit-test.yaml
│   │   ├── integration-test.yaml
│   │   ├── qualification-test.yaml
│   │   ├── story.yaml
│   │   ├── spike.yaml
│   │   ├── decision.yaml
│   │   └── defect.yaml
│   ├── impact-log/               # One file per event, artifact-first naming
│   │   ├── REQ-001_2026-03-20T14-30-00Z.yaml
│   │   └── ARCH-001_2026-03-22T10-00-00Z.yaml
│   ├── checklist-log/            # One file per execution, timestamp-first naming
│   │   ├── 2026-03-20T14-30-00Z_CKL-GATE-002.yaml
│   │   └── 2026-03-22T10-00-00Z_CKL-HTTP-001.yaml
│   ├── checklists/               # Checklist definitions (copied during init, grows over time)
│   │   ├── phase-gates/          # Pre-task: entry criteria between phases
│   │   ├── in-process/           # Writing constraints during artifact generation
│   │   ├── review/               # Post-task: validation before user sees output
│   │   ├── readiness/            # Discovery/planning readiness assessments
│   │   ├── shared/               # Auto-matched by tags/types (user-extensible)
│   │   └── learned/              # Prevention patterns extracted from past work
│   ├── baselines/                # One file per baseline, immutable
│   │   ├── v1.0.yaml
│   │   └── v2.0.yaml
│   ├── standards/                # Imported standards (populated via PDF ingestion)
│   └── locks/                    # Parallel execution locks
├── _specflow/                    # Visible: all user-facing artifacts
│   ├── specs/                    # V-model specification artifacts
│   │   ├── requirements/         # REQ-*
│   │   ├── architecture/         # ARCH-*
│   │   ├── detailed-design/      # DDD-*
│   │   ├── unit-tests/           # UT-*
│   │   ├── integration-tests/    # IT-*
│   │   └── qualification-tests/  # QT-*
│   └── work/                     # Agile delivery & narrative
│       ├── stories/              # STORY-*
│       ├── spikes/               # SPIKE-*
│       ├── defects/              # DEF-*
│       └── decisions/            # DEC-*
├── src/                          # Project source code
├── AGENTS.md                     # Universal instructions (appended by init)
└── .claude/                      # Platform adapter (or .opencode/, .gemini/)
    └── skills/
        ├── specflow-init/
        ├── specflow-discover/
        ├── specflow-plan/
        ├── specflow-execute/
        ├── specflow-artifact-review/
        ├── specflow-change-impact-review/
        ├── specflow-audit/
        ├── specflow-ship/
        ├── specflow-pack-author/
        └── specflow-adapter/
```

### Framework vs. project instance

The **framework** (Python package) ships scripts, templates, and checklists. During `specflow init`, templates are copied into the **project instance**:

| Framework (ships with package) | Project instance (created by init) |
|-------------------------------|-----------------------------------|
| `src/specflow/templates/schemas/` | `.specflow/schema/` |
| `src/specflow/templates/checklists/` | `.specflow/checklists/` (phase-gates, in-process, review, readiness) |
| `src/specflow/templates/skills/<platform>/` | `.claude/skills/` (or `.gemini/`, `.opencode/`) |
| `scripts/` (thin CI/CD wrappers) | — (delegate to `specflow artifact-lint`, not copied) |

After init, per-project checklists grow:
- `.specflow/checklists/shared/` — user-defined, auto-matched by tags
- `.specflow/checklists/learned/` — extracted from completed work by the reactive challenge engine

## Artifact Format

Every artifact is a Markdown file with YAML frontmatter:

```markdown
---
id: REQ-001
title: User Authentication
type: functional
status: approved
priority: high
version: 3
rationale: "Security compliance requires authentication"
links:
  - target: ARCH-001
    role: refined_by
  - target: QT-001
    role: verified_by
tags: [security, auth]
suspect: false
fingerprint: "sha256:a1b2c3..."
checklists_applied:
  - checklist: CKL-GATE-002
    result: passed
    timestamp: 2026-03-20T14:30:00Z
created: 2026-01-15
modified: 2026-03-20
---

# User Authentication

The system **shall** require all users to authenticate before accessing
protected resources.

## Acceptance Criteria

1. Given valid credentials, the system grants access within 2 seconds
2. Given 3 failed attempts, the account locks for 15 minutes
3. Given an expired session, the system redirects to login
```

### Status lifecycle

```
draft -> approved -> implemented -> verified
```

Transitions enforced by validation scripts. Status meanings:
- `draft`: work in progress, not yet reviewed
- `approved`: reviewed and accepted, ready for downstream work
- `implemented`: code exists, awaiting verification
- `verified`: corresponding test level confirms compliance

Terminal states retire an artifact without deleting it (lifecycle is a status, never a
link role):
- `superseded`: replaced by a successor that links back with `supersedes`
- `cancelled`: terminated outright — no replacement
- `deprecated`: still valid but discouraged; don't build on it

## Link Role Vocabulary

The role vocabulary is **frozen and behavior-paired**: a role exists only when a query or
validation consumes it (see `docs/decisions.md`). New domains add roles through packs, not
ad-hoc — unknown roles lint to a warning with a suggested canonical equivalent, never a hard
error. The `mitigates` / `satisfies` rows below are contributed by the safety/ISO-26262 pack
and are absent from core schemas unless that pack is active.

| Role | Direction | Meaning |
|------|-----------|---------|
| `derives_from` | upstream | This artifact was derived from the target |
| `refined_by` | downstream | This artifact is refined by the target (cross-level) |
| `verified_by` | cross-axis | This spec artifact is verified by the target test artifact |
| `implements` | work -> spec | This story implements the target requirement |
| `guided_by` | work -> spec | This story follows the target architecture |
| `specified_by` | work -> spec | This story implements the target detailed design |
| `validated_by` | spec -> checklist | This artifact was validated by the target checklist |
| `complies_with` | spec -> standard | This artifact satisfies the target standard clause |
| `mitigates` | safety | This safety goal mitigates the target hazard |
| `satisfies` | safety | This safety requirement satisfies the target safety goal |
| `fails_to_meet` | defect -> spec | This defect shows the target requirement is not met |
| `addresses` | CR -> defect/spec | This change request addresses the target |
| `executes` | test-run -> test | This test run executes the target test artifact |

Links are stored once and traversed both directions, so there are **no inverse roles**
(`superseded_by`, `implemented_by`, …). To see what points *at* an artifact, query backlinks
with `specflow trace <ID>` — it walks both upstream and downstream.

## Code Realization (D-20)

Code is linked to specs via the `output_files` frontmatter field on **ARCH** and **DDD** (and on
STORY for forward action). The
`output_files` value is a list of file paths and/or glob patterns. Globs are expanded through
`specflow.lib.files.expand_output_files`, which is the single source of truth shared by the
orphan meter, the reconcile command, and the source-drift lint check — so a package glob in
any artifact is honored uniformly:

```yaml
# One ARCH covers a whole package
links:
  - target: REQ-007
    role: derives_from
output_files:
  - "src/main/java/com/acme/payments/**/*.java"
```

| Artifact | Carries `output_files`? | When |
|----------|--------------------------|------|
| **REQ**  | no (behavioral) | Code refs don't belong here — use ARCH |
| **ARCH** | yes (component custody) | Adoption: one per component, typically a package glob |
| **DDD**  | yes (internals) | Adoption: finer-grained file set for the detail |
| **STORY** | yes (forward action) | Forward work: subset of files the change touches |
| **UT/IT/QT** | (rarely) | An executable test targeting specific files |

**Adoption rule (D-20):** backfilled artifacts are tagged `backfilled`; backfilled code is
linked via ARCH/DDD `output_files` only — adoption creates zero STORYs. STORY is reserved
for forward action and appears only when someone changes adopted code, `specified_by` the
existing ARCH.

**Why globs:** on a 200k-LOC monorepo, one ARCH with `src/main/java/com/acme/payments/**/*.java`
in its `output_files` covers hundreds of files in a single entry — feasible, reviewable, and
credited in every downstream view. A bare file list would not be.

## Checklist System

Three layers at every phase:

### Layer 1: Pre-task (phase gates)

Entry criteria checklists between every phase transition. Catch missing inputs, unresolved issues, and readiness gaps before work begins. Stored in `.specflow/checklists/phase-gates/`.

### Layer 2: In-process (writing constraints)

Constraint checklists loaded while generating or reviewing artifacts. Enforce level boundaries, normative language, interface completeness. Stored in `.specflow/checklists/in-process/`.

### Layer 3: Post-task (review)

Validate generated output before the user sees it. Assembled from artifact type + domain tags + shared checklists + learned patterns. Stored in `.specflow/checklists/review/`.

### Automated vs agent-judged

Every checklist item declares `automated: true|false`:
- **Automated** (zero tokens): verified by Python CLI (schema, links, status, fingerprints)
- **Agent-judged** (host agent intelligence): requires reasoning (quality, ambiguity, contradiction)

CI runs automated checks first. Agent-judged checks are displayed for the host agent to evaluate — fully self-contained, no external API calls.

### Checklist file format

```yaml
id: CKL-GATE-002
name: "Requirements to Planning Gate"
phase_from: specifying
phase_to: planning
version: 1

items:
  - id: CKL-GATE-002-01
    check: "All REQ-* artifacts have status: approved"
    automated: true
    script: "uv run specflow artifact-lint --type status"
    severity: blocking

  - id: CKL-GATE-002-02
    check: "Non-functional requirements are quantified"
    automated: false
    llm_prompt: "Review each REQ tagged 'nonfunctional'. Flag qualitative terms without measurable thresholds."
    severity: warning
```

Severity levels: `blocking` (must fix), `warning` (should fix), `info` (nice to know).

### Shared checklists

Defined once in `.specflow/checklists/shared/`, auto-matched to artifacts by `applies_to` tags and types:

```yaml
id: CKL-HTTP-001
name: "HTTP Client Requirements"
applies_to:
  tags: [http, api-client, web-scraping]
  types: [story, detailed-design]
```

### Checklist traceability

Per-artifact (in frontmatter `checklists_applied`) and global audit log (`.specflow/checklist-log/`, one file per execution).

## Commands

### Conversational commands (agent-driven)

These are the **primary user interface** — skill file invocations via `/specflow-*` commands in the AI coding tool. The agent follows structured SKILL.md workflows, calls Python CLI commands for validation, and conducts conversations with the user. See D-17.

| Command | Skill directory | What it does |
|---------|----------------|-------------|
| `/specflow-init` | `specflow-init/` | Bootstrap project: scaffolds directories, installs skills, optional CI and standards packs. |
| `/specflow-discover` | `specflow-discover/` | Discovery conversation (3-phase progressive disclosure with readiness assessment). Generates REQ artifacts. Adapts ceremony to ambiguity — bounded changes get lean artifacts automatically. |
| `/specflow-plan` | `specflow-plan/` | Architecture and story breakdown discussion. Proposes architecture, design, stories. Populates `specs/` and `work/`. |
| `/specflow-execute` | `specflow-execute/` | Orchestrates parallel subagent execution per story wave. Reports progress, handles locks, auto-commits per task. |
| `/specflow-artifact-review` | `specflow-artifact-review/` | Context-specific review. Assembles criteria from artifact type + domain tags + shared + learned checklists. Runs automated then agent-judged checks. |
| `/specflow-change-impact-review` | `specflow-change-impact-review/` | Blast-radius review of recent commits/PRs via unreviewed change records. Idempotent. |
| `/specflow-audit` | `specflow-audit/` | Full-project periodic health check. Deterministic core with optional adversarial wings. |
| `/specflow-ship` | `specflow-ship/` | Release workflow: immutable baseline, change records, quick audit. |
| `/specflow-pack-author` | `specflow-pack-author/` | LLM-assisted authoring of standards compliance packs from PDF, URL, or pasted text. |
| `/specflow-adapter` | `specflow-adapter/` | Manage CI workflows, import/export, standards ingestion, and team RBAC. |

### Programmatic commands (Python CLI, zero tokens)

All programmatic commands are `specflow <subcommand>` subcommands of the Python CLI. All logic lives in Python `lib/` modules. Shell scripts in `scripts/` are optional thin CI/CD wrappers that delegate to the CLI. See D-16.

| Command | What it does |
|---------|-------------|
| `specflow init` | Auto-detects platform, generates correct file structure |
| `specflow status` | Reads state, prints dashboard: current phase, flag counts, checklist warnings, suggested next action |
| `specflow artifact-lint` | Runs all validation checks: schema, links, status, IDs, fingerprints, acceptance, conflicts, coverage, quality |
| `specflow change-impact` | Reads fingerprints, prints flagged artifacts, change history, recommended review order |
| `specflow fingerprint-refresh` | Recompute fingerprint for minor edit without triggering suspect cascade |
| `specflow document-changes` | Synthesizes DEC artifact from git diffs + impact-log entries |
| `specflow standards gaps` | Gap analysis against imported standard clauses |
| `specflow baseline create` | Snapshot current state into immutable baseline YAML |
| `specflow baseline diff` | Compare two baselines |
| `specflow detect dead-code` | AST-based informational scan for declared-but-unreferenced functions/classes (exit 0 regardless of findings) |
| `specflow detect similarity` | Token-level informational scan for near-duplicate function bodies (exit 0 regardless of findings) |
| `specflow detect orphan-code` | Report source files not traced to any STORY/REQ/ARCH/DDD via `output_files` (literal paths + glob patterns). Reports coverage % and the biggest un-adopted cluster. `--retro-link <ID>` adopts them to a target artifact of any type. |
| `specflow adopt status` | Adoption completeness, derived from the graph: project/boundary dashboard (coverage %, per-ARCH depth + drift) or per-artifact view (realization, criteria, verification, provenance, gaps, drift). No state file — fully computed. |

### State machine

```
idle -> discovering -> specifying -> planning -> executing -> verifying -> complete
```

State persists in `.specflow/state.yaml` with history. `current` advances along this chain as work progresses: `specflow go` enters `executing`, the discover/plan skills record `specifying`/`planning`, and `specflow done` closes the current phase and advances `current` to the next (e.g. `planning` → `executing` → `verifying` → `complete`). Phase-gate checklists are consulted *advisory*-only (`specflow phase-status`) — they surface readiness, they do not block (accounting, not policing).

## Cross-Platform Strategy

Three compatibility tiers:

1. **Universal layer** — AGENTS.md. Pure Markdown, works everywhere. Appended during init (user chooses target file: AGENTS.md, CLAUDE.md, etc.).
2. **Portable skill layer** — SKILL.md format. Progressive loading: ~50 tokens at startup, full content on-demand.
3. **Platform-specific adapters** — Commands as Markdown (Claude Code/OpenCode). Generated by `uv run specflow init` based on detected platform. First-class support for Claude Code and OpenCode only.

## Token Optimization

Four strategies:

1. **Isolate** — Every major task gets a fresh context. Subagents receive only what they need, return condensed results.
2. **Select** — Hierarchical summarization: full content (~500 tokens/file) -> signatures (~100) -> one-liner (~10) -> directory summary (~5).
3. **Programmatic-first** — Zero-token tools (grep, AST, lint, git diff, SHA256, TF-IDF, local embeddings) before LLM calls.
4. **Compress** — Auto-compaction at 90% context capacity. Budget: system 15%, domain 10%, task 40%, tools 20%, history 10%, buffer 5%.

## Impact Analysis

### Fingerprint-based change detection

Each artifact stores a SHA256 fingerprint of its normative content (title + body, excluding metadata). When content changes, the fingerprint updates and downstream-linked artifacts get `suspect: true`.

### Typo cascade defense (3-tier)

1. **Explicit intent** — User adds `update_type: minor` in frontmatter for cosmetic edits. Framework skips cascade.
2. **`specflow fingerprint-refresh` command** — Convenience wrapper that recomputes an artifact's fingerprint (and logs the change as minor so it skips the suspect cascade).
3. **Magnitude heuristic** — Git-based fallback: if change ratio < 5% AND only frontmatter changed, auto-classify minor. Otherwise: always cascade.

Design principle: when in doubt, cascade.

### Impact-log format

One file per event, artifact-first naming for fast querying:

```
.specflow/impact-log/
├── REQ-001_2026-03-20T14-30-00Z.yaml
├── ARCH-001_2026-03-22T10-00-00Z.yaml
```

Each file:

```yaml
changed: REQ-001
change_type: content_modified
fingerprint_old: "sha256:abc..."
fingerprint_new: "sha256:def..."
flagged_suspects: [ARCH-001, DDD-001, DDD-002, UT-001]
resolved: false
```

## Duplicate Detection

Invoked via `specflow checklist-run --dedup` and as a search-before-create step inside `specflow create`. A three-tier pipeline escalates only as needed:

1. **Tag Jaccard** (Python, zero tokens) — filters artifact pairs by set similarity of `tags`.
2. **TF-IDF cosine** (Python, zero tokens, stdlib only) — filters survivors by keyword similarity on title + normative body.
3. **LLM confirmation** (agent, token cost) — the check skill reads the candidates file and asks the user to confirm/merge/ignore.

Surviving candidates are written to `.specflow/dedup-candidates.yaml` with tier scores and a confidence label. The file is advisory — the user decides whether to merge artifacts. `specflow create` runs tiers 1 and 2 against the proposed `{title, tags}` before writing the new file and warns on likely duplicates.

## Project Hygiene (detect commands)

Two informational subcommands analyze project source code. Neither blocks any workflow; both return exit code 0 regardless of findings.

- `specflow detect dead-code` walks Python ASTs in the configured source root, builds a declaration and call graph, and reports functions/classes declared but never referenced. Framework entry points are excluded: `[project.scripts]` / `[project.entry-points]` from `pyproject.toml`, `pytest` fixtures and `test_*` functions, symbols in `__all__`, and dunder methods.
- `specflow detect similarity` compares normalized token sequences across function bodies longer than a configurable minimum and reports pairs whose Jaccard similarity exceeds a threshold (default 0.9) with both file paths, line ranges, and similarity percentage.

## Change Management (Hybrid)

Git is the live record. Impact-log entries are automatic. Suspect flags are automatic. The `.md` CR artifact is only materialized on demand — before a PR, before a baseline, or when a compliance audit asks for it. The `.md` file is a projection of what git + impact-log already know, not a separate thing to maintain.

## Compliance as Code

SpecFlow proves compliance through automated, version-controlled mechanisms rather than manual paperwork. The framework treats the repository as the database:
- **Executable Schemas:** Requirements and architecture are Markdown files with strictly typed YAML frontmatter.
- **Zero-Token Validation:** Traceability matrices, linkage rules, and phase-gate checklists are validated locally by zero-token shell/Python scripts running in CI/CD pipelines, independent of LLM inference.
- **Cryptographic Fingerprints:** Changes automatically flag downstream impacts via SHA256 hashes.
- **On-Demand Reporting:** Final compliance reports are synthesized from Git history on demand, proving that "the code *is* the compliance."

## Baselines

One YAML file per baseline, stored in `.specflow/baselines/`, immutable after creation:

```yaml
name: v1.0
git_tag: v1.0
created: 2026-03-20
snapshot:
  REQ-001: { status: approved, fingerprint: "sha256:abc..." }
  ARCH-001: { status: approved, fingerprint: "sha256:def..." }
test_summary:
  UT: { total: 45, passed: 43, failed: 2 }
  IT: { total: 12, passed: 12, failed: 0 }
  QT: { total: 8, passed: 7, failed: 1 }
```
