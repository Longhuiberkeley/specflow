---
id: ARCH-003
title: Skill & Platform System
type: architecture
status: implemented
priority: high
rationale: The skill system enables AI agents to perform SpecFlow workflows through
  modular, platform-specific skill files with progressive disclosure
tags:
- skills
- platform
- ai
- progressive-disclosure
suspect: false
fingerprint: sha256:223dcdd6c2e2
thinking_techniques:
- assumption_surfacing
- devils_advocate
links:
- target: REQ-004
  role: derives_from
- target: REQ-005
  role: derives_from
created: 2026-04-10
checklists_applied:
- checklist: check-ARCH-003
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-ARCH-003
  timestamp: '2026-04-14T17:03:22Z'
modified: '2026-10-08'
version: 4
---

# Skill & Platform System

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-027, R1-102); earlier text described a 14-platform registry at `src/specflow/platforms.yaml` including Gemini CLI, 10 skills, per-platform facades and a `create --type standard` pack-author backend.

The skill system bridges the SpecFlow Python CLI with AI agent platforms through modular, self-contained skill directories. It follows the progressive disclosure pattern: minimal context always loaded, detailed references loaded on demand.

## Platform Support (13 Registered)

13 platforms are registered in `src/specflow/templates/platforms.yaml` and loaded by `lib/platform.py` (`get_all_platforms()`, `detect_platform()`, `detect_platforms()`). Gemini CLI was retired (DEC-094). Each entry names the host's own `skills_dir`, the `instruction_file` that receives the injected SpecFlow context, `detection` markers, and optional `legacy_dirs`. `specflow init` installs skills into the directory returned by `platform.get_skills_install_dir()`, which is not always the host's own `skills_dir`: OpenCode already reads `.claude/skills`, so SpecFlow installs there for it, and hosts that declare the same `skills_dir` (Codex and Junie) share one install.

| Platform | Registry key | `skills_dir` | SpecFlow skills installed to | `instruction_file` |
|----------|--------------|--------------|------------------------------|--------------------|
| Claude Code | `claude-code` | `.claude/skills` | `.claude/skills` | `AGENTS.md` |
| Cursor | `cursor` | `.cursor/skills` | `.cursor/skills` | `.cursor/rules/specflow.md` |
| Windsurf | `windsurf` | `.windsurf/skills` | `.windsurf/skills` | `.windsurf/rules/specflow.md` |
| Cline | `cline` | `.cline/skills` | `.cline/skills` | `.clinerules/specflow.md` |
| OpenCode | `opencode` | `.opencode/skills` | `.claude/skills` (OpenCode reads it) | `AGENTS.md` |
| GitHub Copilot | `github-copilot` | `.github/skills` | `.github/skills` | `.github/copilot-instructions.md` |
| Roo Code | `roo` | `.roo/skills` | `.roo/skills` | `.roo/rules/specflow.md` |
| QwenCoder | `qwen` | `.qwen/skills` | `.qwen/skills` | `.qwen/rules/specflow.md` |
| Kiro | `kiro` | `.kiro/skills` | `.kiro/skills` | `.kiro/steering/specflow.md` |
| KiloCoder | `kilocode` | `.kilocode/skills` | `.kilocode/skills` | `.kilocode/rules/specflow.md` |
| Codex | `codex` | `.agents/skills` | `.agents/skills` (shared with Junie) | `AGENTS.md` |
| Trae | `trae` | `.trae/skills` | `.trae/skills` | `.trae/rules/specflow.md` |
| Junie | `junie` | `.agents/skills` | `.agents/skills` (shared with Codex; one install) | `AGENTS.md` |

Platform auto-detection during `specflow init` scans for each entry's `detection` markers (for example `.claude/`, `.cursor/`).

## Skill Inventory (12 Core Skills)

| Skill | Purpose | CLI Backend |
|-------|---------|-------------|
| `/specflow-init` | Bootstrap project, install skills, optional CI | `specflow init`, `specflow refresh`, `specflow practices seed`, `specflow ci generate`, `specflow hook install` |
| `/specflow-discover` | Shape a fuzzy idea; author or revise REQs | `specflow create`, `specflow update`, `specflow approve`, `specflow phase-set`, `specflow standards gaps` |
| `/specflow-plan` | Decompose approved REQs into ARCH/DDD/STORY | `specflow create`, `specflow update`, `specflow artifact-lint`, `specflow go`, `specflow risk-tier` |
| `/specflow-execute` | Implement approved STORYs with status updates | `specflow go`, `specflow update`, `specflow artifact-lint`, `specflow verify`, `specflow done`, `specflow generate-tests` |
| `/specflow-artifact-review` | Lint + checklists + agent judgment + thinking-technique lenses | `specflow artifact-review`, `specflow checklist-run`, `specflow update`, `specflow fingerprint-refresh` |
| `/specflow-change-impact-review` | Blast-radius review of recent DECs | `specflow change-impact`, `specflow detect stale-docs`, `specflow update` |
| `/specflow-audit` | Whole-project health review producing AUD and CHL | `specflow project-audit`, `specflow findings-baseline`, `specflow rtm`, `specflow standards gaps`, `specflow detect orphan-code` |
| `/specflow-ship` | Baseline, change records, audit, release summary | `specflow project-audit --quick`, `specflow baseline create`, `specflow document-changes`, `specflow findings-baseline update`, `specflow verify` |
| `/specflow-pack-author` | Standards compliance pack authoring from PDF/URL/text | `specflow pack-validate`, `specflow create --from-standard`, `specflow standards gaps`, `specflow refresh --packs` |
| `/specflow-adapter` | CI setup, exchange (ReqIF), team RBAC, post-upgrade refresh | `specflow ci generate`, `specflow hook install`, `specflow import`/`export`, `specflow refresh` |
| `/specflow-doc` | Cite specs from docs, find stale docs, keep decisions in artifacts | `specflow detect stale-docs`, `specflow brief`, `specflow project-audit` |
| `/specflow-start` | Router when the next step is unknown | `specflow brief --next` |

The shipped tree also holds `specflow-references/`, a support directory of shared `references/` files (no `SKILL.md`). `platform.get_skill_names()` lists the 12 skills.

## Skill Anatomy

Each skill is a directory containing:

```
specflow-discover/
├── SKILL.md              # Required: Core instructions and triggers (lean router; budgeted, see below)
└── references/           # Optional: Domain knowledge loaded ON DEMAND
    ├── readiness-assessment.md
    ├── domain-checklists/
    │   ├── web-app.md
    │   ├── cli-tool.md
    │   ├── api-service.md
    │   ├── data-pipeline.md
    │   ├── embedded.md
    │   ├── library.md
    │   ├── ml.md
    │   ├── mobile.md
    │   └── quant.md
    ├── conflict-check.md
    ├── cross-cutting.md
    ├── framing.md
    ├── level-boundaries.md
    ├── normative-language.md
    └── thinking-techniques.md

specflow-pack-author/
└── scripts/              # Optional: Zero-token deterministic operations (validate-pack.sh)
```

### `SKILL.md` (The Core)
- **Frontmatter**: `name` and `description` in YAML
- **Description**: The ONLY thing the agent reads to decide whether to trigger
- **Body**: Imperative, high-level workflow instructions. DEC-083 sets the outer cap at 500 lines; the enforced budgets are 120 lines for core skills and 300 for pack skills, with named per-file ceilings that may only shrink (tests/test_reference_lint.py).
- **Single Agent Persona**: No explicit personas. One generalized agent scales ceremony to ambiguity.
- **Progressive Loading**: ~50 tokens at startup, full content on invocation.

### `references/` (On-Demand Knowledge)
- Markdown files with detailed constraints, large checklists, schema examples
- Loaded only when the workflow determines relevance
- Keeps always-loaded context minimal

### `scripts/` (Zero-Token Operations)
- Executable shell or Python scripts for deterministic tasks
- Rule: If deterministic, the AI MUST delegate to a script

## Unified Skill Templates

All 13 registered platforms share the same skill content via `src/specflow/templates/skills/shared/`:
- `specflow-init/SKILL.md`
- `specflow-discover/SKILL.md` + `references/`
- `specflow-plan/SKILL.md`
- `specflow-execute/SKILL.md`
- `specflow-artifact-review/SKILL.md`
- `specflow-change-impact-review/SKILL.md`
- `specflow-audit/SKILL.md`
- `specflow-ship/SKILL.md`
- `specflow-pack-author/SKILL.md` + `scripts/`
- `specflow-adapter/SKILL.md`
- `specflow-doc/SKILL.md`
- `specflow-start/SKILL.md`
- `specflow-references/references/` (support files, no `SKILL.md`)

There are no per-platform facades: `init` (`commands/init.py:_install_skills`) copies every directory of the shared tree whole into the platform's install directory, replacing any existing copy.

## Progressive Disclosure in Practice

### Always Loaded (~50 tokens)
The skill's YAML `description` field:
> "Shape a fuzzy idea, or author/revise REQs when the requested change has no approved requirements yet, or rewind to requirements."

### On Invocation (~500 tokens)
The `SKILL.md` body: Workflow steps, decision points, readiness criteria.

### On Demand (variable)
Files in `references/` loaded only when relevant:
- Domain checklists for project type
- Cross-cutting concern checklists
- Framing and level-boundary guides
- Normative-language (EARS) guidance

### Zero-Token
Scripts in `scripts/` executed directly — no tokens consumed.

## Interface

The skill system exposes a uniform interface through `/specflow-*` skill invocations in AI agent platforms and the `specflow` CLI backend.

## Component

Each skill is a self-contained directory (SKILL.md + optional references/ + optional scripts/) installed for all 13 registered platforms from the shared templates in `src/specflow/templates/skills/shared/`.

## Responsibility

- SKILL.md: workflow instructions and trigger conditions (lean router within the enforced line budget)
- references/: on-demand domain knowledge loaded only when relevant
- scripts/: zero-token deterministic operations delegated to shell/Python

## Data Flow

User invokes skill → platform loads SKILL.md description (~50 tokens) → on invocation loads full SKILL.md body (~500 tokens) → on demand loads references/ → delegates deterministic work to scripts/.

## Dependencies

- `src/specflow/templates/platforms.yaml` — platform registry
- `lib/platform.py` — platform detection and skills install-directory resolution
- `src/specflow/templates/skills/shared/` — unified skill content

## Skill Standards Compliance

All skills conform to `docs/skill-standards.md`:
- SKILL.md within the enforced line budget (120 core / 300 pack; 500 outer cap per DEC-083)
- `name` and `description` in frontmatter
- `references/` for domain knowledge (on-demand)
- `scripts/` for deterministic operations (zero-token)
- No explicit agent personas
- Single generalized agent handles everything
