---
id: STORY-643
title: 'v1.15.0: OpenCode native commands (harness-level, deferred per owner 2026-08-27)'
type: story
status: draft
tags:
- v1.15.0-backlog
suspect: false
links:
- target: REQ-001
  role: implements
created: '2026-08-27'
fingerprint: sha256:1f7ed654008d
modified: '2026-09-13'
---

# v1.15.0: OpenCode native commands (harness-level, deferred per owner 2026-08-27)

Deferred per owner decision 2026-08-27 (delay harness-level customization; generalized core first). Ship OpenCode-native commands/tools instead of relying solely on the shared .claude/skills tree (see STORY-632 out-of-scope, DEC-077 host model).

## Acceptance Criteria

1. OpenCode hosts get native commands/tools in addition to the shared skills tree, installed by init/refresh for that platform.
2. Skill delivery on the other hosts is unchanged (mirror byte-equality guards still pass).
