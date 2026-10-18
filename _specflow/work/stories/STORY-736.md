---
id: STORY-736
title: 'Test-only: lint negative fixtures (tests/test_lint_negative_fixtures.py)'
type: story
status: verified
suspect: false
links:
- target: REQ-065
  role: implements
created: '2026-10-17'
fingerprint: sha256:33ec90e5fb81
modified: '2026-10-17'
---

# Test-only: lint negative fixtures (tests/test_lint_negative_fixtures.py)

## Summary

Test-only change implementing the linked REQ: add `tests/test_lint_negative_fixtures.py`. No production-code change.

1. Rule-id enumeration parsed from src/specflow/commands/artifact_lint.py `_emit` literals — single source of truth, never a hand-copied list.
2. FIXTURES registry mapping each rule id to a builder that mutates a scaffolded project so exactly that rule fires (reusing the write_artifact / hand-written-invalid fixture patterns from tests/test_artifact_lint.py).
3. Two tests: `test_every_rule_id_has_a_fixture` (fails both directions — missing and stale ids) and `test_fixture_trips_its_rule` (parametrized over the registry; asserts the exact rule id appears in findings).

The module docstring carries the philosophy line with attribution: "A check that quietly matches nothing looks identical to a pass. Every rule id gets a fixture that must trip it." (pstack-claude tests/invariants.test.mjs).

## Acceptance Criteria

1. Given the rule-id set enumerated from artifact-lint source, when it is compared with the FIXTURES registry keys, then the sets are equal and any diff is reported by rule id.
2. Given each registered builder's mutated tree, when lint runs on it, then a finding with that exact rule id is present in the findings list.
3. Given the full test suite, when it runs, then it is green with the new module included and no change under src/specflow was needed.
