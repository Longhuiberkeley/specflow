---
id: ARCH-003
title: Skill & Platform System
type: architecture
status: draft
priority: high
rationale: The skill system enables AI agents to perform SpecFlow workflows through
  modular, platform-specific skill files with progressive disclosure
tags:
- skills
- platform
- ai
- progressive-disclosure
suspect: false
fingerprint: sha256:14b81a2fe72b86d1f65df2fd9031d3a8fb315651abfa8e71c576327e0ecb108a
links:
- target: REQ-004
  role: derives_from
- target: REQ-005
  role: derives_from
created: 2026-04-10
checklists_applied:
- checklist: check-ARCH-003
  timestamp: '2026-04-11T13:45:49Z'
---


# Skill & Platform System

The skill system bridges the SpecFlow Python CLI with AI agent platforms through modular, self-contained skill directories.

## Platform Adapter Directories

Platform-specific directories at the project root:

```
.claude/                    # Claude Code adapter
└── skills/
    ├── specflow-discover/
    ├── specflow-plan/
    ├── specflow-execute/
    └── specflow-verify/

.gemini/                    # Gemini CLI adapter
└── skills/
    ├── specflow-discover/
    ├── specflow-plan/
    ├── specflow-execute/
    └── specflow-verify/

.opencode/                  # OpenCode adapter
└── skills/
    ├── specflow-discover/
    ├── specflow-plan/
    ├── specflow-execute/
    └── specflow-verify/
```

These directories are populated by `specflow init` based on platform detection. Skills are copied from `src/specflow/templates/skills/<platform>/`.

## Skill Anatomy

Each skill is a directory containing:

```
specflow-discover/
├── SKILL.md              # Required: Core instructions and triggers
├── references/           # Optional: Domain knowledge loaded ON DEMAND
│   ├── readiness-assessment.md
│   ├── domain-checklists/
│   │   ├── web-app.md
│   │   ├── cli-tool.md
│   │   └── api-service.md
│   └── cross-cutting.md
└── scripts/              # Optional: Zero-token deterministic operations
    └── create-artifact.sh
```

### `SKILL.md` (The Core)
- **Frontmatter**: Must contain `name` and `description` in YAML
- **Description**: The ONLY thing the agent reads to decide whether to trigger the skill. Must clearly state *when* to use it.
- **Body**: Imperative, high-level workflow instructions. Must be under 500 lines.
- **Single Agent Persona**: No explicit personas (PM, Architect). The skill guides the general agent to scale ceremony based on ambiguity.
- **Progressive Loading**: ~50 tokens at startup (description), full content loaded on skill invocation.

### `references/` (On-Demand Knowledge)
- Markdown files with detailed constraints, large checklists, or schema examples
- The `SKILL.md` instructs the agent *when* to read each reference file
- Example: "If the user is building a web app, read `references/domain-checklists/web-app.md`"
- Keeps the always-loaded context minimal while providing deep detail when needed

### `scripts/` (Zero-Token Operations)
- Executable shell or Python scripts for deterministic tasks
- **Rule**: If a task is deterministic, the AI MUST delegate it to a script rather than using LLM tokens
- Examples:
  - `create-artifact.sh` — creates a new artifact, assigns next ID, updates `_index.yaml`
  - `compute-fingerprint.sh` — SHA256 of artifact body (excludes frontmatter)
  - `validate-links.sh` — checks all link targets exist
- Scripts output clear, LLM-friendly stdout (e.g., `Success: Created REQ-006`)

## Skill Inventory

| Skill | Command | Purpose |
|-------|---------|---------|
| `specflow-discover` | `specflow-new` | Discovery conversation to elicit requirements |
| `specflow-plan` | `specflow-plan` | Architecture and story decomposition |
| `specflow-execute` | `specflow-go` | Parallel subagent orchestration for story waves |
| `specflow-verify` | `specflow-check` | Context-specific artifact review |

## Platform Detection Flow

During `specflow init`:
1. Scan project root for `.claude/`, `.gemini/`, `.opencode/`
2. If exactly one found → use it silently
3. If multiple found → prompt user to select
4. If none found → prompt user to select and create the directory
5. Copy all skill directories from `templates/skills/<platform>/` into the platform's skills directory

## Skill File Distribution

- **Source of truth**: `src/specflow/templates/skills/<platform>/` in the Python package
- **Installed copy**: Copied into the project's platform-specific skills directory during `specflow init`
- **Updates**: User re-runs `specflow init` to pick up new skill versions (prompts about overwriting)

## Progressive Disclosure in Practice

### Always Loaded (~50 tokens)
The skill's YAML `description` field:
> "Use when the user wants to discover and specify requirements for a new feature. Conducts a 3-phase discovery conversation and generates REQ artifacts."

### On Invocation (~500 tokens)
The `SKILL.md` body: Workflow steps, decision points, readiness assessment criteria.

### On Demand (variable)
Files in `references/` loaded only when the workflow determines they are relevant:
- Domain checklists for the user's project type
- Cross-cutting concern checklists
- SPIDR decomposition guides

### Zero-Token
Scripts in `scripts/` executed directly — no tokens consumed.

## Skill Standards Compliance

All skills conform to the SpecFlow Skill Standard defined in `docs/skill-standards.md`:
- SKILL.md under 500 lines
- `name` and `description` in frontmatter
- `references/` for domain knowledge (on-demand)
- `scripts/` for deterministic operations (zero-token)
- No explicit agent personas
- Single generalized agent handles everything, scaling ceremony to ambiguity
