---
id: STORY-686
title: 'CLI defects: import parsing, dead hook suspect check, CI gate refs on pull
  requests'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- cli
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:185210cc7318
modified: '2026-09-30'
output_files:
- src/specflow/cli.py
- src/specflow/commands/import_cmd.py
- src/specflow/commands/export_cmd.py
- src/specflow/commands/hook.py
- src/specflow/lib/adapters/github_actions.py
- .github/workflows/specflow.yml
- tests/test_cli_import_export_parse.py
- tests/test_ci_generation.py
- tests/test_hook.py
---

# CLI defects: import parsing, dead hook suspect check, CI gate refs on pull requests

## Acceptance Criteria
1. specflow import --adapter reqif <file> and specflow export --adapter <name> parse; the empty subparsers are gone and a parse test pins it.
2. The pre-commit suspect warning reads the staged artifact's suspect field in-process and no longer spawns a per-artifact subprocess.
3. The generated CI gate diffs origin/<base_ref> against the pull-request head sha; this repository's workflow uses the same form; the CI generation test asserts it.
4. Each fix has a failing-then-passing test.
