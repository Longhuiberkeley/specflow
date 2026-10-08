---
id: STORY-733
title: supersession status and supersedes role for REQ/ARCH/DDD schemas
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-063
  role: implements
- target: UT-053
  role: verified_by
created: '2026-07-10'
fingerprint: sha256:c5a67de7c67a
modified: '2026-08-04'
output_files:
- tests/test_supersession.py
version: 1
---

# supersession status and supersedes role for REQ/ARCH/DDD schemas

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-063).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
