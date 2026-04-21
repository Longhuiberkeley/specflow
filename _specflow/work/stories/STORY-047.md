---
id: STORY-047
title: Enhance standards gap analysis with scoring, remediation, and JSON output
type: story
status: draft
priority: medium
tags:
- standards
- compliance
- gap-analysis
- json
suspect: false
links:
- target: REQ-016
  role: implements
- target: ARCH-004
  role: guided_by
created: '2026-04-22'
---

# Enhance standards gap analysis with scoring, remediation, and JSON output

Extend `specflow standards gaps` with coverage scoring, remediation suggestions, severity sorting, and machine-readable JSON output.

## Description

The current `specflow standards gaps` command lists uncovered clauses but provides no scoring, remediation guidance, or machine-readable output. This story enhances the existing `check_compliance()` function in `lib/standards.py` and the `standards_gaps` CLI command to add: per-standard coverage score as a percentage, remediation suggestions (which artifact type to create for each uncovered clause), severity-based sorting, summary dashboard, and `--json` flag.

## Acceptance Criteria

1. Given installed standards with partial coverage, when `specflow standards gaps` is run, then per-standard coverage score is displayed as a percentage
2. Given uncovered clauses with severity metadata, when the command runs, then gaps are sorted by severity (high → medium → low)
3. Given an uncovered clause with `category: safety`, when the command runs, then a remediation suggestion is shown (e.g., "Consider creating a requirement with tags: [hazard, safety]")
4. Given `specflow standards gaps --json`, when run, then output is valid JSON with standard, score, covered, uncovered, and remediation fields
5. Given a summary dashboard, when displayed, then it shows per-standard: total clauses, covered, uncovered, score
6. Given the full test suite, when `uv run pytest` is run, then all existing plus new tests pass

## Out of Scope

- AI-based remediation suggestions (rule-based only)
- Automatic artifact creation from gaps (user decision)
- New artifact types (that is REQ-017)

## Dependencies

- REQ-016 approved
- `lib/standards.py` check_compliance() exists
- `commands/standards_gaps.py` exists
