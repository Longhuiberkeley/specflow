---
id: STORY-082
title: Revive BP and PREV knowledge-surface visibility and consumption
type: story
status: implemented
priority: high
tags:
- learnings
- bp
- prev
- brief
- checklists
- backfilled
suspect: false
links:
- target: REQ-001
  role: implements
- target: REQ-005
  role: implements
created: '2026-07-30'
fingerprint: sha256:d35eee78fc50
thinking_techniques:
- worst_case_user
- composition
modified: '2026-07-30'
version: 1
verification_gate:
  baseline: 'uv run pytest: 718 passed'
  final: 'uv run pytest: 723 passed'
  delta: +5 tests, 0 regressions
output_files:
- src/specflow/lib/ci.py
- src/specflow/lib/checklists.py
- src/specflow/commands/artifact_review.py
- src/specflow/commands/brief.py
- src/specflow/templates/agent-context.md
- AGENTS.md
- tests/test_brief.py
- tests/test_knowledge_lifecycle.py
checklists_applied:
- checklist: check-STORY-082
  timestamp: '2026-07-29T17:23:03Z'
---

# Revive BP and PREV knowledge-surface visibility and consumption

## Description

Make the existing proactive BP and reactive PREV knowledge surfaces visible and reliably consumed without adding a third learning system. This backfills traceability for the reviewed implementation begun before a STORY was created.

## Acceptance Criteria

1. Given BP, PREV, FIND, and CHL are all empty, when `specflow brief` runs, then it still renders the Knowledge surfaces block with zero counts and advisory dormancy hints.
2. Given an active or approved BP matches an artifact by tag or `applies_to`, when checklist assembly or artifact review runs, then one canonical matcher selects it and the practice is judged exactly once.
3. Given nonmatching, draft, or superseded BPs, when checklist assembly runs, then they are excluded.
4. Given the dogfood repository, when brief and checklist commands run, then genuine BP and PREV examples prove both proactive and reactive loops end to end.
5. Given generated agent context, when compared with the dogfood AGENTS.md block, then the knowledge-surface guidance remains synchronized.
6. Given the implementation, when targeted and full tests run, then empty-state visibility, matching, no duplicate prompt content, and single inventory discovery are covered with no regression from the 718-test baseline.

## Test Strategy

Add focused unit/integration coverage in `tests/test_brief.py` and `tests/test_knowledge_lifecycle.py`, then run the full pytest suite and deterministic artifact lint.
