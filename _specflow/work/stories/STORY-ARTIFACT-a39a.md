---
id: STORY-ARTIFACT-a39a
title: 'artifact-lint quality gates: empty-AC error and NFR threshold warning'
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-DEFERRED-5cea
  role: implements
created: '2026-07-10'
fingerprint: sha256:e45e9f28f9d1
modified: '2026-07-10'
output_files:
- tests/test_lint_quality_gates.py
---

# artifact-lint quality gates: empty-AC error and NFR threshold warning

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-DEFERRED-5cea).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
