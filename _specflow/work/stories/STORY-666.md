---
id: STORY-666
title: BP anatomy, provenance fields, and transitional status map (REQ-044)
type: story
status: implemented
suspect: false
links:
- target: REQ-044
  role: implements
- target: ARCH-035
  role: guided_by
- target: DDD-032
  role: specified_by
created: '2026-09-25'
fingerprint: sha256:5b71045d81f0
thinking_techniques:
- premortem
- dependency-shock
- worst_case_user
- composition
modified: '2026-09-25'
---

# BP anatomy, provenance fields, and transitional status map (REQ-044)

## Story
Extend best-practice.yaml with the five-section anatomy, optional provenance/source/confidence/strength/applicability/tailoring/verification_method, and the transitional status map (approved: [draft, active]; superseded: [approved, active]) pinned byte-identical in pytest. This is the schema half of the DEC-089 coupling: it must land in the same release as the loader rewrite (STORY-668).

## Acceptance Criteria
1. Given a BP created with the new anatomy, when rendered, then all five sections appear in order.
2. Given the transitional map, when artifact-lint validates statuses, then active legacy BPs pass through approved and legacy supersession edges stay reachable.
3. Given the map file, when pytest runs, then the pinned-bytes assertion holds and any map edit fails the suite.
