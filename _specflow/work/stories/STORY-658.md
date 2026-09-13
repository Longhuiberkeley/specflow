---
id: STORY-658
title: Collapse lifecycle skill bodies into lean routers
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:d41c31288e5d
modified: '2026-09-13'
---

# Collapse lifecycle skill bodies into lean routers

Router treatment per SPIKE-002 STORY-3 section: discover/execute/plan/init/start/doc/review-triad keep decisions+gates+pointers, cut recipes; delete the shared Freeform block; execute keeps Step 1L + stop-list per the F3 revision.

## Acceptance Criteria

1. discover/execute/plan/init/start/doc/review-triad SKILL.md bodies are lean routers — decisions, gates, and pointers only, no scripted recipes.
2. The copy-pasted Freeform block is gone from init/adapter/pack-author/lifecycle skills, replaced by one shared line.
3. execute keeps the gate command, Step 1L (trivial-change-still-gets-STORY), STORY→implemented + cascade-status, and baseline-then-delta, and stops only for approval-gated status, unapproved linked specs, or scope change.
4. Template and live `.claude` mirrors stay byte-identical (tests/test_v1143_integration.py).
