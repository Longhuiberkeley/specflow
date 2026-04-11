---
id: STORY-006
title: Group stories into dependency-free waves for parallel execution
type: story
status: draft
priority: high
tags:
- execution
- orchestration
- P5
suspect: false
links:
- target: REQ-004
  role: implements
- target: ARCH-003
  role: guided_by
- target: DDD-002
  role: specified_by
created: '2026-04-11'
---

# Group stories into dependency-free waves for parallel execution

# Group stories into dependency-free waves for parallel execution

## Description

Implement the wave computation algorithm that analyzes story dependencies (via links) and groups them into waves where all stories within a wave can execute in parallel. This is the scheduling backbone of specflow go.

## Acceptance Criteria

1. Given 5 stories where STORY-002 depends on STORY-001 (derives_from link), and STORY-003, STORY-004, STORY-005 have no inter-story dependencies, when waves are computed, then Wave 1 contains [STORY-001, STORY-003, STORY-004, STORY-005] and Wave 2 contains [STORY-002]

2. Given stories with a diamond dependency (STORY-004 depends on STORY-002 and STORY-003, which both depend on STORY-001), when waves are computed, then Wave 1 = [STORY-001], Wave 2 = [STORY-002, STORY-003], Wave 3 = [STORY-004]

3. Given stories with a circular dependency (STORY-001 depends on STORY-002 which depends on STORY-001), when wave computation runs, then an error is reported listing the cycle and no waves are produced

4. Given all stories have no inter-story dependencies, when waves are computed, then all stories are placed in a single Wave 1

## Out of Scope

- Subagent spawning and context isolation (STORY-007)
- Lock handling during execution (uses STORY-005)

## Dependencies

- None (pure algorithm)
