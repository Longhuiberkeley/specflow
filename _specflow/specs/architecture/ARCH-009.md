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
fingerprint: sha256:8110e43064fb
thinking_techniques:
- assumption_surfacing
- devils_advocate
- red_blue_team
version: 4
modified: '2026-10-08'
---

# Provider-Agnostic CI Gate

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-030); earlier text described ci-gate as one net base-to-head diff and a workflow that passed `head_ref`.

The CI gate enforces RBAC policies on artifact status transitions in pull requests, using only git operations. Provider-specific knowledge is confined to adapter templates.

## Components

### CI Gate Command (`commands/hook.py`)

`specflow ci-gate --base <ref> --head <ref>` (both flags required; `_add_ci_gate_parser` in `cli.py`, dispatched by `cmd_ci_gate` to `hook.run_ci_gate`) performs server-side RBAC enforcement. Since STORY-698 a pull request is evaluated as a history of commits, not as one net diff:

1. Run `git diff --name-only <base>...<head>` and keep `_specflow/**/*.md` paths, skipping files whose name starts with `_` (directory indexes).
2. For each changed artifact, `_status_steps()` walks the commits in `base..head` that touched it, oldest first, through `git_utils.file_history()` (`git log --follow`, so renumber renames are followed). Each commit whose frontmatter status differs from its parent's (both read with `git show <ref>:<path>`) becomes one step `{sha, author, old, new, type, path}`. If the walk does not arrive at the head status, one closing step is charged to the newest commit author in the range.
3. When team roles are configured, `_illegal_step_reason()` checks each step against the type's `allowed_status` map in `.specflow/schema/`. The new status must be reachable from the old one by a chain of legal single transitions (`_legal_path()`), because one commit may record several CLI steps. `_intermediate_authority_reason()` then charges every policy-gated status passed through on that chain to the same commit's author.
4. `rbac.authorize_status_transition()` checks that commit's author against the team role policy for the new status.
5. `rbac.check_independence(..., upto=<sha>)` blocks the commit's author from setting a verification status on a file they committed to earlier. Only strict ancestors of that commit count as prior implementation.
6. Each violation is printed with its commit sha. Exit code 1 if any violation, 0 otherwise.

### RBAC Engine (`lib/rbac.py`)

Shared between pre-commit hook and CI gate:

- `authorize_status_transition(root, artifact_id, new_status, author_email)`: looks up `team.policy.transitions` in config for the roles allowed to set `new_status` and checks the author's roles (`resolve_author_roles()`).
- `check_independence(root, artifact_file, new_status, author_email, upto=None)`: reads the file's author history with `git_utils.file_history()` (`git log --follow`) and rejects an author who already appears in it when `new_status` is in `team.policy.verification_statuses` (default `["verified"]`).
- Solo-dev fast path: when no role has members (`_has_configured_roles()`), all transitions are allowed, independence is not checked, and the CI gate also skips its schema-legality check.

### Adapter Framework (`lib/adapters/`)

Registry pattern with class decorators:

- `base.py`: `Adapter` ABC with `name`, a `supported_operations` set, and stub methods that raise `NotImplementedError` unless overridden (`generate_ci_workflow`, `import_artifacts`, `export_artifacts`, `ingest_standard`, `get_hook_script`). The `register_adapter` decorator adds concrete adapters to `ADAPTER_REGISTRY`, and `get_adapter(name)` instantiates one.
- `github_actions.py`: `_CI_GATE` is a raw YAML string for a pull-request-only job (`fetch-depth: 0`) that runs `uvx --from <git source> specflow ci-gate --base origin/${{ github.base_ref }} --head ${{ github.event.pull_request.head.sha }}`. String templates preserve GitHub Actions expressions that yaml.dump would escape. The `__SPECFLOW_SOURCE__` sentinel is replaced with the version-pinned Git source (`_specflow_source()`).
- `__init__.py`: imports the adapter modules so they self-register. `load_adapters_config()` reads `.specflow/adapters.yaml` and falls back to `DEFAULT_ADAPTERS_CONFIG`.

## Architectural Decisions

- **Provider-agnostic core**: `hook.py` uses only git (`git diff`, `git log`, `git show`, `git merge-base`). No GitHub/GitLab APIs or environment variables.
- **History, not net diff** (STORY-698): a net diff hides an unauthorised intermediate approval and an illegal hidden step, so each commit's step is judged against that commit's author.
- **Pre-commit hook reuse**: Both the pre-commit hook and CI gate share RBAC functions but differ in how they obtain transitions (the staged index via `rbac.staged_artifact_changes()` vs. the per-commit walk between refs).
- **Solo-dev fast path**: Zero configuration needed to opt out — when no roles are configured, all transitions are allowed.
- **String templates for YAML**: Raw Python strings preserve `${{ }}` expressions that YAML serialization would quote-escape.

## Interfaces

| Interface | Direction | Purpose |
|-----------|-----------|---------|
| `specflow ci-gate --base <ref> --head <ref>` | CLI | CI pipeline entry point (per-commit history walk) |
| `authorize_status_transition()` | Internal | Shared RBAC policy check |
| `check_independence()` | Internal | Shared independence check |
| `specflow ci generate [--force] [--dry-run]` | CLI | Writes `.github/workflows/specflow.yml` from `adapters.yaml`; includes the gate job when `ci-gate` is listed |
| `ADAPTER_REGISTRY` | Internal | Provider adapter registry |
