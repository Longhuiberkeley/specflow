---
id: STORY-004
title: Implement split and merge operations for artifact refactoring
type: story
status: implemented
priority: medium
tags:
- traceability
- refactoring
- P4
suspect: false
links:
- target: REQ-003
  role: implements
- target: ARCH-002
  role: guided_by
- target: DDD-001
  role: specified_by
created: '2026-04-11'
modified: '2026-04-11'
fingerprint: sha256:8b507fe4c303ad6020988de6f6886a9d8e54ae6c302f01751a058a5e81446410
checklists_applied:
- checklist: check-STORY-004
  timestamp: '2026-04-11T13:45:49Z'
---


# Implement split and merge operations for artifact refactoring

## Description

Implement the ability to split one artifact into two (reassigning downstream links) and merge two artifacts into one (rewriting all references). These operations maintain link integrity during architectural refactoring.

## Acceptance Criteria

1. Given ARCH-001 is being split into ARCH-001 and ARCH-004, and DDD-001, DDD-002, IT-001 all link to ARCH-001, when the split operation runs, then the user is presented with the list of downstream artifacts and can select which ones should be reassigned to ARCH-004, selected links are rewritten in the downstream artifacts' frontmatter, and a split event is recorded in the impact-log

2. Given ARCH-002 is being merged into ARCH-001, and STORY-005 and DDD-003 both link to ARCH-002, when the merge operation runs, then all links targeting ARCH-002 are rewritten to target ARCH-001, a merge event is recorded in the impact-log, and ARCH-002's status is set to merged_into with merged_target: ARCH-001

3. Given a split operation where the user selects zero downstream artifacts for reassignment, then all downstream links remain pointing to the original artifact and the split event is still logged (documenting the content fork without link changes)

## Out of Scope

- Hierarchical decomposition (dot-notation sub-artifacts)
- Automatic detection of when a split is needed

## Dependencies

- STORY-001 (impact-log infrastructure must exist)
