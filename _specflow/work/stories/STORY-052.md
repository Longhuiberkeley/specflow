---
id: STORY-052
title: Add --output-files flag to specflow update command
type: story
status: implemented
priority: medium
tags:
- cli
- traceability
suspect: false
links:
- target: REQ-024
  role: implements
- target: ARCH-018
  role: guided_by
- target: DDD-018
  role: specified_by
created: '2026-05-04'
modified: '2026-05-04'
fingerprint: sha256:57148d878b2c
---

# Add --output-files flag to specflow update command

Extend `specflow update <ID>` with an `--output-files` flag that sets the `output_files` field on an artifact.

## Acceptance Criteria

1. Given a user running `specflow update ARCH-001 --output-files "src/foo.py,src/bar.py"`, when the command completes, then the artifact's frontmatter contains `output_files: [src/foo.py, src/bar.py]`.
2. Given an artifact with existing `output_files`, when `--output-files` is provided, then the previous value is replaced entirely (not appended).
3. Given `--output-files ""` (empty string), when the command runs, then the `output_files` field is removed from the artifact frontmatter.
4. Given an artifact ID that does not exist, when `--output-files` is provided, then the command reports an error and exits with non-zero status.
