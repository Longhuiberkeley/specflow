---
id: STORY-727
title: multi-host platform detection warning and refresh --all-platforms
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-063
  role: implements
- target: UT-049
  role: verified_by
created: '2026-07-10'
fingerprint: sha256:6fe0b8ef3ca3
modified: '2026-08-04'
output_files:
- tests/test_multi_platform.py
version: 1
---

# multi-host platform detection warning and refresh --all-platforms

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-063).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
