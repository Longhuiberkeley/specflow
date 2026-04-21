---
id: STORY-046
title: Add compliance evidence report to specflow ship
type: story
status: implemented
priority: medium
tags:
- compliance
- reports
- shipping
- evidence
suspect: false
links:
- target: REQ-015
  role: implements
- target: ARCH-004
  role: guided_by
- target: ARCH-005
  role: guided_by
created: '2026-04-22'
modified: '2026-04-22'
fingerprint: sha256:307c26741722
---

# Add compliance evidence report to specflow ship

Add `--evidence` flag to the ship workflow that generates a deterministic compliance evidence report alongside the baseline.

## Description

When shipping a release in a regulated context, teams need documented evidence that requirements were implemented, tested, and verified. This story adds a Markdown evidence report that aggregates existing artifact data — traceability chains, test status, baseline snapshot, and standards compliance — into a single file suitable for inclusion in a DHF or Technical File.

The report generator is a new module (`lib/evidence.py` or similar) that composes data from existing functions: `trace_chain()` for traceability, artifact status for test results, `load_baseline()` / `diff_baselines()` for baseline data, and `check_compliance()` for standards coverage.

## Acceptance Criteria

1. Given `specflow ship --evidence`, when the command runs, then a Markdown evidence report is generated in `.specflow/baselines/` alongside the baseline
2. Given verified REQs, when the report is generated, then it includes a traceability matrix showing REQ → ARCH → DDD → UT/IT/QT chains
3. Given test artifacts with status, when the report is generated, then it includes a test results summary (pass/fail per test)
4. Given a baseline and its predecessor, when the report is generated, then it includes the baseline snapshot with diff from previous
5. Given installed standards, when the report is generated, then it includes per-standard coverage (covered/uncovered clauses)
6. Given the full test suite, when `uv run pytest` is run, then all existing plus new tests pass

## Out of Scope

- Audit trail with timestamps per status transition (requires git blame integration, deferred)
- PDF or HTML output formats (Markdown only)
- AI-assisted report summarization (zero-token only)

## Dependencies

- REQ-015 approved
- `specflow ship` command exists
- `lib/baselines.py`, `lib/standards.py`, `lib/artifacts.py` available
