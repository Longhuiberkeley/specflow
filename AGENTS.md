# AGENTS.md

## Welcome, AI Agents!

This repository contains the **SpecFlow** framework: a zero-database, filesystem-native, and scale-adaptive specification tracking tool designed to bridge agile workflows and ASPICE/ISO-compliant verification.

You are interacting with the framework's source code, NOT a project using the framework. Follow these guidelines while developing SpecFlow.

## Design Philosophy

### 1. The Repository IS the Database
Do not write logic that relies on a database. All specifications, work tracking, and states are managed via Markdown files with YAML frontmatter. The file tree is the ultimate source of truth.

### 2. Modeless & Scale-Adaptive
Ceremony adapts to ambiguity. SpecFlow has no "Tracks" (Quick/Standard/Enterprise) and no personas. 
When building features, assume a single generalized agent handles everything. If a user has a simple task, SpecFlow handles it with lean artifacts. If the task is complex, it scales up to full V-Model tracking. Avoid creating toggles, settings, or modes for this behavior.

### 3. Bring-Your-Own-Standard
SpecFlow does not ship with proprietary "Extension Packs" or gated industry standards. Instead, it relies on open YAML schema definitions. Users import their own standards (e.g., a PDF of ISO 26262 or an internal policy document), and SpecFlow parses them into executable compliance schemas.

### 4. Compliance as Code
We enforce compliance through CI/CD. Traceability matrices, linkage rules, and checklist requirements are validated locally by zero-token shell/Python scripts, not just by LLM inference. Ensure any new validation rule you add operates deterministically.

### 5. Context Efficiency (Skill Standards)
When writing AI skills for SpecFlow's internal agents (e.g., inside `.claude/skills/`), strictly adhere to the standards outlined in `docs/skill-standards.md`.
- Keep `SKILL.md` under 500 lines.
- Store domain knowledge in `references/`.
- Store deterministic operations in `scripts/`.

### 6. Ephemeral Local Execution (Like npx)
We do not install SpecFlow globally for users. Users will install it directly into their repository ephemerally using `uv run specflow init` to scaffold directories. Ensure scripts and instructions respect this local execution paradigm to avoid system-level pollution.

### 7. The User Interface Is CLI Skills
The user's primary interface to SpecFlow is **`/specflow-*` conversational skills** invoked inside their AI coding assistant (Claude, Cursor, Cline, etc.). Raw CLI commands like `specflow create` or `uv run specflow artifact-lint` are the deterministic backend that skills call under the hood — they are implementation details, not the user-facing product.

When writing documentation, tutorials, or onboarding material, emphasize skill-based workflows (`/specflow-discover`, `/specflow-plan`, `/specflow-execute`, `/specflow-audit`). Only mention raw CLI commands when explaining what a skill does internally or when providing CI/automation examples.

The install mechanism (`uv tool install`, `uvx`, `python -m specflow`) is our concern, not the user's. Once installed, the user thinks in terms of skills, not shell commands.


<!-- SpecFlow section (auto-generated, do not edit manually) -->
## SpecFlow

This project uses **SpecFlow** — a spec-driven development framework.
All specifications and work items are tracked as Markdown + YAML frontmatter.
The primary interface is `/specflow-*` slash commands in your AI assistant.

### Where Artifacts Live

- `_specflow/specs/` — V-model specification artifacts (requirements, architecture, design, tests)
- `_specflow/work/` — Agile delivery artifacts (stories, spikes, decisions, defects)
- `.specflow/` — Framework internals (config, schemas, impact log, baselines). **Do not edit manually.**

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/specflow-init` | Bootstrap project structure, install skills, optional CI |
| `/specflow-discover` | Capture requirements through guided conversation |
| `/specflow-plan` | Break approved REQs into architecture + stories |
| `/specflow-execute` | Implement stories with test generation |
| `/specflow-artifact-review` | Quality review of specific artifacts |
| `/specflow-change-impact-review` | Blast-radius review of recent commits/PRs |
| `/specflow-audit` | Full-project periodic health check |
| `/specflow-ship` | Release: baseline + change records + quick audit |
| `/specflow-pack-author` | Author a standards compliance pack |
| `/specflow-adapter` | Manage CI, exchange, standards ingestion, team RBAC |

### Skills vs CLI

| Interface | When to Use | Example |
|-----------|-------------|---------|
| **Skills** (`/specflow-*`) | Interactive work in your AI assistant | `/specflow-discover` |
| **CLI** (`specflow <cmd>`) | CI pipelines, automation, terminal | `specflow artifact-lint` |

Skills compose CLI commands internally. You can always use the CLI directly when you prefer the terminal or need automation.

### Lifecycle Flow

```
init → discover → plan → execute → artifact-review → ship
                                    ├── audit (periodic health check)
                                    ├── change-impact-review (per-commit/PR)
                                    └── adapter (CI, exchange, team setup)
```

### Artifact Status Lifecycle

When working with artifacts, **always update their status** as work progresses:

| Trigger | Action | Command |
|---------|--------|---------|
| Creating a new artifact | Set `status: draft` | `specflow create --type <type> --status draft` |
| User approves the artifact | Update to `status: approved` | `specflow update <ID> --status approved` |
| Code implementing the artifact is written | Update to `status: implemented` | `specflow update <ID> --status implemented` |
| Tests pass and review is complete | Update to `status: verified` | `specflow update <ID> --status verified` |

When implementing stories via `/specflow-execute`, also update linked ARCH and DDD artifacts to `implemented` once the code that realizes them is written. Do not wait for the story to be fully complete -- update spec status as the corresponding code lands.

### Working Principles

- **Trace before implement.** Every code change traces to a STORY or REQ. No orphan work.
- **Evidence over claims.** "Verified" means an artifact proves it — run the checks, don't assume.
- **State assumptions explicitly.** If uncertain, ask rather than silently picking an interpretation.
- **Fail early.** Run `specflow artifact-lint` after changes, not at release time.
- **Surgical changes.** Touch only what the request requires. Match existing conventions.
- **Label defaults.** When offering choices, mark the suggested option with "(Recommended)".
- **Escape hatches.** If the user says "move on" or "skip", proceed with what you have.

### Conventions

- Status flow: `draft` → `approved` → `implemented` → `verified`
- Stories link to specs via `links:` in YAML frontmatter
- `.specflow/` internals are managed by CLI commands — never edit manually
- Use `specflow update <ID>` for all status transitions and frontmatter changes
- Run `specflow artifact-lint` after creating or updating artifacts

<!-- End SpecFlow section -->
