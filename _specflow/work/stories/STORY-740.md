---
id: STORY-740
title: 'Revive the PREV loop: tag inheritance on DEF closure, patterns update/retire,
  prev/inert audit row, backfill'
type: story
status: verified
tags:
- core
- cli
- robustness
- review
suspect: false
links:
- target: REQ-067
  role: implements
created: '2026-10-18'
fingerprint: sha256:cea2a39b1ff7
modified: '2026-10-18'
output_files:
- src/specflow/lib/defects.py
- src/specflow/lib/learning.py
- src/specflow/lib/checklists.py
- src/specflow/commands/patterns.py
- src/specflow/cli.py
- src/specflow/commands/project_audit.py
- src/specflow/commands/brief.py
- docs/cli-reference.md
- tests/test_prev_loop.py
- tests/test_project_audit_cache_key.py
thinking_techniques:
- worst_case_user
- composition
---

# Revive the PREV loop: tag inheritance on DEF closure, patterns update/retire, prev/inert audit row, backfill

## Summary

Revive the compound loop. (1) `lib/defects.py on_closure`: compute the seeded PREV's `applies_to.tags` as DEF tags ∪ tags of its `fails_to_meet` REQs (resolve via lib/artifacts), minus tags matching `^v\d`; when the result is empty print a WARNING naming the PREV as inert plus the exact repair command. (2) New `specflow patterns update <PREV-ID> --tags a,b` and `specflow patterns retire <PREV-ID>` subcommands (src/specflow/commands/patterns.py + cli.py parser + dispatch), writing the YAML under `.specflow/checklists/learned/` through lib/learning helpers (retire sets `retired: true`; `_load_learned_patterns` and `list_learned_patterns` skip retired ones). (3) `project-audit` gains a `prev/inert` accounting row per PREV with empty tags (register the concern in `_ACCOUNTING_CONCERNS`, bump `_CACHE_GENERATION`). (4) `brief` knowledge line reads "PREV N (M inert)". (5) Backfill PREV-003..PREV-020 through the new CLI with tags derived from each `discovered_from` artifact (DEF/CHL/STORY tags, else the artifact's linked REQ tags; use `core,review` when nothing resolves) and record the commands run on this STORY. docs/cli-reference.md gains the two subcommands. Tests: tag inheritance (DEF+REQ union, release-tag exclusion, empty → warning text), patterns update/retire round-trip, inert audit row, brief count.

## Acceptance Criteria

1. Given a DEF tagged `cli,v1.17.5` that fails_to_meet a REQ tagged `core`, when it closes, then the seeded PREV has tags `cli` and `core` and not `v1.17.5`.
2. Given a DEF whose computed tags are empty, when it closes, then stdout contains "inert" and a `specflow patterns update PREV-` repair command.
3. Given `specflow patterns update PREV-003 --tags core,review`, when `specflow checklist-run` runs on an artifact tagged `core`, then the assembled sources include `learned/PREV-*` and PREV-003's item.
4. Given `specflow patterns retire PREV-NNN`, when `patterns list` and checklist assembly run, then the pattern is absent from both.
5. Given a project with one empty-tag PREV, when `project-audit` runs, then one `prev/inert` warning row appears, it is accounting, and the exit code is unchanged.
6. Given this repository after backfill, when `specflow brief` runs, then the knowledge line reads "PREV 20 (0 inert)" and `project-audit` emits zero `prev/inert` rows.

## Backfill record

Tags derived per PREV from its `discovered_from` DEF via `learning.inherited_tags` (DEF tags ∪ `fails_to_meet` REQ tags, minus `^v\d`). Every DEF-001..DEF-019 source was untagged, so all tags come from the REQs; no PREV needed the `core,review` fallback. PREV-001/PREV-002 were already tagged and left unchanged. Commands run (each exit 0):

```
specflow patterns update PREV-003 --tags autoresearch,logging,domain-awareness,quant,safety
specflow patterns update PREV-004 --tags rbac,ci,adapters
specflow patterns update PREV-005 --tags rbac,ci,adapters
specflow patterns update PREV-006 --tags verification,accounting-not-policing
specflow patterns update PREV-007 --tags quality,ears,requirements,lint
specflow patterns update PREV-008 --tags functional,core,format,mvp
specflow patterns update PREV-009 --tags functional,core,format,mvp
specflow patterns update PREV-010 --tags functional,core,format,mvp
specflow patterns update PREV-011 --tags functional,core,format,mvp
specflow patterns update PREV-012 --tags functional,core,format,mvp
specflow patterns update PREV-013 --tags functional,traceability,impact,core
specflow patterns update PREV-014 --tags functional,core,format,mvp
specflow patterns update PREV-015 --tags functional,core,format,mvp
specflow patterns update PREV-016 --tags functional,core,format,mvp
specflow patterns update PREV-017 --tags rbac,ci,adapters
specflow patterns update PREV-018 --tags verification,evidence,formal-methods
specflow patterns update PREV-019 --tags functional,traceability,impact,core
specflow patterns update PREV-020 --tags functional,core,format,mvp
```

Result: `specflow brief` → `PREV 20 (0 inert)`; `specflow project-audit --dry-run` → 0 `prev/inert` rows.
