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
modified: '2026-05-04'
fingerprint: sha256:829c96b2d7ea
thinking_techniques: [assumption-surfacing, devil's-advocate]
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
