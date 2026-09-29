---
id: STORY-678
title: format_version stamped on init and refresh, read-side warning, hook format
  guard
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
suspect: false
links:
- target: REQ-057
  role: implements
created: '2026-09-30'
fingerprint: sha256:1404a6a1036e
modified: '2026-09-30'
output_files:
- src/specflow/lib/config.py
- src/specflow/commands/refresh.py
- src/specflow/commands/hook.py
- src/specflow/cli.py
- tests/test_format_version.py
---

# format_version stamped on init and refresh, read-side warning, hook format guard

## Acceptance Criteria
1. init and refresh both stamp format_version: 1 into config.yaml; the legacy version key is untouched.
2. Any command run against a repo whose format_version exceeds the engine's supported value warns once with the exact upgrade instruction.
3. specflow hook pre-commit refuses on that mismatch with the same message.
4. Tests cover init, refresh, the warning, and the hook refusal.
