---
id: STORY-713
title: 'Wave P-8: CLI root walk-up, hint parser, read-only help labels, scoped lint
  hint, verbose flag'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-059
  role: implements
created: '2026-10-08'
fingerprint: sha256:a222cd9cf725
modified: '2026-10-08'
output_files:
- src/specflow/cli.py
- src/specflow/commands/update.py
- src/specflow/lib/artifacts.py
- src/specflow/templates/agent-context.md
- tests/test_cli_hints.py
- tests/test_cli_root.py
- tests/test_update_thinking_techniques.py
---

# Wave P-8: CLI root walk-up, hint parser, read-only help labels, scoped lint hint, verbose flag

# Wave P-8

Findings F-027, F-024, F-026 step 1, F-054, F-069 (cmd_standards), F-129 (ci flags), F-005 (--verbose), F-074 text, F-085 SUPPRESS.
## Acceptance Criteria

- [ ] AC1: Given cwd is _specflow/work inside a project, when specflow trace REQ-001 runs, then it resolves the project root and succeeds.
- [ ] AC2: Given a collapsed shell token like "--add-link X:role", when update runs, then the hint says to quote each flag and value separately.
- [ ] AC3: Given specflow artifact-lint --help, when read, then it carries a (read-only) marker and artifact-lint <ID> prints a one-line scope hint.
- [ ] AC4: Given ci generate on an existing differing workflow, when run, then it skips with a --force/--dry-run hint.
