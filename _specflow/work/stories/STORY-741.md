---
id: STORY-741
title: Lint rules placeholder/unfilled and challenge/disposition-without-reason, CHL
  resolution field, legacy placeholder cleanup
type: story
status: verified
tags:
- core
- cli
- robustness
- review
suspect: false
links:
- target: REQ-067
  role: implements
created: '2026-10-18'
fingerprint: sha256:64dff80597e0
modified: '2026-10-18'
output_files:
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/generate_tests.py
- src/specflow/core/policy.py
- src/specflow/templates/schemas/challenge.yaml
- .specflow/schema/challenge.yaml
- tests/test_lint_negative_fixtures.py
- tests/test_lint_placeholder_disposition.py
- src/specflow/templates/skills/shared/specflow-artifact-review/SKILL.md
- .claude/skills/specflow-artifact-review/SKILL.md
- docs/cli-reference.md
thinking_techniques:
- worst_case_user
- composition
version: 1
---

# Lint rules placeholder/unfilled and challenge/disposition-without-reason, CHL resolution field, legacy placeholder cleanup

## Summary

Two accounting lint rules plus the ledger cleanup. (1) Hoist the generator placeholder at src/specflow/commands/generate_tests.py:94 into a module constant `PLACEHOLDER_TEST_CASES` and add `_check_placeholders` to src/specflow/commands/artifact_lint.py (CHECK_NAMES entry `placeholders`, rule id `placeholder/unfilled`, warning, dedicated check so it never routes through schema → project-audit consistency → exit 2): scan every artifact whose status is past `draft`, skip fenced code blocks and inline code spans, emit one finding per artifact. (2) Add optional `resolution` to the challenge schema (`.specflow/schema/challenge.yaml` and `src/specflow/templates/schemas/challenge.yaml`, byte-identical) and `_check_challenge_disposition` (CHECK_NAMES `challenge-disposition`, rule id `challenge/disposition-without-reason`, warning) firing on `accepted` CHLs whose `resolution` is missing or empty. Register both rule ids with builders in tests/test_lint_negative_fixtures.py and add positive tests (fenced placeholder not flagged; draft not flagged; resolution set not flagged). (3) Replace the placeholder in all 20 affected test specs (18 verified, 2 draft — enumerate with grep) with real test-case lists derived from the linked STORY/REQ acceptance criteria, refreshing fingerprints through `specflow fingerprint-refresh`. (4) Update the artifact-review SKILL.md report step so disposing a finding records the reason: `specflow update <CHL> --status accepted --set resolution="<why>"`; mirror both trees. The 90 legacy CHLs are NOT backfilled (they are history); the rule applies going forward and the baseline accepts them via `findings-baseline update --accept-new` only if the owner agrees — otherwise scope the rule to CHLs modified after the schema change date. Prefer the scoped rule: fire only when `modified` (or `created`) is on or after the date the field shipped, read from the schema file's `resolution_since` key.

## Acceptance Criteria

1. Given a `verified` UT whose body contains the placeholder line, when `artifact-lint` runs, then one `placeholder/unfilled` warning names it; given the same line inside a fenced block or in a `draft` artifact, then none.
2. Given an `accepted` CHL created after `resolution_since` with no `resolution`, when `artifact-lint` runs, then one `challenge/disposition-without-reason` warning names it; given `resolution` set, or a CHL older than `resolution_since`, then none.
3. Given tests/test_lint_negative_fixtures.py, when it runs, then both rule ids trip their fixtures and the both-directions coverage test passes.
4. Given this repository, when `artifact-lint --type placeholder` runs after the cleanup, then it emits zero `placeholder/unfilled` findings (artifacts that merely quote the placeholder in inline code, such as REQ-067, are not findings).
5. Given both schema copies, when diffed, then they are identical and `specflow schema challenge` lists `resolution`.
