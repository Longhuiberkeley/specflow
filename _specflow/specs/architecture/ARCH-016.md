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
fingerprint: sha256:b70d3b3a81f6
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 1
---

# Init Upgrade Engine

Provides safe re-initialization of SpecFlow projects by preserving existing user state while applying framework updates. Manages version detection, configuration merging, and selective schema migration.

## Package Structure

```
src/specflow/commands/init.py     — Upgrade detection, config merge, --force flag
src/specflow/lib/config.py        — merge_config(), version stamp read/write
src/specflow/lib/scaffold.py      — Incremental schema copy (merge, not replace)
```

## Component Responsibilities

1. **Version Detector**: Reads `version` from existing config.yaml. Compares against current framework version. Reports delta (new fields, changed defaults, deprecated fields).

2. **Config Merger**: Reads existing user config, merges with new defaults. User values always win. New fields added with defaults. Deprecated fields preserved but flagged.

3. **State Preserver**: Skips state.yaml overwrite on re-init. Preserves phase history and timestamps.

4. **Schema Updater**: Replaces destructive `shutil.rmtree + copytree` with per-file copy that skips existing files. Preserves pack-installed and user-added schemas.

5. **Force Mode**: When `--force` flag is provided, backs up existing config/state/schemas to `.specflow/cache/backups/<timestamp>/` before performing a clean re-init.

## Interfaces

- `init.run()` — detects upgrade vs. fresh init, delegates to merge or create path
- `config.merge_config(existing, defaults) -> dict` — merges user values over defaults
- `config.read_version(root) -> str | None` — reads version stamp

> Amended 2026-10-18 (SPIKE-008 R1-032): `read_version` and `scaffold.merge_schemas` do not exist. The stamp is now a format version (`_read_format_version`, `stamp_format_version`, `format_version_mismatch` in lib/config.py), schemas are copied by `create_internal_dirs(root, template_dir, overwrite_schemas=...)`, and re-init reports added config fields rather than a version delta.

- `scaffold.merge_schemas(src, dst)` — incremental file copy

## Dependencies

- `specflow.__version__` for version comparison
- Existing `config.py` read/write infrastructure
- Existing `scaffold.py` directory creation

## Data Flow

1. `init.run()` checks if `.specflow/config.yaml` exists
2. If exists: read version, compare, merge config, update schema incrementally
3. If not exists: fresh init (current behavior)
4. If `--force`: backup, then fresh init
