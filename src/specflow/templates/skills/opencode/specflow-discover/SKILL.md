---
name: specflow-discover
description: Use when the user wants to discover, capture, or author new requirements. Triggers a progressive disclosure conversation to extract specifications and create REQ artifacts.
---

# SpecFlow Discover

Conduct a structured discovery conversation to capture requirements.

## Workflow

1. **Readiness Assessment** — Ask clarifying questions about scope. If all dimensions are satisfied within 1 exchange, proceed with lean artifacts.
2. **Progressive Disclosure** — Uncover WHAT the system must do (not HOW). Focus on observable behavior.
3. **Artifact Creation** — Generate REQ Markdown files in `_specflow/specs/requirements/` with proper YAML frontmatter.
4. **Validation** — Run `uv run specflow artifact-lint` to check schema compliance.

## Rules

- Requirements answer "WHAT must the system do?"
- Use normative language: "The system **shall**..."
- No implementation details, technology choices, or "how" descriptions
- Each REQ must have acceptance criteria
