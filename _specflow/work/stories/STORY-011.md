---
id: STORY-011
title: Create and compare immutable baselines for project state snapshots
type: story
status: draft
priority: high
tags:
- compliance
- baselines
- P6
suspect: false
links:
- target: REQ-005
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-011
  timestamp: '2026-04-11T13:45:49Z'
---

# Create and compare immutable baselines for project state snapshots

## Description

Implement specflow baseline create and specflow baseline diff commands. Baselines capture an immutable snapshot of all artifact statuses, fingerprints, and test summaries at a point in time, enabling compliance audits and progress tracking.

## Acceptance Criteria

1. Given a project with 10 artifacts in various statuses, when specflow baseline create v1.0 runs, then a file .specflow/baselines/v1.0.yaml is created containing every artifact's ID, status, fingerprint, the creation timestamp, and a git tag reference

2. Given baselines v1.0 and v2.0 exist, when specflow baseline diff v1.0 v2.0 runs, then the output shows added artifacts (in v2.0 but not v1.0), removed artifacts, artifacts with changed status, and artifacts with changed fingerprints

3. Given a baseline v1.0 already exists, when specflow baseline create v1.0 is run again, then the command fails with an error stating baselines are immutable and cannot be overwritten

## Out of Scope

- Gap analysis against standards (STORY-012)
- Test execution records (P7)

## Dependencies

- None
