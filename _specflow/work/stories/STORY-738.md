---
id: STORY-738
title: 'Fix DEF-020: specflow go assembles context only, never stages or commits'
type: story
status: verified
tags:
- core
- cli
- robustness
suspect: false
links:
- target: REQ-067
  role: implements
- target: DEF-020
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:b0ca2cae46c0
modified: '2026-10-18'
output_files:
- src/specflow/lib/executor.py
- src/specflow/commands/go.py
- src/specflow/cli.py
- docs/cli-reference.md
- tests/test_go_executor.py
- tests/test_cli_hints.py
- src/specflow/lib/orphans.py
- src/specflow/lib/orphans.py
- docs/architecture.md
thinking_techniques:
- worst_case_user
- composition
version: 1
---

# Fix DEF-020: specflow go assembles context only, never stages or commits

## Summary

Fix DEF-020. `specflow go` becomes context assembly only: delete `auto_commit_wave` and its call in `run_execution` (src/specflow/lib/executor.py), make `go.py` print "Context assembled" for the stories whose context was built instead of "Completed", drop the dead `--timeout` flag from the `go` subparser (src/specflow/cli.py) and from docs/cli-reference.md, and update the subparser help text so it no longer claims to run stories or update their status. Replace `tests/test_go_executor.py::TestAutoCommitWave` with a test that runs `go` (non-dry-run) in a throwaway git repo with uncommitted files and asserts `git status --porcelain` and `git rev-parse HEAD` are unchanged. Move DEF-020 open → fixing → verified → closed as the fix lands.

## Acceptance Criteria

1. Given a git repo with an approved STORY and uncommitted files, when `specflow go` runs, then no commit is created, nothing is staged, every `git status --porcelain` line outside `.specflow/` is unchanged (the only permitted difference is the engine's own `.specflow/state.yaml` execution-state write), and the exit code is 0.
2. Given the same run, when the summary prints, then it says "Context assembled" for the story ids and never "Completed".
3. Given `specflow go --help`, when printed, then `--timeout` is absent and the help text does not claim to update story status; docs/cli-reference.md matches.
4. Given the test suite, when it runs, then no test references `auto_commit_wave` and the new no-commit test is green.
