---
id: STORY-683
title: 'Fail loud: schema registration and audit lenses emit findings instead of swallowing
  errors'
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
- determinism
suspect: false
links:
- target: REQ-053
  role: implements
- target: REQ-052
  role: implements
created: '2026-09-30'
fingerprint: sha256:4d73cc41863f
modified: '2026-09-30'
output_files:
- src/specflow/lib/artifacts.py
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/project_audit.py
- tests/test_artifact_lint_schema_errors.py
- tests/test_project_audit_fail_loud.py
---

# Fail loud: schema registration and audit lenses emit findings instead of swallowing errors

## Acceptance Criteria
1. A malformed .specflow/schema/*.yaml produces a blocking schema-error finding naming the file, and the CLI exits non-zero.
2. A project-audit lens that raises produces a blocking lens-error finding naming the lens; the remaining lenses still run.
3. No try/except-pass wrapper remains around lens bodies.
4. Tests inject a malformed schema and a raising lens.
