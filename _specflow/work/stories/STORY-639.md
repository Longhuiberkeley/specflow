---
id: STORY-639
title: 'v1.14.3: role-target semantic matrix (accounting-only)'
type: story
status: verified
tags:
- review-hardening
suspect: false
links:
- target: REQ-003
  role: implements
created: '2026-08-27'
fingerprint: sha256:c1449897c460
authorization_note: UT+IT+QT contracts created and stamped green; full suite 1421
  green; gates clean (owner-pre-authorized overnight run 2026-08-27). Listed in morning
  report.
modified: '2026-08-27'
output_files:
- src/specflow/lib/role_targets.py
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/update.py
- src/specflow/commands/create.py
- src/specflow/cli.py
- tests/test_role_targets.py
- tests/test_v1143_integration.py
version: 1
---

# v1.14.3: role-target semantic matrix (accounting-only)

Schemas list allowed link roles per SOURCE type but never validate target types (lint.py:155-193 checks role names only; deferred from STORY-634). Structurally valid nonsense (`implements` → a test) is accepted silently.

## Acceptance Criteria

1. Data-driven source-type × role → allowed-target-types matrix, derived from/reusing the existing type-pair constants (`_SPEC_LEVEL`/`_TEST_TYPES`/`_WORK_TO_SPEC_ROLES` etc. in artifacts.py) — one source of truth, declared cousin of the deferred chain-depth unification.
2. `complies_with` exempts standard-clause targets (ISO-14971 shape); `verified_by` allows both legal shapes (test→STORY and test→REQ/ARCH/DDD).
3. `artifact-lint` emits a role-target warning collapsed per-artifact/per-role with a repair hint.
4. CRITICAL: warnings are accounting-only — they must NOT feed project-audit `consistency`/exit-2 escalation. Test asserts project-audit exit code is unchanged when role-target warnings exist.
5. Opt-in `lint.role_target_strict` (default false) escalates to blocking; both modes tested.
6. Validation corpus includes research/ops-shaped fixtures (EXPT/LOOP/FIND/COMP incl. legacy-link shapes) — dogfood has zero EXPTs.
