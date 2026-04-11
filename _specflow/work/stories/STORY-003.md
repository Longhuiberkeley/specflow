---
id: STORY-003
title: Implement typo cascade defense with 3-tier classification
type: story
status: draft
priority: high
tags:
- traceability
- typo-defense
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
---

# Implement typo cascade defense with 3-tier classification

# Implement typo cascade defense with 3-tier classification

## Description

Implement the 3-tier defense against unnecessary suspect cascades from minor edits. Tier 1: explicit update_type: minor in frontmatter. Tier 2: specflow tweak convenience command. Tier 3: magnitude heuristic for auto-classification.

## Acceptance Criteria

1. Given REQ-001 with update_type: minor added to its frontmatter before a typo fix, when fingerprint validation detects the change, then the fingerprint is updated silently, the impact-log records update_type: minor, the update_type field is removed from frontmatter after processing, and NO suspect flags are propagated downstream

2. Given REQ-001 has a 1-line typo fix in a 200-line file and no update_type field set, when the magnitude heuristic runs, then the change ratio (< 0.5%) classifies it as minor automatically, skips cascade, and logs the event as minor with heuristic_applied: true

3. Given specflow tweak _specflow/specs/requirements/REQ-001.md is run after a cosmetic edit, then the fingerprint is recomputed, the impact-log records update_type: minor, and no suspect flags are propagated

4. Given REQ-001 has a body text change affecting 30 of 100 lines (30% change ratio) and no update_type field, when the magnitude heuristic runs, then the change is classified as semantic (above 5% threshold) and suspect cascade IS triggered (conservative default)

## Out of Scope

- The suspect propagation mechanism itself (STORY-001)
- Split/merge operations (STORY-004)

## Dependencies

- STORY-001 (propagation engine must exist for cascade to be skipped or triggered)
