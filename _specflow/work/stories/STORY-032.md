---
id: STORY-032
title: "Delete over-exposed skill directories \u2014 collapse 22 skills to 8 Tier\
  \ 1"
type: story
status: verified
priority: high
tags:
- UX
- skills
- M4-ux
suspect: false
links:
- target: STORY-022
  role: depends_on
- target: REQ-019
  role: implements
- target: ARCH-011
  role: guided_by
- target: DDD-008
  role: specified_by
- target: QT-020
  role: verified_by
- target: IT-013
  role: verified_by
- target: UT-014
  role: verified_by
created: '2026-04-17'
fingerprint: sha256:84a65b667115
version: 2
modified: '2026-04-22'
---

# Delete over-exposed skill directories — collapse 22 skills to 9 Tier 1

## Description

The current skill surface exposes 22 `/specflow-*` commands to users, but most of these are thin CLI wrappers or internal plumbing that should not be user-facing. Per the UX review, the target is **9 Tier 1 conversational slash commands** — the `/specflow-*` slash command surface is the product. The `uv run specflow ...` Python CLI is a power-user appendix.

`/specflow-artifact-review` and `/specflow-change-impact-review` are intentionally kept as **separate** slash commands. They do functionally different work (per-artifact quality review vs. blast-radius review of recent commits/PRs) and the project favors explicit naming over conversational scoping that guesses user intent.

This story is the **cleanup phase**: delete the 16 skill directories that are over-exposed, leaving only the 9 that survive (6 existing + 3 to be created/rewritten in STORY-033).

## Deliverables

1. **Delete 16 skill directories** from `.claude/skills/`:
   - Tier 3 (should never have had skill dirs): `specflow-artifact-lint`, `specflow-checklist-run`, `specflow-detect`
   - Thin CLI wrappers (no conversational value): `specflow-create`, `specflow-update`, `specflow-status`, `specflow-fingerprint-refresh`, `specflow-renumber-drafts`, `specflow-import`, `specflow-export`
   - Absorbed by `/specflow-init`: `specflow-hook`
   - Absorbed by `/specflow-execute`: `specflow-done`, `specflow-go`
   - Absorbed by `/specflow-ship`: `specflow-baseline`, `specflow-document-changes`
   - Rewritten as `/specflow-audit` (delete the old dir; STORY-033 creates the new one): `specflow-project-audit`

2. **Verify no breakage** — all 25 CLI commands still work via `uv run specflow --help` and `uv run specflow artifact-lint` (the CLI surface is unchanged)

3. **Delete corresponding shell wrappers** from `scripts/` that only existed for the deleted skill directories (keep wrappers that the remaining 8 skills or CI pipelines use)

## Acceptance Criteria

1. Exactly 9 skill directories remain in `.claude/skills/`: `specflow-init`, `specflow-discover`, `specflow-plan`, `specflow-execute`, `specflow-artifact-review`, `specflow-change-impact-review`, `specflow-audit`, `specflow-ship`, `specflow-pack-author` (init/audit/ship may be placeholder stubs if STORY-033 has not yet landed)
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
