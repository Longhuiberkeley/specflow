---
id: STORY-020
title: Implement dead code and code similarity detection for project hygiene
type: story
status: draft
priority: low
tags:
- intelligence
- analysis
- P8
suspect: false
links:
- target: REQ-004
  role: implements
- target: ARCH-001
  role: guided_by
created: '2026-04-11'
---

# Implement dead code and code similarity detection for project hygiene

# Implement dead code and code similarity detection for project hygiene

## Description

Implement specflow detect dead-code and specflow detect similarity commands that analyze the project source for unreachable/uncalled code and highly similar code blocks. Results are surfaced as informational warnings, not blocking. Implemented in Python lib/analysis.py using AST analysis.

## Acceptance Criteria

1. Given a Python project with 3 functions that are defined but never called from any module, when specflow detect dead-code runs, then the 3 functions are listed with their file paths and line numbers as informational warnings

2. Given a project with two code blocks that are 90% identical (copy-paste pattern), when specflow detect similarity runs, then the pair is flagged with their file paths, line ranges, and a similarity percentage

3. Given specflow detect dead-code runs on a project with no dead code, then the output shows 'No dead code detected' and returns exit code 0 with no false positives for framework entry points or plugin hooks

## Out of Scope

- Automatic refactoring suggestions
- Cross-language analysis (Python only for MVP)

## Dependencies

- None
