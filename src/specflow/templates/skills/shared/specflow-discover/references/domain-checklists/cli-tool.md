# CLI Tool Domain Checklist

Questions for command-line interface tools.

## Interface

1. **Primary interface style?** "Argument-based (like `cp src dst`), subcommand-based (like `git commit`), or interactive prompts? For your use case, subcommands scale best for multi-feature tools."
2. **Output format?** "Human-readable terminal output (default), with optional JSON/YAML for scripting (`--format json`)? Machine-only output (daemons)?"
3. **Interactive mode needed?** "Should the tool run fully non-interactive for CI/CD, or does it need an interactive TUI for exploration?"
4. **Color/presentation?** "Colored output for humans, plain for pipes? Respects `NO_COLOR` environment variable?"

## Distribution

5. **Installation method?** "Package manager (brew, apt, pip, npm), single binary download, or container image? For internal tools, a private registry may be needed."
6. **Target platforms?** "Linux only, macOS + Linux, or cross-platform including Windows? Shell differences affect scripting."
7. **Dependencies?** "Zero-dependency single binary, or acceptable to require a runtime (Python, Node)? Bundled or system-managed?"

## Input & Configuration

8. **Configuration sources?** "Command-line flags, environment variables, config file (`~/.config/tool/config.yaml`), or all three with priority order?"
9. **Input data sources?** "Files on disk, stdin pipes, network URLs, database queries? Any large-file streaming needs?"
10. **Exit codes?** "Standard exit codes (0=success, 1=error) sufficient, or do you need granular exit codes for different failure modes?"

## Operational

11. **Logging?** "Silent on success, verbose flag for debugging, or always log? Log destination: stderr, file, syslog?"
12. **Error handling style?** "Fail fast on first error, or collect all errors and report? Retry logic for transient failures?"
13. **Performance expectations?** "Expected data volumes and acceptable runtime? Sub-second, seconds, or minutes?"
14. **Extensibility?** "Plugin system needed? Configurable pipelines, hooks, or user-defined commands?"
