---
id: STORY-662
title: 'hook.py: route failures to artifact-lint subcommands; fix RBAC copy'
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:5c5250f342f5
modified: '2026-09-13'
---

# hook.py: route failures to artifact-lint subcommands; fix RBAC copy

Per SPIKE-002 STORY-7 section; removes the --no-verify teaching.

## Acceptance Criteria

1. Link/schema hook failures name `specflow artifact-lint --type links|schema` and stop — the hook no longer teaches `--no-verify`.
2. RBAC failures read "local hook blocked this transition; durable enforcement is hosting-side".
3. Suspect warnings stay conditional and ID-exact.
4. tests/test_hook.py pins each message.
