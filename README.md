# SpecFlow

SpecFlow is a spec-driven development framework that unifies requirement capture, ASPICE-grade traceability, and context-efficient execution — all through conversational slash commands in your AI coding assistant. No database, no cloud, no proprietary runtime. All state lives as Markdown + YAML in your repository.

## Quick Start

Open your AI coding assistant (Claude Code, Cursor, OpenCode, Gemini CLI) and run:

```
/specflow-init
```

This scaffolds the project structure, installs slash command skills, and optionally sets up CI workflows. Then:

```
/specflow-discover → /specflow-plan → /specflow-execute → /specflow-ship
```

That's it. Each slash command is a guided conversation — the AI assistant handles the ceremony, you make the decisions.

Read the **[getting-started guide](docs/getting-started.md)** for a full walkthrough.

## The 9 Slash Commands

| Command | Purpose |
|---------|---------|
| `/specflow-init` | Bootstrap project, install skills, optional CI |
| `/specflow-discover` | Capture requirements through conversation |
| `/specflow-plan` | Break REQs into architecture + stories |
| `/specflow-execute` | Implement stories with test generation |
| `/specflow-artifact-review` | Quality review of specific artifacts |
| `/specflow-change-impact-review` | Blast-radius review of recent changes |
| `/specflow-audit` | Full-project periodic health check |
| `/specflow-ship` | Release: baseline + change records + audit |
| `/specflow-pack-author` | Author a standards compliance pack |

## Learn More

- [Getting started](docs/getting-started.md) — tutorial walkthrough
- [Lifecycle overview](docs/lifecycle.md) — flowchart + tiered command table
- [Command reference](docs/commands.md) — per-skill interface spec
- [CLI reference](docs/cli-reference.md) — raw CLI commands for power users and CI
- [Architecture](docs/architecture.md) — technical design
- [Design decisions](docs/decisions.md) — resolved trade-offs

## For Power Users

Under the hood, each slash command composes deterministic CLI commands (`uv run specflow ...`). You can invoke these directly for CI pipelines, automation, or when you prefer the terminal:

```bash
# Install SpecFlow (requires uv)
uv tool install specflow

# Or run without installing
uvx specflow --help

# Scaffold a project
uv run specflow init

# Check project status
uv run specflow status

# Run deterministic validation
uv run specflow artifact-lint
```

See the [CLI reference](docs/cli-reference.md) for the full command catalog organized by workflow phase.
