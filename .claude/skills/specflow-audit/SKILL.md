---
name: specflow-audit
description: Use when the user wants a full-project health review. Runs a zero-question deterministic core with optional adversarial wings. Creates AUD and CHL artifacts.
---

# SpecFlow Audit

Full-project health review.

> **Stub** — This skill is a placeholder. Full implementation lands in STORY-033.

## Workflow

1. Run `uv run specflow project-audit` deterministically (horizontal + vertical + cross-cutting)
2. Optionally launch adversarial wings (16 lenses via 2 parallel subagents)
3. Create AUD and CHL artifacts from findings
4. Present summary with severity breakdown
