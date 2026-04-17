# SpecFlow

SpecFlow is a cross-CLI, spec-driven development framework that unifies requirement capture, ASPICE-grade traceability, and context-efficient execution. All state lives as Markdown + YAML in the repository — no database, no cloud, no proprietary runtime.

## Install

```bash
# One-line install (requires uv)
uv tool install specflow

# Or run without installing
uvx specflow --help
```

Verify the installation:

```bash
specflow --help
```

Quick start:

```bash
specflow init              # scaffold a new project
specflow status            # see the dashboard
```

Read the **[getting-started guide](docs/getting-started.md)** for a full walkthrough.

## Learn more

- [Getting started](docs/getting-started.md) — tutorial walkthrough
- [Lifecycle overview](docs/lifecycle.md) — flowchart + tiered command table
- [Command reference](docs/commands.md) — per-skill interface spec
- [Architecture](docs/architecture.md) — technical design
- [Design decisions](docs/decisions.md) — resolved trade-offs
