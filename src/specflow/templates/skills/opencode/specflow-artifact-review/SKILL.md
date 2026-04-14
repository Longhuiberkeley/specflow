---
name: specflow-artifact-review
description: Use when the user wants to review, validate, or verify any SpecFlow artifacts. Triggers context-specific checks using automated scripts and checklist review.
---

# SpecFlow Artifact Review

Review and verify artifacts using automated validation and checklist review.

## Workflow

1. **Run Validation** — Execute `uv run specflow artifact-lint` for zero-token checks.
2. **Check Status** — Run `uv run specflow status` to review dashboard.
3. **Checklist Review** — Run automated checks first, then LLM-judged checks.
4. **Report** — Summarize findings: blocking issues, warnings, and suggestions.
