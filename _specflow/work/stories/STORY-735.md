---
id: STORY-735
title: Audit ddd-shape accounting class and truthful DDD-thread walk (v1.17.3)
type: story
status: verified
suspect: false
links:
- target: REQ-053
  role: implements
created: '2026-10-09'
fingerprint: sha256:7900dc443e8c
modified: '2026-10-09'
output_files:
- src/specflow/commands/project_audit.py
- tests/test_project_audit_cache_key.py
- tests/test_project_audit_ddd_shape.py
---

# Audit ddd-shape accounting class and truthful DDD-thread walk (v1.17.3)

Engine half of the v1.17.3 release-gate fix (frontier-review AMEND verdict).

1. Truthful DDD walk in project-audit vertical analysis: credit a DDD onto a REQ thread via all three legal shapes - DDD-held refined_by/derives_from, the canonical parent-held ARCH refined_by DDD (mirrors check_coverage), and DDD-held specified_by ARCH (role_targets). Regression: DDD-033 carries specified_by ARCH-039, so REQ-052/053 printed a false no-DDD row.
2. Staged row class (DEC-101): when the thread has an implementing STORY, the no-DDD row is stamped concern ddd-shape (registered accounting); concern-less rows (no ARCH / no STORY / no-DDD-without-STORY) keep escalating.
3. _CACHE_GENERATION 6 to 7 (concern classification is part of cached findings).

Tests: tests/test_project_audit_ddd_shape.py (new), tests/test_project_audit_cache_key.py (gen 7).

## Acceptance Criteria

1. Given an approved REQ whose thread has an ARCH and an implementing STORY but no DDD, when project-audit runs, then the no-DDD row SHALL carry concern ddd-shape and SHALL NOT drive exit 2.
2. Given an approved REQ whose thread has an ARCH but no STORY and no DDD, when project-audit runs, then the no-DDD row SHALL carry no concern and SHALL escalate.
3. Given a DDD linked to a thread ARCH via parent-held refined_by or DDD-held specified_by, when the vertical walk runs, then the DDD SHALL be credited and no no-DDD row SHALL emit (REQ-052/053 regression).
4. Given the changed lens semantics, when the findings cache is consulted, then _CACHE_GENERATION SHALL be 7 so gen-6 replays cannot shadow the new concern classification.
