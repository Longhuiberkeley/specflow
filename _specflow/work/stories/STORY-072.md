---
id: STORY-072
title: Write explore-exploit-protocol.md
type: story
status: implemented
priority: medium
tags:
- autoresearch
- wave-3
- protocol
suspect: false
links:
- target: REQ-031
  role: implements
created: '2026-05-15'
fingerprint: sha256:fec81ef311f1
---

# Write explore-exploit-protocol.md

## Outcome

`references/explore-exploit-protocol.md` (~150 lines) — new document describing mode behavior.

## Content

- **When to use each mode**:
  - explore: first loop on a COMP; after exploit loops plateau
  - exploit: after explore found something promising
  - validate: after significant improvement; before deployment
- **How mode influences Phase 2 (Ideate)**:
  - explore reads FIND `what_failed` to avoid repeats; aims for creative variation
  - exploit reads FIND `what_worked` for direction; aims for refinement
  - validate re-runs best approaches, possibly on different data/config
- **Post-loop mode suggestion heuristic** (documentation only, not automated in v1):
  - Improved significantly → suggest exploit
  - Plateaued without improvement → suggest explore
  - Haven't validated in N loops → suggest validate
- **Anti-patterns**: don't exploit a fragile result; don't explore when close to breakthrough

## Acceptance Criteria

1. All 3 modes documented with concrete examples
2. Heuristic clearly labeled as documentation, not automation
3. File compiles when included in skill bundle
