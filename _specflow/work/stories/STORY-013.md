---
id: STORY-013
title: Generate retroactive change records from git history and impact-log
type: story
status: implemented
priority: medium
tags:
- compliance
- change-records
- P6
suspect: false
links:
- target: REQ-005
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-013
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-013
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-14'
fingerprint: sha256:ca1d162d382f
---

# Generate retroactive change records from git history and impact-log

## Description

Implement specflow document-changes that synthesizes change records (CR/DEC artifacts) from git diffs and impact-log events, so compliance documentation is a projection of existing data rather than a separate maintenance burden.

## Acceptance Criteria

1. Given 3 commits since HEAD~3 that each modified specification artifacts, when specflow document-changes --since HEAD~3 runs, then a DEC artifact is created for each semantic change, containing the commit message, changed artifacts, impact-log events, and a generated rationale summary

2. Given a commit that only changed non-artifact files (e.g., source code), when specflow document-changes processes it, then no DEC artifact is generated for that commit (only spec artifact changes produce records)

3. Given specflow document-changes --since v1.0 is run with a git tag, then only commits between v1.0 and HEAD are processed

## Out of Scope

- Manual change record authoring (handled by specflow create --type decision)
- Standards-specific CR formats (future pack content)

## Dependencies

- STORY-001 (impact-log infrastructure)
