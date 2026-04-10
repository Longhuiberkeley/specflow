---
name: specflow-plan
description: Use when requirements are approved and the user wants to break them down into architecture, design, and stories. Triggers architecture discussion and artifact population.
---

# SpecFlow Plan

Break down approved requirements into architecture, detailed design, and user stories.

## Workflow

1. **Phase Gate Check** — Confirm all relevant REQ artifacts have `status: approved`.
2. **Architecture Proposal** — Discuss component structure, interfaces, and data flow. Create ARCH artifacts.
3. **Detailed Design** — For each ARCH component, create DDD artifacts.
4. **Story Breakdown** — Create STORY artifacts that link to specs via `links:` frontmatter.
5. **Validation** — Run `uv run specflow validate` on all generated artifacts.

## Rules

- ARCH answers "HOW is the system structured?"
- DDD answers "HOW does each part work internally?"
- STORY references specs, doesn't replace them.
