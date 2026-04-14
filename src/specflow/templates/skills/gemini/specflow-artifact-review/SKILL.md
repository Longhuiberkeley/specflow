---
name: specflow-artifact-review
description: Use when the user wants to review, validate, or verify any SpecFlow artifacts.
---

# SpecFlow Artifact Review

Review and verify artifacts using automated validation and checklist review.

## Workflow

1. **Run Validation** — Execute `uv run specflow artifact-lint`.
2. **Check Status** — Run `uv run specflow status`.
3. **Report** — Summarize blocking issues, warnings, and suggestions.
