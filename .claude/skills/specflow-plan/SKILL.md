---
name: specflow-plan
description: Use when requirements are approved and the user wants to break them down into architecture, design, and stories. Triggers architecture discussion and artifact population.
---

# SpecFlow Plan

Break down approved requirements into architecture, detailed design, and user stories.

## Workflow

1. **Phase Gate Check** — Confirm all relevant REQ artifacts have `status: approved`. Run gate checklist if available.
2. **Architecture Proposal** — Discuss component structure, interfaces, and data flow. Create ARCH artifacts in `_specflow/specs/architecture/`.
3. **Detailed Design** — For each ARCH component, create DDD artifacts in `_specflow/specs/detailed-design/`.
4. **Story Breakdown** — Create STORY artifacts in `_specflow/work/stories/` that link to specs via `links:` frontmatter.
5. **Validation** — Run `uv run specflow validate` on all generated artifacts.

## Rules

- ARCH answers "HOW is the system structured?" — interfaces between components
- DDD answers "HOW does each part work internally?" — implementation detail
- STORY references specs, doesn't replace them. Use `implements`, `guided_by`, `specified_by` link roles.
- Respect level boundaries — no user-facing behavior in ARCH, no code-level detail in ARCH

## References

- Read `references/link-roles.md` for proper link role usage.
- Read `references/level-boundaries.md` if unsure about artifact level.
