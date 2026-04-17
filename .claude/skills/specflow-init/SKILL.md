---
name: specflow-init
description: Use when setting up SpecFlow in a new or existing project. Conversational bootstrap that scaffolds directories, installs hooks, generates CI workflows, and recommends next steps.
---

# SpecFlow Init

Conversational bootstrap for a SpecFlow project.

> **Stub** — This skill is a placeholder. Full implementation lands in STORY-033.

## Workflow

1. Ask the user about project type, preset, and CI provider
2. Run `uv run specflow init` with appropriate flags
3. Install git hook via `uv run specflow hook install`
4. Optionally generate CI workflow via `uv run specflow ci generate`
5. Report what was scaffolded and recommend `/specflow-discover`
