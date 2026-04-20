---
id: STORY-039
title: Create pytest test suite for core lib modules
type: story
status: approved
priority: medium
tags:
- testing
- quality
suspect: false
links:
- target: REQ-009
  role: implements
created: '2026-04-20'
modified: '2026-04-20'
---

# Create pytest test suite for core lib modules

## Description

Create a `tests/` directory with pytest test modules covering the core SpecFlow library: `lib/artifacts.py`, `lib/rbac.py`, `lib/standards.py`, and `lib/baselines.py`. Add `pytest` as a dev dependency in `pyproject.toml`.

## Acceptance Criteria

1. Given the `tests/` directory with all test files, when running `uv run pytest tests/`, then pytest discovers and executes all tests and reports 0 failures

2. Given `tests/test_artifacts.py`, when the test module is inspected, then it covers compute_fingerprint, parse_artifact, find_orphans, find_missing_v_pairs, trace_chain, and compute_chain_depth

3. Given `tests/test_rbac.py`, when the test module is inspected, then it covers solo-dev fast path, role authorization with authorized and unauthorized users, and independence checking

4. Given `tests/test_standards.py`, when the test module is inspected, then it covers standards listing, loading, and gap analysis

5. Given `tests/test_baselines.py`, when the test module is inspected, then it covers baseline creation, immutability, loading, and diff computation

6. Given `pyproject.toml`, when the `[dependency-groups]` section is inspected, then `pytest` is listed as a dev dependency

7. Given any test in the suite, when executed, then it requires no network access, no LLM calls, and produces deterministic results

## Out of Scope

- CLI command integration tests (trace, ci-gate, artifact-lint)
- Performance or stress tests
- Mutation testing or coverage enforcement

## Dependencies

- REQ-009 must be approved
- Core lib modules must be importable from the specflow package
