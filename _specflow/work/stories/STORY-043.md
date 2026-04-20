---
id: STORY-043
title: Add coverage metrics to specflow status command
type: story
status: approved
priority: medium
tags:
- compliance
- reporting
- status
suspect: false
links:
- target: REQ-012
  role: implements
- target: ARCH-001
  role: guided_by
created: '2026-04-21'
---

# Add coverage metrics to specflow status command

Extend specflow status to compute and display REQ coverage, STORY test coverage, chain completeness, and gate pass rate.

## Description

The current status command shows artifact counts but no coverage metrics. This story adds a coverage dashboard section that computes percentage-based metrics from existing artifact data, all deterministically.

## Acceptance Criteria

1. Given approved REQs with linked stories, when `specflow status` is run, then REQ coverage percentage is displayed
2. Given implemented stories with UT/IT/QT links, when `specflow status` is run, then STORY test coverage percentage is displayed
3. Given approved specs with verification tests in their chains, when `specflow status` is run, then chain completeness percentage is displayed
4. Given no phase-gate checklists, when `specflow status` is run, then gate pass rate shows "N/A" or is omitted
5. Given the status command, when run, then exit code is always 0 (informational)
6. Given the full test suite, when `uv run pytest` is run, then all existing plus new tests pass

## Out of Scope

- Phase-gate pass rate computation (deferred until phase-gate checklists exist in the project)
- Compliance evidence reports (that is REQ-015)
- Machine-readable JSON output (that is REQ-016)

## Dependencies

- None
