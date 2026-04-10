---
name: specflow-verify
description: Use when the user wants to review, validate, or verify any SpecFlow artifacts. Triggers context-specific checks using automated scripts and checklist review.
---

# SpecFlow Verify

Review and verify artifacts using automated validation and checklist review.

## Workflow

1. **Run Validation** — Execute `uv run specflow validate` for zero-token checks (schema, links, status, IDs, fingerprints).
2. **Check Status** — Run `uv run specflow status` to review dashboard.
3. **Checklist Review** — Assemble checklists from artifact type + domain tags + shared checklists. Run automated checks first, then LLM-judged checks.
4. **Report** — Summarize findings: blocking issues, warnings, and suggestions.

## Rules

- Automated checks (zero tokens) always run first
- LLM-judged checks only run if automated checks pass
- Severity levels: `blocking` (must fix), `warning` (should fix), `info` (nice to know)

## References

- Read `references/checklist-assembly.md` for how checklists are assembled.
- Read `references/severity-levels.md` for severity definitions.
