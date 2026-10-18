---
id: ARCH-016
title: Init Upgrade Engine
type: architecture
status: implemented
suspect: false
links:
- target: REQ-022
  role: derives_from
created: '2026-05-04'
modified: '2026-10-08'
fingerprint: sha256:4786f4789922
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 2
---

# Init Upgrade Engine

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-032); earlier text described a release-version stamp with `read_version`/`merge_schemas` helpers and a reported version delta.

Provides safe re-initialization of SpecFlow projects by preserving existing user state while applying framework updates. Manages the config format-version stamp, configuration merging, and non-destructive schema copying; `init --force` is the explicit, backed-up reset path.

## Package Structure

```
src/specflow/commands/init.py     — run(): re-init detection (config.yaml present), merge path, --force backup + reset path
src/specflow/lib/config.py        — merge_config(), FORMAT_VERSION helpers, backup_specflow_internals()
src/specflow/lib/scaffold.py      — create_internal_dirs(overwrite_schemas=...), backup_run_dir()
src/specflow/commands/refresh.py  — stamps format_version / strips the legacy version key on `specflow refresh`
```

## Component Responsibilities

1. **Format-Version Stamp**: config.yaml carries an integer `format_version` (`FORMAT_VERSION = 1` in lib/config.py), not the release version. `merge_config` drops the legacy top-level `version` key and stamps `format_version` when it is missing or lower. `specflow refresh` applies the same upgrade in place via `stamp_format_version` and `strip_legacy_version`. When a repo's `format_version` exceeds `SUPPORTED_FORMAT_VERSION`, `format_version_mismatch` builds an upgrade message that the CLI prints once per process (`warn_format_version_once`) and the hook command also checks. Re-init reports the top-level config fields it added (`New config fields added: ...`), not a version delta.

2. **Config Merger**: `merge_config(existing, defaults)` deep-merges the user config over fresh defaults. User values always win, new default keys are added, lists are merged and de-duplicated. Unknown or retired user keys are kept as-is (not flagged); only the legacy `version` key is removed.

3. **State Preserver**: The merge path never rewrites state.yaml; it writes `default_state()` only when state.yaml is missing. Phase history and timestamps survive.

4. **Schema Updater**: `create_internal_dirs(root, template_dir, overwrite_schemas=False)` copies each shipped `templates/schemas/*.yaml` into `.specflow/schema/` only when the destination file is absent, so pack-installed, user-added and locally edited schemas are preserved. Only `overwrite_schemas=True` (the `--force` path) replaces existing schema files.

5. **Force Mode**: With `--force` on an initialised project, `init` first copies config.yaml, state.yaml, findings-baseline.yaml, source-fingerprints.yaml, `schema/` and `checklists/` to `.specflow/cache/backups/<timestamp>/` (`backup_run_dir` + `backup_specflow_internals`) and aborts if the backup fails. It then performs a clean re-init that resets config, state and schemas (clearing `active_packs`) while keeping an existing findings baseline.

## Interfaces

- `init.run(root, args) -> int` — detects re-init vs. fresh init (`.specflow/config.yaml` exists) and delegates to the merge or create path; `--force` turns a re-init into backup + create
- `config.merge_config(existing: dict, defaults: dict) -> dict` — merges user values over defaults and stamps `format_version`
- `config.stamp_format_version(root, *, dry_run=False) -> bool`, `config.strip_legacy_version(root, *, dry_run=False) -> str | None`, `config.format_version_mismatch(root) -> str | None`, `config.warn_format_version_once(root)` — format-version helpers
- `scaffold.create_internal_dirs(root, template_dir, *, overwrite_schemas=False)` — internal dirs plus copy-if-absent schema copy
- `config.backup_specflow_internals(root, backup_dir) -> list[str]` and `scaffold.backup_run_dir(root, stamp=None) -> Path` — the `--force` backup

## Dependencies

- `FORMAT_VERSION` / `SUPPORTED_FORMAT_VERSION` in lib/config.py for compatibility; `specflow.__version__` only labels the merge message
- Existing `config.py` read/write infrastructure (`read_config`, `write_config`, `read_state`, `write_state`)
- Existing `scaffold.py` directory creation (`create_internal_dirs`, `create_spec_dirs`, `copy_checklists`, `copy_adapters_config`)

## Data Flow

1. `init.run()` checks whether `.specflow/config.yaml` exists
2. If it exists (no `--force`): create missing dirs, copy only absent schemas, merge config over defaults (stamping `format_version`), print added fields, refresh checklists and adapters config, write state.yaml only if missing
3. If it does not exist: fresh init (internal dirs, spec dirs, default config and state, empty findings baseline)
4. If `--force` on an initialised project: back up internals to `.specflow/cache/backups/<timestamp>/`, then fresh init with `overwrite_schemas=True`, keeping an existing findings baseline
