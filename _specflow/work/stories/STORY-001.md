---
id: STORY-001
title: Detect fingerprint changes and propagate suspect flags for downstream artifacts
type: story
status: draft
priority: high
tags:
- traceability
- impact
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
---

# Detect fingerprint changes and propagate suspect flags for downstream artifacts

# Detect fingerprint changes and propagate suspect flags for downstream artifacts

## Description

Implement the core impact analysis engine: when an artifact's body content changes, recompute its fingerprint, propagate suspect: true to all downstream-linked artifacts, bump version, and create an impact-log event file. This is the foundation of SpecFlow's traceability system.

## Acceptance Criteria

1. Given REQ-001 with body text 'The system SHALL provide a CLI', and ARCH-001 links to REQ-001 via derives_from, when REQ-001's body text is changed to 'The system SHOULD provide a CLI', then running specflow validate detects the fingerprint mismatch, updates REQ-001's fingerprint, sets ARCH-001's suspect to true, bumps REQ-001's version by 1, and creates an impact-log event file in .specflow/impact-log/

2. Given an artifact with no downstream links (nothing references it), when its body content changes, then the fingerprint is updated and version bumped, but no suspect flags are propagated and the impact-log event shows an empty flagged_suspects list

3. Given a chain REQ-001 -> ARCH-001 -> DDD-001 (each downstream links to the one above), when REQ-001 changes, then ARCH-001 is flagged suspect but DDD-001 is NOT flagged suspect in this single pass (propagation is one hop, not transitive, unless ARCH-001 is also recomputed and changed)

4. Given an artifact file with malformed YAML frontmatter (missing closing delimiter), when fingerprint validation runs, then the file is skipped with a warning logged and other artifacts continue processing normally

## Out of Scope

- Typo cascade defense (separate story)
- Split/merge operations (separate story)
- The specflow impact CLI command (separate story)

## Dependencies

- None (foundation story)
