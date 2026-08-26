---
id: STORY-634
title: 'Type-aware trace direction: implements/guided_by/specified_by and test verified_by
  as upstream'
type: story
status: implemented
tags:
- traceability
suspect: false
links:
- target: REQ-003
  role: implements
- target: REQ-007
  role: implements
created: '2026-08-26'
fingerprint: sha256:81166a6a050a
modified: '2026-08-26'
output_files:
- src/specflow/lib/artifacts.py
- tests/test_artifacts.py
---

# Type-aware trace direction: implements/guided_by/specified_by and test verified_by as upstream

## Goal

specflow trace STORY-NNN currently shows '(none)' upstream even when the STORY implements a REQ: UPSTREAM_ROLES only contains derives_from/complies_with.

## Acceptance Criteria

1. Upstream traversal is type-aware, not role-only: STORY implements/guided_by/specified_by targets are upstream; UT/IT/QT verified_by targets are upstream for tests; STORY→test verified_by edges render downstream (role is bidirectional in dogfood, direction must follow source/target types).
2. specflow trace STORY-632 shows REQ-005, REQ-001, DEC-077 upstream and its UT/IT/QT downstream.
3. chain-depth computation is not inflated by unrelated incoming edges (evaluated on the same type-aware rules).
4. Tests cover both directions of verified_by plus implements/guided_by/specified_by; full suite green.

## Out of scope
Role-target semantic enforcement matrix (deferred to v1.15.0).

## Authorization note
Pre-authorized by the owner via scheduled autonomous task (oc-later 2026-08-26).
rization note
Pre-authorized by the owner via scheduled autonomous task (oc-later 2026-08-26).
