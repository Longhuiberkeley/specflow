---
id: STORY-010
title: Extract prevention patterns into learned checklists via specflow done
type: story
status: verified
priority: medium
tags:
- challenge
- reactive
- learning
- P5
suspect: false
links:
- target: REQ-004
  role: implements
- target: REQ-001
  role: implements
- target: ARCH-002
  role: guided_by
- target: DDD-003
  role: specified_by
- target: UT-006
  role: verified_by
- target: IT-001
  role: verified_by
- target: QT-006
  role: verified_by
created: '2026-04-11'
modified: '2026-04-22'
fingerprint: sha256:fbbc5a2ad9c7
checklists_applied:
- checklist: check-STORY-010
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-010
  timestamp: '2026-04-14T17:03:22Z'
---

# Extract prevention patterns into learned checklists via specflow done

## Description

Implement the reactive challenge engine and specflow done command. When work completes, extract prevention patterns from completed stories, defect resolutions, and failed reviews into .specflow/checklists/learned/PREV-*.yaml files. These patterns auto-load for matching artifacts in future reviews.

## Acceptance Criteria

1. Given STORY-003 is completed and during review a race condition in token rotation was discovered and fixed, when specflow done runs and the user confirms the pattern is worth remembering, then a PREV-001.yaml is created in .specflow/checklists/learned/ with the pattern description, applies_to tags matching the story's tags, and a check item for future reviews

2. Given PREV-001.yaml exists with applies_to tags [auth, security], when a future artifact tagged [security] is reviewed via specflow check, then PREV-001's check items are automatically included in the assembled review criteria without the user explicitly requesting them

3. Given specflow done is run for a phase with 5 completed stories, when pattern extraction runs, then the user is asked about each story whether a prevention pattern should be extracted, state.yaml history records the phase exit, and all artifact statuses are finalized

4. Given specflow done is run and no patterns are worth extracting, then the phase closure proceeds normally without creating any PREV-*.yaml files

## Out of Scope

- Proactive challenge engine (STORY-009)
- Duplicate detection in learned patterns (P8)

## Dependencies

- STORY-008 (checklist assembly must support loading learned patterns)
