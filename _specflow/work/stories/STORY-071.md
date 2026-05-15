---
id: STORY-071
title: Adapt autonomous-loop-protocol.md from autoresearch_fork
type: story
status: implemented
priority: high
tags:
- autoresearch
- wave-3
- protocol
suspect: false
links:
- target: REQ-028
  role: implements
- target: DDD-025
  role: specified_by
- target: SPIKE-001
  role: depends_on
created: '2026-05-15'
---

# Adapt autonomous-loop-protocol.md from autoresearch_fork

## Outcome

`references/autonomous-loop-protocol.md` (~600 lines) adapted from the autoresearch_fork's 1030-line version.

## Adaptation map (full detail in DDD-025)

- **Preserved**: precondition checks, atomicity rules, commit/revert, verify/guard/noise handling, decision matrix, crash recovery, stuck detection
- **Modified**: Phase 1 (FIND + EXPT + git log read), Phase 7 (`specflow create` + LOOP update), Phase 8 (FIND authoring step)
- **Removed**: TSV append, state.json persistence, fresh-mode references

## Dependencies

- SPIKE-001 must complete first — it produces the concrete diff list

## Acceptance

- Each of the 8 phases has a clearly demarcated section
- Examples use `specflow create --type experiment ...` (not TSV append)
- Crash recovery still has the 3-attempt cap
- Stuck detection still triggers at 5 consecutive discards
- Atomicity 'one-sentence test' preserved verbatim
