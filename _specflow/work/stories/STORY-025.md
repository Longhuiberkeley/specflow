---
id: STORY-025
title: Ship the change-audit pipeline with review_status field
type: story
status: draft
priority: high
tags:
- pipeline
- audit
- M1-clarity
suspect: false
created: '2026-04-14'
checklists_applied:
- checklist: check-STORY-025
  timestamp: '2026-04-14T17:03:23Z'
---

# Ship the change-audit pipeline with review_status field

## Description

Ship the two-stage change-audit pipeline from retrospective §7: `/specflow-document-changes` emits DEC artifacts from git history, then `/specflow-change-impact-review` LLM-reviews unreviewed DECs scoped by blast radius. Add `review_status` field to DEC/CHL/AUD schemas. The pipeline must be idempotent — running twice with no new commits is a no-op.

### Pipeline flow

```
git commit → /specflow-document-changes (emits DEC with review_status: unreviewed)
           → /specflow-change-impact-review (per-DEC: blast radius + LLM review → flip review_status)
```

### review_status field

Values: `unreviewed`, `reviewed`, `flagged`, `addressed`, `accepted`, `stale`. Added to DEC schema, CHL schema (from STORY-024), and new AUD schema.

### Blast-radius scoping

Per-commit work is bounded by the impact cone of each unreviewed DEC (via `specflow change-impact`), not the whole project. Subagent review is scoped to that cone.

## Acceptance Criteria

1. `specflow document-changes --since <ref>` creates DEC artifacts in `_specflow/specs/decisions/` with `review_status: unreviewed` and links to affected artifacts

2. `/specflow-change-impact-review` finds all DECs with `review_status: unreviewed`, computes blast radius per DEC via `specflow change-impact`, and launches subagent review scoped to each cone

3. After review, each DEC's `review_status` is flipped to `reviewed` or `flagged`; findings become CHL artifacts linked to the DEC

4. Running `/specflow-change-impact-review` twice in a row with no new commits produces no new work (idempotent)

5. `review_status` field is added to `templates/schemas/decision.yaml`, `templates/schemas/challenge.yaml`, and new `templates/schemas/audit.yaml`

6. `templates/schemas/audit.yaml` is created with the AUD artifact type definition

## Out of Scope

- Full `/specflow-project-audit` (STORY-030)
- CI workflow integration (STORY-026)
- `/specflow-release` orchestration skill (depends on this pipeline but is a separate story)

## Dependencies

- STORY-022 (command rename — impact→change-impact)
- STORY-024 (CHL artifact type and schema)
