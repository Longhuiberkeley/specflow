---
id: STORY-015
title: Implement draft IDs on branches with CI renumbering on merge
type: story
status: verified
priority: medium
tags:
- team
- ids
- branching
- P7
suspect: false
links:
- target: REQ-002
  role: implements
- target: ARCH-001
  role: guided_by
- target: UT-007
  role: verified_by
- target: IT-001
  role: verified_by
- target: QT-004
  role: verified_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-015
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-015
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:949cd520fcbe
version: 2
---

# Implement draft IDs on branches with CI renumbering on merge

## Description

Implement readable draft IDs (e.g., REQ-AUTH-a7b9) for feature branches that are automatically renumbered to sequential integers (REQ-006) on merge to main via specflow renumber-drafts. This eliminates ID collision conflicts between parallel branches.

## Acceptance Criteria

1. Given a user creates an artifact on a feature branch, when specflow create runs, then the artifact receives a draft ID with a readable prefix and 4-char hash suffix (e.g., REQ-AUTH-a7b9) instead of a sequential integer

2. Given a feature branch with 3 draft-ID artifacts is merged to main, when specflow renumber-drafts runs, then all draft IDs are replaced with sequential integers continuing from the current next_id, all links referencing the draft IDs are rewritten across the entire repo, and _index.yaml files are updated

3. Given two feature branches both create REQ artifacts with draft IDs, when both are merged to main, then specflow renumber-drafts assigns non-conflicting sequential IDs to both sets of artifacts without manual intervention

> Amended 2026-10-18 (SPIKE-008 R1-129): the command is `specflow renumber-drafts` (cli.py:732); there is no `specflow sequence`.

## Out of Scope

- Cross-repo ID namespacing
- Automatic merge conflict resolution for artifact files

## Dependencies

- None
