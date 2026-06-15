---
id: ARCH-014
title: Test Engine
type: architecture
status: implemented
suspect: false
links:
- target: REQ-009
  role: derives_from
created: '2026-04-22'
modified: '2026-06-15'
fingerprint: sha256:dae45f1d864e
thinking_techniques: [assumption-surfacing]
---

# Test Engine

## Component

The test suite uses `pytest` as its runner and is located in `tests/`. Test modules mirror the library structure: `tests/test_artifacts.py`, `tests/test_lint.py`, `tests/test_rbac.py`, `tests/test_standards.py`, `tests/test_baselines.py`, and additional modules for newer features.

## Structure

- **Fixtures**: `tmp_path`-based fixtures create isolated filesystem environments for each test. Sample artifact files with valid YAML frontmatter are generated in temp directories, ensuring no global state leakage.
- **Test categories**: Unit tests cover individual lib functions (parsing, fingerprinting, link traversal, role resolution). Integration tests exercise multi-step workflows (scaffold → create artifact → lint → trace).
- **Determinism**: All tests run without network access, environment variables, or LLM calls. No `@pytest.mark.skip` for infrastructure reasons — every test must pass in CI.

## Responsibility

- Validates that `lib/artifacts.py` correctly parses YAML frontmatter, computes fingerprints, finds orphans, and detects missing V-model pairs.
- Validates that `lib/rbac.py` enforces solo-dev direct path, role-based authorization, and independence violation detection.
- Validates that `lib/standards.py` loads standards YAML and reports covered vs. uncovered clauses.
- Validates that `lib/lint.py` detects structural warnings (short bodies, missing headers, broken links).

## Dependencies

- `pytest` as the test runner (listed in `pyproject.toml` dev dependencies).
- `tmp_path` fixture for filesystem isolation.
- `src/specflow/lib/` modules under test — no mocking of internal modules; tests exercise real implementations against temp directories.
