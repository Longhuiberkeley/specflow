---
id: STORY-054
title: Add --force flag to specflow init for clean re-initialization
type: story
status: implemented
priority: medium
tags:
- init
- upgrade
- cli
suspect: false
links:
- target: REQ-022
  role: implements
- target: ARCH-016
  role: guided_by
- target: DDD-017
  role: specified_by
created: '2026-05-04'
modified: '2026-05-04'
fingerprint: sha256:9a614e46dc55
---

# Add --force flag to specflow init for clean re-initialization

Add a `--force` flag to `specflow init` that performs a destructive clean re-init with backup of previous files.

## Acceptance Criteria

1. Given an initialized project, when `specflow init --force` is executed, then existing config.yaml, state.yaml, and schema files are backed up to `.specflow/cache/backups/<timestamp>/` before being replaced.
2. Given an initialized project, when `specflow init --force` completes, then the project is in the same state as a fresh init (all defaults, clean state).
3. Given `specflow init` without `--force` on an existing project, when the command runs, then the merge path is taken (no destructive operations).
4. Given a backup directory, when the backup is created, then it contains the previous config.yaml, state.yaml, and the full schema directory.
5. Given a backup failure (disk full, permissions), when `--force` is attempted, then the init is aborted with an error message and no files are deleted.
