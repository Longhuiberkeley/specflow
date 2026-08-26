---
id: STORY-640
title: 'v1.14.3: creation-status entry gates (CLI-level, --sanctioned)'
type: story
status: verified
tags:
- review-hardening
suspect: false
links:
- target: REQ-001
  role: implements
created: '2026-08-27'
fingerprint: sha256:82063a14c58d
authorization_note: UT+IT+QT contracts created and stamped green; full suite 1421
  green; gates clean (owner-pre-authorized overnight run 2026-08-27). Listed in morning
  report.
modified: '2026-08-27'
output_files:
- src/specflow/commands/create.py
- src/specflow/cli.py
- src/specflow/commands/handbook.py
- src/specflow/lib/lint.py
- src/specflow/templates/skills/shared/specflow-execute/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/references/escalation-and-promotion.md
- src/specflow/templates/skills/shared/specflow-references/references/bp-authoring.md
- docs/cli-reference.md
- tests/test_creation_status_gate.py
- tests/test_handbook.py
- tests/test_v1143_integration.py
version: 1
---

# v1.14.3: creation-status entry gates (CLI-level, --sanctioned)

`create --status` accepts any schema-allowed status (commands/create.py:225-237) and handbook generation writes BPs directly as approved (commands/handbook.py:43) — an approval-bypass side door. Deferred from v1.14.1 review.

## Acceptance Criteria

1. Gate at the CLI level only (commands/create.py); lib `create_artifact` API unchanged (trusted internal callers + test fixtures keep working).
2. Non-entry statuses (anything not the per-type root(s)) require `--sanctioned "justification"`; the justification is recorded in the artifact frontmatter.
3. Internal sanctioned callers handled deliberately: orphans.py:280 (adopt → approved backfill), autoresearch.py:405 (LOOP running start), reqif.py:90 (ALM import statuses), handbook.py:43 → FIX: generated BPs now draft; test_handbook.py:211-217 updated to track the intended change.
4. Shipped skill recipes + docs synced: specflow-execute/SKILL.md:81, specflow-discover/SKILL.md:124,178, escalation-and-promotion.md:31,37,43, bp-authoring.md:35, docs/cli-reference.md:225.
5. Guardrail test re-pinned to new expectations; CHANGELOG documents the intentional behavior change with --sanctioned as the migration path.
