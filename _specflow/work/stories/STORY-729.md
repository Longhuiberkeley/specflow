---
id: STORY-729
title: 'rbac check command: author role resolution and transition authorization'
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-063
  role: implements
- target: UT-051
  role: verified_by
created: '2026-07-10'
fingerprint: sha256:53e8886fd18e
modified: '2026-08-04'
output_files:
- src/specflow/commands/rbac_check.py
- tests/test_rbac_check.py
version: 1
---

# rbac check command: author role resolution and transition authorization

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-063).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
