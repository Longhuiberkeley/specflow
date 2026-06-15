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
fingerprint: sha256:f5769d8f0da2
thinking_techniques: [assumption-surfacing, devil's-advocate]
version: 1
modified: '2026-06-15'
---

# Command Wrappers & Adapter Framework

## Component

The CLI entry point (`cli.py`) registers all commands as Click groups. Each command delegates to a thin wrapper function that parses arguments, resolves filesystem paths, and calls the corresponding library function in `src/specflow/lib/`. This separation keeps the CLI surface declarative while library modules remain independently testable.

## Interface

- **Command surface**: `specflow <subcommand>` with global options `--repo-root` and `--format` (json/text/markdown).
- **Adapter base class** (`lib/adapters/base.py`): defines the contract for CI and export adapters — `name`, `detect()`, and `run()` methods.
- **Concrete adapters**: `GitHubActionsAdapter` (`lib/adapters/github_actions.py`) generates workflow YAML; `ReqIFAdapter` (`lib/adapters/reqif.py`) handles ReqIF import/export.

## Responsibility

- Wrappers validate input and translate CLI flags into keyword arguments for lib functions.
- Adapters isolate third-party integrations (GitHub Actions, ReqIF) behind a common interface so core logic has no direct dependency on external formats.
- The adapter registry auto-discovers implementations via `lib/adapters/__init__.py`, allowing new adapters to be added without modifying the CLI.

## Dependencies

- Click for CLI argument parsing and help generation.
- PyYAML for reading artifact frontmatter.
- `lib/files.py` for path resolution and directory scaffolding.
