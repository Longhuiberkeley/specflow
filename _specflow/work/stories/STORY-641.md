---
id: STORY-641
title: 'v1.14.3: guardrail-test assertion hardening (chore)'
type: story
status: verified
tags:
- review-hardening
suspect: false
links:
- target: REQ-009
  role: implements
created: '2026-08-27'
fingerprint: sha256:60ef394e36f9
authorization_note: UT+IT+QT contracts created and stamped green; full suite 1421
  green; gates clean (owner-pre-authorized overnight run 2026-08-27). Listed in morning
  report.
modified: '2026-08-27'
output_files:
- tests/test_approval_guardrail.py
- src/specflow/templates/skills/shared/specflow-artifact-review/SKILL.md
- tests/test_v1143_integration.py
version: 1
---

# v1.14.3: guardrail-test assertion hardening (chore)

tests/test_approval_guardrail.py:45,90-104 use broad substring assertions (e.g. 'walk' in lowered; any text containing 'only'+'user'+'confirm') that can pass on unrelated phrases. Tighten to anchored word-boundary/section-scoped regex assertions. No product change; no test weakened.

## Acceptance Criteria

1. Loose assertions replaced with anchored, section-scoped or word-boundary regex checks that cannot pass on unrelated phrase matches.
2. All guardrail tests still pass against current (compliant) skills; a mutation check demonstrates at least one previously-passing bogus phrase now fails.
