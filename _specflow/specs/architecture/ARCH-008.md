---
id: ARCH-008
title: V-Model Test Scaffolding Engine
type: architecture
status: implemented
priority: high
rationale: Generates deterministic test artifact stubs from implemented spec artifacts,
  wiring the V-model verification chain without LLM tokens
tags:
- testing
- vmodel
- scaffolding
- cli
suspect: false
links:
- target: REQ-013
  role: derives_from
- target: REQ-002
  role: derives_from
created: '2026-04-22'
fingerprint: sha256:beaa1348562b
version: 1
---

# V-Model Test Scaffolding Engine

The test scaffolding engine creates UT, IT, and QT stub artifacts from implemented spec artifacts using a deterministic type mapping with zero LLM tokens.

## Components

### Type Mapping (`commands/generate_tests.py`)

Three static dictionaries define the V-model left-right pairing:

| Spec Type | Test Prefix | Test Type |
|-----------|-------------|-----------|
| requirement | QT | qualification-test |
| architecture | IT | integration-test |
| detailed-design | UT | unit-test |

The canonical mapping (`V_MODEL_PAIRS`) lives in `lib/artifacts.py` and is shared with `find_missing_v_pairs()`, the coverage lint check, and `status.py`.

### Command Flow (`commands/generate_tests.py`)

1. **Discover**: Load all artifacts and build the ID index.
2. **Scope**: `--from DDD-001` for single artifact, no args for batch mode scanning all specs missing verification pairs.
3. **Duplicate prevention**: Scan all existing artifacts for `verified_by` links pointing to the source spec before creating.
4. **Creation**: Call `create_artifact()` with mapped test type, derived title, draft status, and `verified_by` link.
5. **Acceptance criteria propagation**: For QT stubs only, parse numbered items, bullets, and Given/When/Then lines from the REQ's Acceptance Criteria section into test case placeholders.

### Acceptance Criteria Extraction

A simple state-machine line parser scans for an "Acceptance Criteria" heading, collects numbered items (`1. ...`), bullet items (`- ...` / `* ...`), and BDD-style lines (`Given ...`, `When ...`, `Then ...`). Stops at the next heading or blank line after content.

## Architectural Decisions

- **Zero-token, fully deterministic**: Pure Python with no LLM calls. Type mapping is static, acceptance criteria extraction is regex-free line parsing.
- **V_MODEL_PAIRS as single source of truth**: Adding a new spec-test pair requires only updating this dict in `lib/artifacts.py`.
- **Duplicate prevention via link scanning**: O(N*M) where N = artifacts, M = links per artifact. Acceptable for filesystem-native corpus sizes.
- **Draft status for stubs**: Created stubs are `draft` — the `/specflow-execute` skill guides AI to populate them.

## Interfaces

| Interface | Direction | Purpose |
|-----------|-----------|---------|
| `specflow generate-tests [--from ID] [--dry-run]` | CLI | User-facing command |
| `create_artifact()` | Outbound | Shared artifact creation in `lib/artifacts.py` |
| `V_MODEL_PAIRS` | Inbound | Shared type mapping from `lib/artifacts.py` |
| `find_missing_v_pairs()` | Shared | Used by both `generate_tests` and `artifact-lint --type coverage` |
