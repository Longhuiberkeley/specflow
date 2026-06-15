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
modified: '2026-05-04'
fingerprint: sha256:88f0010c1fb2
thinking_techniques: [assumption-surfacing]
---

# Spec Quality Gate

Extends the deterministic validation engine with body-content quality checks for architecture and detailed design artifacts. Ensures that spec artifacts contain substantive design content, not just valid frontmatter.

## Package Structure

```
src/specflow/commands/artifact_lint.py  — New check functions: spec-body, coverage-arch, story-min-ac
src/specflow/lib/lint.py                — Extended quality validation helpers
```

## Component Responsibilities

1. **ARCH Body Validator**: Checks that architecture artifacts contain at least one structural section header (Interface, Component, Responsibility, Data Flow, Structure, Package, Module, Dependencies). Warns on bodies under 50 words.

2. **DDD Body Validator**: Checks that detailed design artifacts contain at least one design section header (Function, Data Structure, Algorithm, Error Handling, Invariant, Precondition, Signature, Implementation). Warns on bodies under 100 words.

3. **REQ-to-ARCH Coverage Checker**: Extends `check_coverage()` to warn when an approved REQ has no ARCH artifact with a `derives_from` link pointing to it.

4. **Story Minimum AC Checker**: Extends `_check_story_size()` to warn when a story has fewer than 2 acceptance criteria or no Acceptance Criteria section at all.

## Interfaces

- `_check_spec_body(artifacts) -> (blocking, warnings, details)` — new check function in artifact_lint.py
- `_check_coverage_arch(artifacts) -> (blocking, warnings, details)` — extends coverage check
- `_check_story_min_ac(artifacts) -> (blocking, warnings, details)` — extends story size check

## Dependencies

- Existing `artifact_lint.py` check dispatch (`_run_check()`)
- Existing `artifacts.py` for body content extraction
- Existing `CHECK_NAMES` list and check registration

## Data Flow

1. `artifact-lint` invokes all registered checks including new ones
2. Each new check reads artifact body content, applies type-specific patterns
3. Results merged into existing lint report format
4. All new checks produce warnings (not blocking) to avoid breaking existing projects
