---
id: STORY-002
title: Report and resolve suspect flags via specflow impact command
type: story
status: implemented
priority: high
tags:
- traceability
- impact
- cli
- P4
suspect: false
links:
- target: REQ-003
  role: implements
- target: REQ-001
  role: implements
- target: ARCH-001
  role: guided_by
- target: DDD-001
  role: specified_by
created: '2026-04-11'
modified: '2026-04-11'
fingerprint: sha256:e6c357dd6dd6f16db86a8e922a2fe950097e1dcafa93ec11b5cdcde01482b8f5
checklists_applied:
- checklist: check-STORY-002
  timestamp: '2026-04-11T13:45:49Z'
---


# Report and resolve suspect flags via specflow impact command

## Description

Implement the specflow impact CLI command that reads impact-log events and artifact state to display unresolved suspect flags with source lineage, and allows resolving individual flags after review.

## Acceptance Criteria

1. Given 3 artifacts with suspect: true (flagged from 2 different source changes), when running specflow impact, then the output groups suspects by source artifact, shows each suspect's link role, displays the oldest unresolved flag age, and suggests the resolve command

2. Given ARCH-001 has suspect: true from a change to REQ-001, when running specflow impact --resolve ARCH-001, then ARCH-001's suspect is set to false, the impact-log event is updated with resolved: true, resolved_by and resolved_at fields, and subsequent specflow impact output no longer shows ARCH-001

3. Given no unresolved suspect flags exist, when running specflow impact, then the output shows 'No unresolved suspect flags' and returns exit code 0

4. Given specflow impact REQ-001 is run, then only flags caused by changes to REQ-001 are shown, filtering out flags from other sources

## Out of Scope

- Suspect propagation logic (STORY-001)
- Typo cascade defense (STORY-003)

## Dependencies

- STORY-001 (suspect propagation must exist to generate flags)
