---
id: STORY-027
title: Expose recovery primitives as CLI commands and clean up dead code
type: story
status: draft
priority: medium
tags:
  - cleanup
  - CLI
  - M2-extensible
suspect: false
created: '2026-04-14'
---

# Expose recovery primitives as CLI commands and clean up dead code

## Description

Execute the dead-code disposition from retrospective §12. Expose 5 recovery primitives as new CLI commands and delete 9 genuinely-unused functions. Add `__all__` markers to 4 intentional exports. Ordered after the rename (STORY-022) to avoid conflicting refactors.

### New CLI commands

- `specflow unlock <id>` — Break a stale lock on an artifact (wraps `locks.break_stale_lock`)
- `specflow locks` — List all active locks (wraps `locks.list_locks`)
- `specflow rebuild-index` — Regenerate stale `_index.yaml` files (wraps `artifacts.rebuild_index`)
- `specflow split <id>` — Split an artifact into two (wraps `impact.split_artifact`)
- `specflow merge <id1> <id2>` — Merge two artifacts (wraps `impact.merge_artifact`)

### Deletions (9 functions)

- `artifacts.get_stories_by_status` — Specialized filter never wired up
- `challenge.persist_edge_cases` — Referenced by old SKILL.md but never called
- `challenge.create_decision_artifact` — DEC creation uses `specflow create dec`
- `config.update_execution_state` — Shadowed by `executor.load_execution_state`
- `config.read_execution_state` — Duplicate of above
- `dedup.run_dedup` — Orphaned; check.py has private `_run_dedup`
- `lint.load_schema_for_type` — Thin wrapper; callers use `load_schemas()` directly
- `lint.load_checklist` — Trivial helper used once internally; inline it
- (Assess `rbac.check_gpg_signature` — wire into hook or delete)

### `__all__` additions

- `executor.load_execution_state`
- `lint.recompute_fingerprint`
- `lint.discover_checklists`
- `lint.run_automated_checklist`

### Internal rename

- `lint.validate_status_transition` → `_validate_status_transition` (underscore prefix, internal)

## Acceptance Criteria

1. `specflow unlock <id>`, `specflow locks`, `specflow rebuild-index`, `specflow split <id>`, `specflow merge <id1> <id2>` all work as CLI commands with `--help` output

2. All 9 deleted functions are removed from the codebase and no import references them — `grep -r "<function_name>" src/` returns zero hits for each

3. `challenge.py` is assessed for full-module deletion if both its functions are removed

4. `__all__` exports are added to the 4 modules listed above and verified via `from specflow.lib.lint import *` style imports

5. `_validate_status_transition` is renamed with underscore prefix and all callers updated

6. `rbac.check_gpg_signature` disposition is decided: either wired into the pre-commit hook or deleted with documented rationale

7. Shell wrapper scripts in `scripts/` are created for each new CLI command

## Out of Scope

- Adapter framework (STORY-026)
- Pack authoring (STORY-028)

## Dependencies

- STORY-022 (command rename — must land first to avoid merge conflicts in cli.py and command files)
