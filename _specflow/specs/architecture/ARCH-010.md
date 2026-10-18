---
id: ARCH-010
title: Command Wrappers & Adapter Framework
type: architecture
status: implemented
suspect: false
links:
- target: REQ-018
  role: derives_from
- target: IT-012
  role: verified_by
created: '2026-04-22'
fingerprint: sha256:0000cebd720c
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 3
modified: '2026-10-08'
---

# Command Wrappers & Adapter Framework

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-031); earlier text described Click command groups, global `--repo-root`/`--format` options and an adapter contract of `detect()`/`run()`.

## Component

The CLI entry point (`src/specflow/cli.py`) builds one argparse parser in `build_parser()`: a `_HintParser` (an `argparse.ArgumentParser` subclass that adds did-you-mean hints for mistyped subcommands and flags) with one subparser per command, each registered by an `_add_<name>_parser()` helper. `main()` dispatches `args.command` through a dict to a `cmd_<name>(args)` handler. Each handler lazily imports its module under `src/specflow/commands/`, resolves the project root and calls `run(root, vars(args))`; the command module then calls the library functions in `src/specflow/lib/`. This separation keeps the CLI surface declarative while library modules remain independently testable.

## Interface

- **Command surface**: `specflow <subcommand>`. The only top-level option is `--version`. The project root is the nearest directory (the current one or an ancestor) that holds `.specflow/` (`_find_project_root()`, with no flag or env override); `init` always uses the current directory. Output formats are per-command flags (for example `rtm --format table|markdown|csv`, `list --json`).
- **Adapter base class** (`lib/adapters/base.py`): `Adapter` declares `name`, a `supported_operations` set, and five stub methods that raise `NotImplementedError` unless a subclass overrides them: `generate_ci_workflow(ops)`, `import_artifacts(source)`, `export_artifacts(dest)`, `ingest_standard(source)` and `get_hook_script()`. Callers check `supported_operations` before calling a method.
- **Concrete adapters**: `GitHubActionsAdapter` (`github-actions`, `lib/adapters/github_actions.py`) generates workflow YAML and the hook script; `ReqIFAdapter` (`reqif`, `lib/adapters/reqif.py`) handles ReqIF import/export by delegating to `lib/reqif.py` (`import_reqif`, `export_reqif`).

## Responsibility

- Handlers pass the parsed namespace to the command module as a dict; command modules validate input and call lib functions.
- Adapters isolate third-party integrations (GitHub Actions, ReqIF) behind a common interface so core logic has no direct dependency on external formats.
- Concrete adapters self-register with `@register_adapter` when `lib/adapters/__init__.py` imports their modules. Commands resolve them by name with `get_adapter()`: `import`/`export` take `--adapter`, while `ci generate` and `hook` read the provider from `.specflow/adapters.yaml`. A new adapter needs its module plus one import line in `__init__.py`, not a CLI change.

## Dependencies

- Python standard-library `argparse` for CLI argument parsing and help generation.
- PyYAML (the only runtime dependency in `pyproject.toml`) for reading artifact frontmatter and config.
- `lib/files.py` for source-file scanning and `output_files` expansion; `lib/scaffold.py` for directory scaffolding.
