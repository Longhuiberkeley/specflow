---
id: STORY-698
title: 'CI gate walks every commit: per-step legality, per-commit authority, rename-proof
  independence'
type: story
status: verified
tags:
- v1.17.0
- engine
- p1c
- ci-gate
suspect: false
links:
- target: REQ-008
  role: implements
- target: STORY-686
  role: depends_on
- target: DEF-002
  role: derives_from
- target: DEF-003
  role: derives_from
- target: DEF-016
  role: derives_from
created: '2026-09-30'
fingerprint: sha256:0588b0bca32d
modified: '2026-09-30'
output_files:
- src/specflow/commands/hook.py
- src/specflow/lib/rbac.py
- src/specflow/lib/git_utils.py
- tests/test_ci_gate_history.py
- tests/test_rbac.py
- tests/test_hook.py
---

# CI gate walks every commit: per-step legality, per-commit authority, rename-proof independence

## Acceptance Criteria

1. When team roles are configured, run_ci_gate walks each changed artifact's commits in base-to-head order and checks every consecutive status pair for schema legality: a pair is legal when a chain of single allowed_status steps reaches it, because one commit may record several legal CLI steps (cascade-status). With no roles configured the gate stays the solo-dev no-op; artifact-lint and update own solo legality.
2. Each transition is authorised against the author of the commit that made it, not the oldest author in the range, including every policy-gated status a single commit passes through.
3. check_independence follows renames or keys on the frontmatter id, so renumber-drafts cannot erase authorship.
4. An integration test with a temporary git repository reproduces DEF-002 (H1/H2) and DEF-003 (H3), and the cascade multi-step regression DEF-016, and then passes.
