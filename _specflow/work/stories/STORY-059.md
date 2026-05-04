---
id: STORY-059
title: Bundle generic best-practice fallback for handbook generation
type: story
status: implemented
priority: low
tags:
- handbook
- best-practices
suspect: false
links:
- target: REQ-026
  role: implements
- target: ARCH-020
  role: guided_by
- target: DDD-020
  role: specified_by
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:3e99768cf37d
---

# Bundle generic best-practice fallback for handbook generation

Create bundled generic best-practice YAML files that are copied as fallback when handbook generation is called without an LLM API key, so planning is never guidance-free.

## Acceptance Criteria

1. Given `specflow handbook generate plan-arc` called without an API key, when the command runs, then a generic phase-arc BP file is copied to the cache instead of returning an error.
2. Given the generic plan-arc BPs, when reviewed, then they contain 4-6 items covering component boundaries, error strategies, dependency documentation, and interface contracts.
3. Given the generic plan-ddd BPs, when reviewed, then they contain 4-6 items covering data structure typing, algorithm complexity, boundary error handling, and preconditions.
4. Given the generic plan-story BPs, when reviewed, then they contain 4-6 items covering vertical slicing, independent implementability, acceptance criteria depth, and sizing heuristics.
5. Given an existing cached BP file (user-edited), when generic fallback would copy, then the existing file is preserved (same skip-if-exists pattern).
