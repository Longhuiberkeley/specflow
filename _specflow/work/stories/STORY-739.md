---
id: STORY-739
title: brief reports the uncommitted working tree and --next carries an advisory
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
created: '2026-10-18'
fingerprint: sha256:fefd1bf410b8
modified: '2026-10-18'
output_files:
- src/specflow/commands/brief.py
- tests/test_brief_working_tree.py
- docs/cli-reference.md
thinking_techniques:
- worst_case_user
- composition
---

# brief reports the uncommitted working tree and --next carries an advisory

## Summary

`specflow brief` reads only `git log` today. Add a `_working_tree(root)` helper in src/specflow/commands/brief.py (same subprocess pattern as `_last_ledger_commit`; `git status --porcelain --untracked-files=all`, timeout 15, degrade to nothing outside git), bucket paths into `_specflow/` (ledger), `.specflow/` (engine state, informational only) and everything else (source), print a "Working tree" line in the rendered brief with counts per bucket and up to three example paths, and append one advisory line to the `--next` recommendation when the ledger or source bucket is non-empty ("N uncommitted _specflow/ path(s) and M source path(s) — commit or review before shipping"). `.specflow/`-only changes produce no line. Exit codes unchanged. Tests in tests/test_brief*.py cover: clean tree (no line), ledger-only, source-only, `.specflow/`-only (no line), and not-a-git-repo (no line, no crash).

## Acceptance Criteria

1. Given modified or untracked `_specflow/` and `src/` paths, when `specflow brief` runs, then a "Working tree" line reports both buckets with counts.
2. Given the same tree, when `specflow brief --next` runs, then the output ends with one advisory line naming the counts and the exit code is 0.
3. Given only `.specflow/` changes, when `brief` and `brief --next` run, then neither prints a working-tree line.
4. Given a directory that is not a git repository, when `brief` runs, then it prints no working-tree line and does not fail.
