---
id: STORY-057
title: Add story dependency cycle detection to artifact-lint
type: story
status: implemented
priority: low
tags:
- lint
- waves
- plan
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
fingerprint: sha256:d21a286a3111
---

# Add story dependency cycle detection to artifact-lint

Add a lint check that detects circular dependencies between stories by running wave computation during lint, catching cycle issues at planning time instead of execution time.

## Acceptance Criteria

1. Given stories with no circular dependencies, when `artifact-lint` runs the `wave-cycles` check, then no warnings are produced and the wave count is reported as informational.
2. Given stories A depends on B, B depends on A, when `artifact-lint` runs, then a warning reports the circular dependency with both story IDs.
3. Given a story with 4 or more dependencies, when `artifact-lint` runs, then a warning suggests restructuring the story.
4. Given stories with valid dependency ordering, when `artifact-lint` runs, then the wave report shows stories grouped by execution wave.
