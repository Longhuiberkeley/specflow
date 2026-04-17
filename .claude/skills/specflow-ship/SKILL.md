---
name: specflow-ship
description: Use when the user wants to release a version. Produces a baseline, generates change records, runs a quick audit, and presents a release summary.
---

# SpecFlow Ship

Release workflow: baseline, change records, and audit.

> **Stub** — This skill is a placeholder. Full implementation lands in STORY-033.

## Workflow

1. Run `uv run specflow baseline create <tag>` to create an immutable snapshot
2. Run `uv run specflow document-changes --since <prev>` to generate DEC trail
3. Run `uv run specflow project-audit --quick` for a fast health check
4. Present release summary with links to baseline, DECs, and audit report
5. Advisory if audit severity >= error — user must confirm to proceed
