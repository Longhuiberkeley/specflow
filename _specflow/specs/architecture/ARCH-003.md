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
fingerprint: sha256:ee902ce1a49a
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
modified: '2026-04-21'
---


# Skill & Platform System

The skill system bridges the SpecFlow Python CLI with AI agent platforms through modular, self-contained skill directories. It follows the progressive disclosure pattern: minimal context always loaded, detailed references loaded on demand.

## Platform Support (14 Registered, 4 Instantiated in v0.2.0)

14 platforms are registered in `src/specflow/platforms.yaml` and known to
the platform-detection code in `lib/platform.py`. In the v0.2.0 repo, only
4 platform directories are actually instantiated (the "Instantiated"
column); the rest are dispatch targets that `specflow init` will scaffold
on demand when run in a consumer project that uses them.

| Platform | Directory | Registered | Instantiated in v0.2.0 |
|----------|-----------|------------|------------------------|
| Claude Code | `.claude/skills/` | ✅ | ✅ (Primary) |
| Gemini CLI | `.gemini/skills/` | ✅ | ✅ |
| OpenCode | `.opencode/skills/` | ✅ | ✅ |
| QwenCoder | `.qwen/skills/` | ✅ | ✅ |
| Cursor | `.cursor/skills/` | ✅ | — |
| Windsurf | `.windsurf/skills/` | ✅ | — |
| Cline | `.cline/skills/` | ✅ | — |
| GitHub Copilot | `.github/copilot/skills/` | ✅ | — |
| Roo Code | `.roo/skills/` | ✅ | — |
| Kiro | `.kiro/skills/` | ✅ | — |
| KiloCoder | `.kilocoder/skills/` | ✅ | — |
| Codex | `.codex/skills/` | ✅ | — |
| Trae | `.trae/skills/` | ✅ | — |
| Junie | `.junie/skills/` | ✅ | — |

Platform auto-detection during `specflow init` scans for these directories.

## Skill Inventory (10 Tier-1 Skills)

| Skill | Purpose | CLI Backend |
|-------|---------|-------------|
| `/specflow-init` | Bootstrap project, install skills, optional CI | `specflow init` |
| `/specflow-discover` | Progressive disclosure requirement capture | `specflow create --type requirement` |
| `/specflow-plan` | Architecture proposal, DDD creation, SPIDR story decomposition | `specflow create --type architecture`, `create --type story` |
| `/specflow-execute` | Wave-based story implementation with status updates | `specflow go`, `specflow done`, `specflow generate-tests` |
| `/specflow-artifact-review` | Lint + checklists + LLM judgment + adversarial lenses | `specflow artifact-lint`, `specflow checklist-run`, `specflow artifact-review` |
| `/specflow-change-impact-review` | Blast-radius review of unreviewed change records | `specflow change-impact` |
| `/specflow-audit` | Full-project health review (deterministic core + adversarial wings) | `specflow project-audit` |
| `/specflow-ship` | Baseline creation, DEC trail, quick audit, advisory gate | `specflow baseline create`, `specflow document-changes`, `specflow project-audit --quick` |
| `/specflow-pack-author` | Standards compliance pack authoring from PDF/URL/text | `specflow create --type standard` (indirect) |
| `/specflow-adapter` | CI setup, exchange (ReqIF), standards ingestion, team RBAC | `specflow ci generate`, `specflow hook install`, `specflow import/export` |

## Skill Anatomy

Each skill is a directory containing:

```
specflow-discover/
├── SKILL.md              # Required: Core instructions and triggers (<500 lines)
├── references/           # Optional: Domain knowledge loaded ON DEMAND
│   ├── readiness-assessment.md
│   ├── domain-checklists/
│   │   ├── web-app.md
│   │   ├── cli-tool.md
│   │   ├── api-service.md
│   │   ├── embedded.md
│   │   └── mobile.md
│   ├── normative-language.md
│   ├── spidr-decomposition.md
│   └── cross-cutting.md
└── scripts/              # Optional: Zero-token deterministic operations
```

### `SKILL.md` (The Core)
- **Frontmatter**: `name` and `description` in YAML
- **Description**: The ONLY thing the agent reads to decide whether to trigger
- **Body**: Imperative, high-level workflow instructions. Under 500 lines.
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

All 14 registered platforms share the same skill content via `src/specflow/templates/skills/shared/`:
- `specflow-init/SKILL.md`
- `specflow-discover/SKILL.md` + `references/`
- `specflow-plan/SKILL.md`
- `specflow-execute/SKILL.md`
- `specflow-artifact-review/SKILL.md`
- `specflow-change-impact-review/SKILL.md`
- `specflow-audit/SKILL.md`
- `specflow-ship/SKILL.md`
- `specflow-pack-author/SKILL.md`
- `specflow-adapter/SKILL.md`

Platform-specific wrappers (e.g., `.claude/skills/`) are thin facades that reference the shared templates.

## Progressive Disclosure in Practice

### Always Loaded (~50 tokens)
The skill's YAML `description` field:
> "Use when the user wants to discover and specify requirements for a new feature."

### On Invocation (~500 tokens)
The `SKILL.md` body: Workflow steps, decision points, readiness criteria.

### On Demand (variable)
Files in `references/` loaded only when relevant:
- Domain checklists for project type
- Cross-cutting concern checklists
- SPIDR decomposition guides
- EARS quality guidance

### Zero-Token
Scripts in `scripts/` executed directly — no tokens consumed.

## Skill Standards Compliance

All skills conform to `docs/skill-standards.md`:
- SKILL.md under 500 lines
- `name` and `description` in frontmatter
- `references/` for domain knowledge (on-demand)
- `scripts/` for deterministic operations (zero-token)
- No explicit agent personas
- Single generalized agent handles everything
