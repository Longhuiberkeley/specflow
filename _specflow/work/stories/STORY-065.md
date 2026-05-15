---
id: STORY-065
title: Add category field to existing schema YAMLs
type: story
status: draft
priority: medium
tags:
- autoresearch
- wave-1
- schemas
suspect: false
links:
- target: REQ-033
  role: implements
- target: DDD-024
  role: specified_by
created: '2026-05-15'
---

# Add category field to existing schema YAMLs

## Outcome

All existing schema YAMLs in `src/specflow/templates/schemas/` declare a `category:` field.

## Scope

13 top-level + 3 optional schema files:

- **spec**: requirement, architecture, detailed-design, unit-test, integration-test, qualification-test
- **review**: review, audit, challenge
- **work**: story, spike, decision, defect
- **optional (spec)**: hazard, risk, control

One-line addition per file. No code changes.

## Acceptance

- `grep -L 'category:' src/specflow/templates/schemas/*.yaml` returns nothing (all top-level files have the field)
- Same for `optional/*.yaml`
- Existing schema-validation tests still pass
- iso26262-demo pack's `hazard.yaml` also gets a category line
