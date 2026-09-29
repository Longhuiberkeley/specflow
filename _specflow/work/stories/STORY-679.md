---
id: STORY-679
title: check_coverage credits canonical REQ refined_by ARCH and STORY-to-test verified_by
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
- coverage
suspect: false
links:
- target: REQ-012
  role: implements
- target: REQ-053
  role: implements
created: '2026-09-30'
fingerprint: sha256:5dfece6babb5
modified: '2026-09-30'
output_files:
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/project_audit.py
- tests/test_coverage_semantics.py
- CHANGELOG.md
---

# check_coverage credits canonical REQ refined_by ARCH and STORY-to-test verified_by

## Acceptance Criteria
1. A REQ whose only ARCH link is the canonical refined_by shape is credited as architecturally covered.
2. A STORY whose only test link is its own outgoing verified_by is credited as verified.
3. A REQ covered only through derives_from produces an accounting-severity finding, never a blocking one.
4. The dogfood metric delta is recorded in a DEC citing REQ-012, and the CHANGELOG names it.
