---
id: STORY-699
title: 'Verification evidence semantics: one expected-exit helper, dead-oracle finding,
  QT-011 repointed'
type: story
status: verified
tags:
- v1.17.0
- engine
- p1c
- verification
suspect: false
links:
- target: REQ-058
  role: implements
- target: ARCH-026
  role: specified_by
- target: DEF-004
  role: derives_from
- target: DEF-005
  role: derives_from
- target: DEF-017
  role: derives_from
created: '2026-09-30'
fingerprint: sha256:8b73ef40eb48
modified: '2026-09-30'
output_files:
- src/specflow/lib/verification.py
- src/specflow/lib/evidence.py
- src/specflow/lib/risk.py
- src/specflow/commands/brief.py
- src/specflow/commands/project_audit.py
- src/specflow/commands/artifact_lint.py
- src/specflow/lib/evaluator_fingerprint.py
- tests/test_run_matches_expected.py
- tests/test_dead_oracle.py
- tests/test_verify_expected_exit_cli.py
---

# Verification evidence semantics: one expected-exit helper, dead-oracle finding, QT-011 repointed

## Acceptance Criteria

1. One run_matches_expected helper decides pass or fail from the declared verify_exit_code (default 0) and brief, evidence, risk tier and project audit all call it.
2. A verify_command token that looks like a repository path and does not exist yields a dead-oracle accounting finding; it never blocks, including under the STORY-663 persistent-warning escalation of full artifact-lint runs.
3. QT-011 cites an existing test; DEF-004 (readers disagree on the expected exit code, planned label DEF-010), DEF-005 (QT-011 dead oracle, planned label DEF-012) and DEF-017 (dead-oracle escalated to blocking) are filed from failing tests and closed.
4. Tests cover unset, zero and non-zero declared codes for every reader.
