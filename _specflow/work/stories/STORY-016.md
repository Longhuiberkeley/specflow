---
id: STORY-016
title: Implement defect lifecycle tracking with V-model linkage
type: story
status: verified
priority: medium
tags:
- team
- defects
- lifecycle
- P7
suspect: false
links:
- target: REQ-002
  role: implements
- target: ARCH-002
  role: guided_by
- target: UT-003
  role: verified_by
- target: IT-002
  role: verified_by
- target: QT-004
  role: verified_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-016
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-016
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:bcd75bb30bed
---

# Implement defect lifecycle tracking with V-model linkage

## Description

Implement DEF-* artifact lifecycle (open -> investigating -> fixing -> verified -> closed) with links back to the V-model (fails_to_meet for broken requirements, exposed_by for catching tests). On closure, trigger the reactive challenge engine to extract prevention patterns.

## Acceptance Criteria

1. Given a test failure reveals a bug in authentication, when specflow create --type defect is run with links to the failing REQ and exposing test, then DEF-001 is created with status: open, severity and priority fields, and fails_to_meet and exposed_by links

2. Given DEF-001 is in status 'open', when specflow update DEF-001 --status investigating runs, then the status transitions successfully, and when specflow update DEF-001 --status closed is attempted (skipping fixing and verified), then the transition is rejected as invalid

3. Given DEF-001 transitions to status: closed, when the closure is processed, then the reactive challenge engine is triggered to ask whether a prevention pattern should be extracted from this defect's resolution

## Out of Scope

- Defect priority triaging automation
- Integration with external bug trackers

## Dependencies

- STORY-010 (reactive challenge engine for pattern extraction on closure)
