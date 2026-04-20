---
id: STORY-042
title: Add requirements quality lint check to artifact-lint
type: story
status: implemented
priority: high
tags:
- quality
- lint
- ears
suspect: false
links:
- target: REQ-010
  role: implements
- target: ARCH-001
  role: guided_by
created: '2026-04-21'
modified: '2026-04-21'
fingerprint: sha256:7753ffed1db4
---

# Add requirements quality lint check to artifact-lint

Add a zero-token quality check to artifact-lint that detects ambiguity words, passive voice, compound shall, and missing thresholds in REQ bodies.

## Description

A new `--type quality` check in artifact-lint performs regex analysis on REQ bodies to catch common requirement quality issues. This is the safety net that catches problems missed during authoring.

## Acceptance Criteria

1. Given REQ bodies with ambiguity words (e.g., "fast", "user-friendly"), when `specflow artifact-lint --type quality` is run, then those words are flagged as warnings
2. Given REQ bodies with passive voice patterns (e.g., "shall be validated"), when quality check runs, then passive voice is flagged
3. Given a REQ body with multiple "shall" in one sentence, when quality check runs, then compound shall is flagged
4. Given a REQ body with "shall respond quickly" and no quantitative threshold, when quality check runs, then missing threshold is flagged
5. Given quality check findings, when artifact-lint reports results, then all findings are warnings (non-blocking)
6. Given the full test suite, when `uv run pytest` is run, then all existing plus new tests pass

## Out of Scope

- Making quality checks blocking (future configuration)
- AI-based quality analysis (zero-token only)
- Changing existing REQ artifacts

## Dependencies

- STORY-041 (the ambiguity word list and patterns defined in normative-language.md inform the regex patterns)
