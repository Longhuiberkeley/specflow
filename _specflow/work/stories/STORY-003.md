---
id: STORY-003
title: Implement typo cascade defense with 3-tier classification
type: story
status: implemented
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
modified: '2026-04-11'
fingerprint: sha256:ffd852f3fbc25b46c53f68130ee55a44686570452d8bbc443c5cfbf211d26843
checklists_applied:
- checklist: check-STORY-003
  timestamp: '2026-04-11T13:45:49Z'
---



# Implement typo cascade defense with 3-tier classification

## Description

Implement the 3-tier defense against unnecessary suspect cascades from minor edits. Tier 1: explicit update_type: minor in frontmatter. Tier 2: specflow tweak convenience command. Tier 3: magnitude heuristic for auto-classification.

## Acceptance Criteria

1. Given REQ-001 with update_type: minor added to its frontmatter before a typo fix, when fingerprint validation detects the change, then the fingerprint is updated silently, the impact-log records update_type: minor, the update_type field is removed from frontmatter after processing, and NO suspect flags are propagated downstream

2. Given no update_type field is set and the magnitude heuristic runs, when git diff context is unavailable at the call site, then the heuristic conservatively classifies the change as semantic (triggering cascade). Users should use Tier 1 (update_type: minor) or Tier 2 (specflow tweak) for known minor edits

3. Given specflow tweak _specflow/specs/requirements/REQ-001.md is run after a cosmetic edit, then the fingerprint is recomputed, the impact-log records update_type: minor, and no suspect flags are propagated

4. Given REQ-001 has a body text change and no update_type field, when the magnitude heuristic runs without git diff context, then the change is classified as semantic (conservative default) and suspect cascade IS triggered

## Out of Scope

- The suspect propagation mechanism itself (STORY-001)
- Split/merge operations (STORY-004)

## Dependencies

- STORY-001 (propagation engine must exist for cascade to be skipped or triggered)
