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
fingerprint: sha256:2f37303ac6d9
version: 1
thinking_techniques:
- worst_case_user
- composition
modified: '2026-09-13'
output_files:
- src/specflow/commands/refresh.py
- tests/test_refresh_lints.py
---

# Refresh active pack assets safely

Refresh configured active-pack schemas, skills, checklists, and context safely. Acceptance: preview changes; preserve _specflow artifacts; require force for ambiguous user edits; keep context idempotent; cover behavior with tests.

## Acceptance Criteria

1. `specflow refresh` previews every schema/skill/checklist/context change before writing anything.
2. Local `_specflow/` artifacts are never modified by a pack-asset refresh.
3. A locally edited shipped asset is preserved by default and replaced only under explicit `--force`.
4. Re-running refresh is idempotent: a second run reports nothing to change.
5. Behavior is pinned by tests/test_refresh_lints.py.
