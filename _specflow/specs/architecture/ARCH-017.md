---
id: ARCH-017
title: Spec Quality Gate
type: architecture
status: implemented
suspect: false
links:
- target: REQ-023
  role: derives_from
created: '2026-05-04'
modified: '2026-10-08'
fingerprint: sha256:31c6f8c5b9e4
thinking_techniques:
- assumption_surfacing
version: 2
---

# Spec Quality Gate

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-107); earlier text described separate `coverage-arch` / `story-min-ac` checks and tuple-returning check functions.

Extends the deterministic validation engine with body-content quality checks for architecture and detailed design artifacts. Ensures that spec artifacts contain substantive design content, not just valid frontmatter. The ARCH-coverage and minimum-AC rules are folded into the existing `coverage` and `story-size` checks rather than registered as checks of their own.

## Package Structure

```
src/specflow/commands/artifact_lint.py  — _check_spec_body() (check `spec-body`); ARCH-coverage rule inside check_coverage() (check `coverage`); minimum-AC rule inside _check_story_size() (check `story-size`)
src/specflow/lib/lint.py                — shared helpers used by these checks (count_acceptance_criteria_items)
```

## Component Responsibilities

1. **ARCH Body Validator**: Checks that architecture artifacts contain at least one structural section header (Interface, Component, Responsibility, Data Flow, Structure, Package, Module, Dependencies), finding `spec-body/headers`. Warns on bodies under 50 words (`_ARCH_MIN_WORDS`), finding `spec-body/word-count`.

2. **DDD Body Validator**: Checks that detailed design artifacts contain at least one design section header (Function, Data Structure, Algorithm, Error Handling, Invariant, Precondition, Signature, Implementation). Warns on bodies under 100 words (`_DDD_MIN_WORDS`). Same finding codes as the ARCH validator.

3. **REQ-to-ARCH Coverage Checker**: Part of `check_coverage()`: warns (`coverage/no-arch`) when an approved REQ has no refining ARCH, counting either the canonical `REQ refined_by ARCH` link or the legacy `ARCH derives_from REQ` link. A REQ that a STORY realises directly is tagged as the lean path (accounting, not a structural hole).

4. **Story Minimum AC Checker**: Part of `_check_story_size()`: warns `story-size/ac-min` when a draft or approved story has fewer than 2 acceptance criteria (counted by `lint.count_acceptance_criteria_items`), and `story-size/no-ac` when a story at any status has no Acceptance Criteria section.

## Interfaces

All checks return the shared check-result dict (`status_icon`, `detail`, `blocking_count`, `warning_count`, `findings`).

- `_check_spec_body(artifacts) -> dict` — the `spec-body` check in artifact_lint.py
- `check_coverage(artifacts, *, pre_planning=False) -> dict` — the `coverage` check, which carries the ARCH-coverage rule
- `_check_story_size(artifacts) -> dict` — the `story-size` check, which carries the minimum-AC rule

## Dependencies

- Existing `artifact_lint.py` check dispatch (`_run_check()`)
- Existing `artifacts.py` for body content extraction (`Artifact.body`)
- Existing `CHECK_NAMES` list and check registration (`spec-body`, `coverage`, `story-size` are all registered)

## Data Flow

1. `artifact-lint` invokes all registered checks, including `spec-body`, `coverage` and `story-size`
2. Each check reads artifact body content or links and applies type-specific patterns
3. Results merged into the existing lint report format as typed findings
4. These rules produce warnings only (`spec-body` always reports `blocking_count: 0`) to avoid breaking existing projects
