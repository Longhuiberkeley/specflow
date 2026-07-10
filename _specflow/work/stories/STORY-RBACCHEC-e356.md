---
id: STORY-RBACCHEC-e356
title: 'rbac check command: author role resolution and transition authorization'
type: story
status: implemented
tags:
- v1.12.0
suspect: false
links:
- target: REQ-DEFERRED-5cea
  role: implements
created: '2026-07-10'
fingerprint: sha256:52d7c708196c
modified: '2026-07-10'
---

# rbac check command: author role resolution and transition authorization

## Description
Implements one of the six v1.12.0 deferred capabilities (see REQ-DEFERRED-5cea).

## Acceptance Criteria
1. Feature implemented per the parent REQ's matching criterion.
2. Covered by dedicated pytest tests via the real command path.
3. Entry points synced (cli-reference, skills, AGENTS.md) where applicable.
