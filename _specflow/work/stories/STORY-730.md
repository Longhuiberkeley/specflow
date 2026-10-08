---
id: STORY-730
title: 'rtm command: bidirectional requirements traceability matrix'
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-063
  role: implements
- target: UT-052
  role: verified_by
created: '2026-07-10'
fingerprint: sha256:3a22ec75a25c
modified: '2026-08-04'
output_files:
- src/specflow/commands/rtm.py
version: 1
---

# rtm command: bidirectional requirements traceability matrix

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-063).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
