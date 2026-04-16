---
id: STORY-032
title: "Delete over-exposed skill directories \u2014 collapse 22 skills to 8 Tier\
  \ 1"
type: story
status: approved
priority: high
tags:
- UX
- skills
- M4-ux
suspect: false
links:
- target: STORY-022
  role: depends_on
created: '2026-04-17'
---

# Delete over-exposed skill directories — collapse 22 skills to 8 Tier 1

## Description

The current skill surface exposes 22 `/specflow-*` commands to users, but most of these are thin CLI wrappers or internal plumbing that should not be user-facing. Per the UX review, the target is **8 Tier 1 conversational skills** — everything else is a `uv run specflow` CLI command for power users.

This story is the **cleanup phase**: delete the 14 skill directories that are over-exposed, leaving only the 8 that survive (4 existing + 4 to be created/rewritten in STORY-033).

## Deliverables

1. **Delete 14 skill directories** from `.claude/skills/`:
   - Tier 3 (should never have had skill dirs): `specflow-artifact-lint`, `specflow-checklist-run`, `specflow-detect`
   - Absorbed by `/specflow-review`: `specflow-change-impact-review`, `specflow-document-changes`, `specflow-project-audit`
   - Absorbed by `/specflow-ship`: `specflow-baseline`
   - Absorbed by `/specflow-init`: `specflow-hook`
   - Absorbed by `/specflow-execute`: `specflow-done`, `specflow-go`
   - Thin CLI wrappers (no conversational value): `specflow-create`, `specflow-update`, `specflow-status`, `specflow-fingerprint-refresh`, `specflow-renumber-drafts`, `specflow-import`, `specflow-export`

2. **Verify no breakage** — all 25 CLI commands still work via `uv run specflow --help` and `uv run specflow artifact-lint` (the CLI surface is unchanged)

3. **Delete corresponding shell wrappers** from `scripts/` that only existed for the deleted skill directories (keep wrappers that the remaining 8 skills or CI pipelines use)

## Acceptance Criteria

1. Only 8 skill directories remain in `.claude/skills/`: `specflow-discover`, `specflow-plan`, `specflow-execute`, `specflow-artifact-review`, `specflow-pack-author`, plus `specflow-init`, `specflow-review`, `specflow-ship`, `specflow-audit` (placeholders if STORY-033 is not yet done)
2. `uv run specflow --help` shows all 25 CLI commands with no errors
3. `uv run specflow artifact-lint` runs successfully (Tier 3 commands still work as CLI)
4. `uv run specflow status` runs successfully (Tier 2 commands still work as CLI)
5. No dangling references to deleted skill directories in any code or config

## Out of Scope

- Creating new skills (STORY-033)
- Updating documentation (STORY-034)
- Changing any CLI command behavior or renaming

## Dependencies

- STORY-022 (command rename — skill dirs reference post-rename names)
