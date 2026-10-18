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
modified: '2026-10-08'
fingerprint: sha256:ca97e08b69f1
thinking_techniques:
- assumption_surfacing
version: 3
---

# Test Engine

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-106); earlier text named a nonexistent tests/test_lint.py and claimed no skips and no mocking.

## Component

The test suite uses `pytest` as its runner and is located in `tests/` (`testpaths = ["tests"]` in `pyproject.toml`). Test modules mirror the library structure: `tests/test_artifacts.py`, `tests/test_artifact_lint.py` (with `tests/test_lint_*.py` and `tests/test_quality_lint.py`), `tests/test_rbac.py`, `tests/test_standards.py`, `tests/test_baselines.py`, and additional modules for newer features (for example `tests/test_ci_gate_history.py`).

## Structure

- **Fixtures**: `tmp_path`-based fixtures create isolated filesystem environments for each test. `tests/conftest.py` provides `write_artifact()`, which scaffolds fixture artifacts through the production writer (`art_lib.create_artifact`) so the index, fingerprint and frontmatter match what the CLI writes; fixtures that must be invalid on purpose are written by hand in the test that needs them.
- **Test categories**: Unit tests cover individual lib functions (parsing, fingerprinting, link traversal, role resolution). Integration tests exercise multi-step workflows (scaffold → create artifact → lint → trace).
- **Determinism**: Tests make no LLM or external API calls. Skips are environment- or parametrization-driven, never silent failures: a missing host tool (`git`, `bash` or `uv` not on PATH), a missing checkout asset (the live `.specflow/checklists`, the dogfood `_specflow/` tree, or a reachable `v*` release tag for the brownfield-upgrade test), POSIX-only lock tests skipped on Windows, and checklist-corpus parametrized cases that do not apply to a file (project-wide or not type-routed categories).

## Responsibility

- Validates that `lib/artifacts.py` correctly parses YAML frontmatter (`parse_artifact`), computes fingerprints (`compute_fingerprint`), finds orphans (`find_orphans`), and detects missing V-model pairs (`find_missing_v_pairs`).
- Validates that `lib/rbac.py` enforces solo-dev direct path, role-based authorization, and independence violation detection.
- Validates that `lib/standards.py` loads standards YAML and reports covered vs. uncovered clauses (`check_compliance`).
- Validates the artifact-lint stack: the `lib/lint.py` validators (schema, status hierarchy, fingerprint, acceptance criteria) and the checks in `commands/artifact_lint.py` (broken links, spec-body and the rest of `CHECK_NAMES`).

## Dependencies

- `pytest` as the test runner (the `dev` dependency group in `pyproject.toml`).
- `tmp_path` fixture for filesystem isolation.
- `src/specflow/lib/` modules under test, exercised against temp directories. Some tests use `monkeypatch` to stub a function or set an environment variable.
