---
id: STORY-083
title: Refresh active pack assets safely
type: story
status: verified
tags:
- autoresearch
- pack-system
- refresh
- v1.12.5
suspect: false
links:
- target: REQ-032
  role: implements
- target: ARCH-022
  role: specified_by
created: '2026-08-02'
fingerprint: sha256:b6acee5be483
version: 1
thinking_techniques:
- worst_case_user
- composition
modified: '2026-08-02'
output_files:
- src/specflow/commands/refresh.py
- tests/test_refresh_lints.py
---

# Refresh active pack assets safely

Refresh configured active-pack schemas, skills, checklists, and context safely. Acceptance: preview changes; preserve _specflow artifacts; require force for ambiguous user edits; keep context idempotent; cover behavior with tests.
