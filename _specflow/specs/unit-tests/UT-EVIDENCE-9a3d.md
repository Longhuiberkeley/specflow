---
id: UT-EVIDENCE-9a3d
title: Evidence RTM includes mixed eligible REQ statuses
type: unit-test
status: implemented
suspect: false
links:
- target: STORY-KEEPRELE-37de
  role: verified_by
- target: REQ-015
  role: derives_from
created: '2026-08-05'
verify_command: uv run pytest tests/test_evidence.py -q
fingerprint: sha256:cd2ebadd80c8
verify_run_exit_code: 0
verify_run_out_hash: sha256:7167e1d35756
verify_run_at: '2026-08-04T16:36:30Z'
verify_run_git_ref: bf6ab086c91a3d0a1924ca0d8a708622a172db32
verify_run_command_hash: sha256:0f118b6156bf
modified: '2026-08-05'
---

# Evidence RTM includes mixed eligible REQ statuses

## Test Reference

- `tests/test_evidence.py::TestGenerateEvidenceReport::test_traceability_includes_mixed_eligible_statuses`

## Scope

Proves one verified requirement does not hide approved and implemented peers from the compliance evidence traceability matrix.

## Acceptance Criteria

1. The exact verify command exits 0.
2. Approved, implemented, and verified REQs all render in the report.
