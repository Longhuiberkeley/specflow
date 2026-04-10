---
id: ARCH-001
title: CLI Core
type: architecture
status: draft
priority: high
rationale: "The CLI core is the programmatic entry point that dispatches commands and coordinates all SpecFlow operations"
tags: [cli, python, core]
suspect: false
fingerprint: "sha256:78e3e6665c22b155fcf297e6be21f84e51c9b037b9f49684757a4657aa0756e6"
links:
  - target: REQ-001
    role: derives_from
created: 2026-04-10
---

# CLI Core

The `specflow` CLI is implemented as a Python package with argparse-based command dispatch.

## Package Structure

```
src/specflow/
├── __init__.py
├── cli.py                  # Entry point: argparse, subcommand dispatch
├── commands/               # Individual command implementations
│   ├── __init__.py
│   ├── init.py             # specflow init
│   ├── status.py           # specflow status
│   └── validate.py         # specflow validate
├── lib/                    # Shared library modules
│   ├── __init__.py
│   ├── platform.py         # Platform detection logic
│   ├── scaffold.py         # Directory and file creation
│   ├── config.py           # Config and state management
│   ├── fingerprint.py      # SHA256 fingerprint computation
│   └── schema_validator.py # YAML frontmatter validation
└── templates/              # Template files copied during init
    ├── config.yaml         # Default config template
    ├── state.yaml          # Initial state template
    ├── agents-section.md   # SpecFlow section for AGENTS.md
    ├── skills/             # Platform-specific skill facades
    │   ├── claude/
    │   ├── gemini/
    │   └── opencode/
    └── schemas/            # Artifact type schemas
```

## Entry Point (`cli.py`)

The main entry point uses `argparse` with subparsers:
- `specflow init` → `commands/init.py`
- `specflow status` → `commands/status.py`
- `specflow validate` → `commands/validate.py`
- Additional subcommands registered as modules are added

The `main()` function:
1. Parses arguments
2. Dispatches to the appropriate command module
3. Returns exit code (0 for success, 1 for failure)

## Command: `specflow init`

Implementation in `commands/init.py`:
1. Call `lib/platform.py` to detect the AI platform
2. Call `lib/scaffold.py` to create `.specflow/` and `_specflow/` directory trees
3. Call `lib/config.py` to write `config.yaml` and `state.yaml`
4. Copy schema files from `templates/schemas/` to `.specflow/schema/`
5. Create `_index.yaml` stubs in all artifact directories
6. Append SpecFlow section to the project's instruction file (AGENTS.md or chosen)
7. Copy platform-specific skill files from `templates/skills/<platform>/` to the platform's skills directory

## Command: `specflow status`

Implementation in `commands/status.py`:
1. Read `.specflow/state.yaml` for current phase
2. Walk `_specflow/` directory tree counting artifacts by type
3. Read `_index.yaml` files for artifact metadata
4. Scan for suspect flags across all artifacts
5. Check link integrity (broken links, orphans)
6. Format and print dashboard

## Command: `specflow validate`

Implementation in `commands/validate.py`:
1. Load schema definitions from `.specflow/schema/`
2. Walk `_specflow/` directory tree, loading each artifact's frontmatter
3. Run `lib/schema_validator.py` on each artifact
4. Run `lib/fingerprint.py` to check fingerprint freshness
5. Aggregate results by category (schema, links, status, IDs, fingerprints)
6. Format and print results with pass/fail/warning indicators
7. Return exit code 0 if all checks pass, 1 if any blocking check fails

## Shared Library (`lib/`)

### `platform.py`
- Scans the project root for `.claude/`, `.opencode/`, `.gemini/` directories
- Returns detected platform name or `None`
- Platform name determines which skill template set is used

### `scaffold.py`
- Creates `.specflow/` with subdirectories: `schema/`, `impact-log/`, `checklist-log/`, `baselines/`, `locks/`, `standards/`
- Creates `_specflow/` with subdirectories: `specs/` (6 V-model dirs), `work/` (4 work dirs)
- Creates `_index.yaml` stub in each artifact directory
- All directories created via `mkdir -p` equivalent (exist_ok=True)

### `config.py`
- Reads/writes `config.yaml` and `state.yaml` in `.specflow/`
- Generates default config with project name, creation date, impact analysis settings
- Generates initial state with `current: idle` and empty history
- Supports reading artifact counts and suspect flag tallies

### `fingerprint.py`
- Extracts Markdown body after YAML frontmatter delimiter (`---`)
- Computes SHA256 hash of the body content
- Returns `sha256:<hash>` formatted string
- Supports comparing stored vs. computed fingerprints

### `schema_validator.py`
- Loads a schema YAML file for the artifact type
- Checks required fields present in frontmatter
- Checks field values against allowed enums (status, link roles)
- Checks ID format matches schema regex
- Returns structured result: blocking errors, warnings, info messages
