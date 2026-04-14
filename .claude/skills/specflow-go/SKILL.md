---
name: specflow-go
description: Use when the user wants to execute approved stories in parallel waves. Run `/cmd` to invoke.
---

# SpecFlow Go

Execute approved stories in parallel waves.

## Usage

- `/cmd --dry-run` — Show the wave plan without executing.
- `/cmd` — Execute all approved stories in waves with per-artifact locking.
- `/cmd --wave 1` — Execute only wave 1.

Acquires locks per artifact for parallel safety. Generates unit/integration/qualification test stubs. Updates story status to `implemented` on completion.
