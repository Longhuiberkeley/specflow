---
id: STORY-KEEPRELE-37de
title: Keep release evidence RTM complete when verified REQs exist
type: story
status: implemented
suspect: false
links:
- target: REQ-015
  role: implements
- target: UT-EVIDENCE-9a3d
  role: verified_by
created: '2026-08-05'
fingerprint: sha256:387b32f39e7f
modified: '2026-08-05'
output_files:
- src/specflow/lib/evidence.py
- tests/test_evidence.py
---

# Keep release evidence RTM complete when verified REQs exist

## Context

The evidence generator prefers verified REQs and falls back to approved/implemented only when none are verified. The first verified REQ therefore collapses the ship-grade RTM from the full traceable set to one row.

## Acceptance Criteria

1. Evidence includes approved, implemented, and verified requirements in one deterministic matrix.
2. A mixed-status project retains every eligible REQ when at least one is verified.
3. Existing evidence tests and the full suite pass.

## Implementation

Update `src/specflow/lib/evidence.py` and add a mixed-status regression in `tests/test_evidence.py`.
