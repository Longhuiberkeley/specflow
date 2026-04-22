---
id: ARCH-009
title: Provider-Agnostic CI Gate
type: architecture
status: implemented
priority: high
rationale: RBAC enforcement in CI must be provider-agnostic, using only git operations
  with provider-specific knowledge confined to adapter templates
tags:
- rbac
- ci
- adapters
suspect: false
links:
- target: REQ-008
  role: derives_from
- target: REQ-005
  role: derives_from
created: '2026-04-22'
fingerprint: sha256:76c8786760f1
version: 2
---

# Provider-Agnostic CI Gate

The CI gate enforces RBAC policies on artifact status transitions in pull requests, using only git operations. Provider-specific knowledge is confined to adapter templates.

## Components

### CI Gate Command (`commands/hook.py`)

`specflow ci-gate --base <ref> --head <ref>` performs server-side RBAC enforcement:

1. Run `git diff --name-only` between base and head refs, filter to `_specflow/**/*.md`.
2. Extract commit author email from `git log`.
3. For each changed file, parse frontmatter from both refs via `git show` to detect status transitions.
4. For each transition, call `authorize_status_transition()` to check team role policy.
5. For transitions to verification status, call `check_independence()` to block verifier == implementer.
6. Exit code 1 if any violations, code 0 otherwise.

### RBAC Engine (`lib/rbac.py`)

Shared between pre-commit hook and CI gate:

- `authorize_status_transition()`: Checks team role policy for allowed transitions.
- `check_independence()`: Uses `git log --format=%ae -- <filepath>` to verify the reviewer is not the same person who implemented the artifact.
- Solo-dev fast path: When no roles are configured, all transitions are allowed and independence checks are skipped.

### Adapter Framework (`lib/adapters/`)

Registry pattern with class decorators:

- `base.py`: `Adapter` ABC with `supported_operations` set and stub methods. `register_adapter` decorator adds concrete adapters to `ADAPTER_REGISTRY`.
- `github_actions.py`: Defines `_CI_GATE` as a raw YAML template using `${{ github.base_ref }}` and `${{ github.head_ref }}` expressions. String templates preserve GitHub Actions expressions that yaml.dump would escape.
- `__init__.py`: Imports adapter modules for self-registration. `load_adapters_config()` reads `.specflow/adapters.yaml`.

## Architectural Decisions

- **Provider-agnostic core**: `hook.py` uses only `git diff` and `git show`. No GitHub/GitLab APIs or environment variables.
- **Pre-commit hook reuse**: Both the pre-commit hook and CI gate share RBAC functions but differ in how they obtain transitions (staged index vs. git diff between refs).
- **Solo-dev fast path**: Zero configuration needed to opt out — when no roles are configured, all transitions are allowed.
- **String templates for YAML**: Raw Python strings preserve `${{ }}` expressions that YAML serialization would quote-escape.

## Interfaces

| Interface | Direction | Purpose |
|-----------|-----------|---------|
| `specflow ci-gate --base --head` | CLI | CI pipeline entry point |
| `authorize_status_transition()` | Internal | Shared RBAC policy check |
| `check_independence()` | Internal | Shared independence check |
| `specflow ci generate` | CLI | Generates CI workflow with gate job |
| `ADAPTER_REGISTRY` | Internal | Provider adapter registry |
