---
id: REQ-TRANSCRI-24b7
title: "Transcript-mined CLI authoring ergonomics \u2014 wave 2 (v1.13.2)"
type: requirement
status: implemented
priority: high
rationale: 'Reduce repeated agent command friction without adding gates: ambiguous
  or corrupting writes fail loudly; guidance stays deterministic and advisory.'
tags:
- v1.13.2
- ergonomics
- accounting-not-policing
suspect: false
links:
- target: DEC-059
  role: derives_from
created: '2026-08-04'
fingerprint: sha256:7e2a7a6434b9
modified: '2026-08-04'
---

# Transcript-mined CLI authoring ergonomics — wave 2 (v1.13.2)

## Context

A corpus of ~1,558 real agent CLI invocations exposed recurring authoring friction after the v1.13.0/1 false-confidence cycle. This requirement extends DEC-059’s transcript-driven method to whole-body and AC editing, nested-map authoring, deterministic repair hints, report-only drift checks, and next-step decision accounting.

## Constraints

- No new blocking gates or mode toggles.
- No false or nondeterministic warnings.
- Ambiguous writes fail loudly rather than choosing silently.
- Zero external LLM calls; host-agnostic, git-only distribution.
- D-18 link vocabulary remains frozen.

## Acceptance Criteria

1. Given an agent needs to replace an artifact body or Acceptance Criteria section, when it uses the dedicated update surface, then the intended body scope changes and the fingerprint recomputes without clobbering unrelated sections.
2. Given an agent mistypes a status, frontmatter field, confidence option, or lint-repair command, when SpecFlow responds, then the guidance is deterministic, copy-paste-correct, and never fires on correct input.
3. Given fingerprint drift or unreviewed decisions exist, when the agent asks for status, then report-only accounting is fast, non-mutating, and counts each downstream artifact once.
4. Given two flags could write the same field, when both are supplied, then SpecFlow fails loudly rather than silently selecting precedence.
