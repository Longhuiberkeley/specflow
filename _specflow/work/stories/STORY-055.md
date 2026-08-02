---
id: STORY-055
title: Build output file reverse index and flag suspect artifacts
type: story
status: implemented
priority: medium
tags:
- impact
- traceability
suspect: false
links:
- target: REQ-025
  role: implements
- target: ARCH-019
  role: guided_by
- target: DDD-019
  role: specified_by
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:67fc9661feda
output_files:
- src/specflow/commands/reconcile.py
- src/specflow/lib/files.py
- tests/test_source_scope.py
---

# Build output file reverse index and flag suspect artifacts

Implement the reverse impact engine that maps source file changes to spec artifacts via output_files and flags affected artifacts as suspect.

## Acceptance Criteria

1. Given artifacts with output_files listing source paths, when `build_output_file_index()` runs, then a reverse map from file path to artifact IDs is constructed.
2. Given a git commit modifying `src/specflow/lib/impact.py`, when an artifact lists that file in output_files, then the artifact is flagged as suspect.
3. Given a glob pattern `output/YY_MM_DD_*.json` in output_files, when a file matching the pattern is modified, then the governing artifact is flagged as suspect.
4. Given a commit modifying files not in any artifact's output_files, when reverse impact runs, then no artifacts are flagged.
5. Given `specflow change-impact` execution, when source file changes exist, then the report includes a "Source File Impact" section listing affected artifacts.
