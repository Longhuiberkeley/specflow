---
id: STORY-009
title: Implement proactive challenge engine for edge case discovery
type: story
status: draft
priority: medium
tags:
- challenge
- proactive
- review
- P5
suspect: false
links:
- target: REQ-004
  role: implements
- target: ARCH-002
  role: guided_by
- target: DDD-003
  role: specified_by
created: '2026-04-11'
---

# Implement proactive challenge engine for edge case discovery

# Implement proactive challenge engine for edge case discovery

## Description

Implement proactive challenge mode that asks 'What could go wrong? What is missing?' during artifact generation and before approval gates. Proactive challenges persist their findings (edge cases in story frontmatter, alternatives as DEC artifacts).

## Acceptance Criteria

1. Given a STORY artifact being reviewed with proactive checklist items (mode: proactive), when the LLM evaluates the story, then each branching path is enumerated (null input, external system down, out-of-order actions), and any path without defined handling is flagged as a finding

2. Given the proactive challenge finds 2 unhandled edge cases in STORY-001, when results are persisted, then STORY-001's frontmatter gains edge_cases_identified containing the 2 findings, and the checklist-log records the proactive items with their findings

3. Given a proactive challenge identifies 2 alternative approaches to an architectural decision, when the user reviews them, then a DEC (decision) artifact is created documenting the chosen approach, alternatives considered, and rationale

## Out of Scope

- Reactive/learned pattern extraction (STORY-010)
- Automated check execution (STORY-008 handles that)

## Dependencies

- STORY-008 (checklist assembly pipeline must exist)
