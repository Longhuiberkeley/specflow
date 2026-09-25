---
id: ARCH-036
title: 'Guidance application: guided_by binding, evidence-based enforcement, tailoring'
type: architecture
status: approved
suspect: false
links:
- target: REQ-045
  role: derives_from
- target: DEC-086
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:1b4df2c769dd
modified: '2026-09-25'
thinking_techniques:
- '[premortem'
- dependency-shock]
---

# Guidance application: guided_by binding, evidence-based enforcement, tailoring

## Responsibility
Make practice guidance auditable on lifecycle artifacts: the guided_by link role for REQ/ARCH/STORY, the single evidence-based bp-application lint check, tailoring records citing an approved DEC, and brief bound/unbound accounting.

## Public interface
- requirement.yaml allowed_link_roles + requirement/guided_by, architecture/guided_by, story/guided_by rows in role_targets.py
- artifact_lint check bp-application: graph facts only (link presence, field values, coverage arithmetic, test-result status); warning-first, opt-in lint.bp_evidence_strict, migration stamp skip, backfill grace
- brief: bound versus unbound counts for REQ/ARCH/STORY
- tailoring: {status: dropped, rationale, dec} on the BP validating the DEC exists and is approved

## Dependencies
Consumes the practice spine (anatomy, provenance stamp) — the checks skip BPs without provenance. Modeled on compliance-evidence; one check only (no presence-only duplicates).

## Data flow
BP approved + in scope -> STORY/ARCH/REQ links guided_by -> artifact-lint verifies evidence -> brief reports binding coverage; drops route through DEC.
