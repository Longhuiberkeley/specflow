---
id: STORY-728
title: 'phase-set command: reverse-lifecycle phase accounting'
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-063
  role: implements
- target: UT-050
  role: verified_by
created: '2026-07-10'
fingerprint: sha256:f34925825bf1
modified: '2026-08-04'
output_files:
- src/specflow/commands/phase_set.py
- src/specflow/commands/phase_status.py
- tests/test_phase_machine.py
version: 1
---

# phase-set command: reverse-lifecycle phase accounting

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-063).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
