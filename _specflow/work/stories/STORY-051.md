---
id: STORY-051
title: Add output_files field to artifact schemas and lint
type: story
status: implemented
priority: medium
tags:
- traceability
- schema
- spidr-data
suspect: false
links:
- target: REQ-024
  role: implements
- target: ARCH-018
  role: guided_by
- target: DDD-018
  role: specified_by
created: '2026-05-04'
modified: '2026-06-15'
fingerprint: sha256:d11543fd4127
output_files:
- tests/test_create_set_fields.py
---

# Add output_files field to artifact schemas and lint

Add `output_files` optional field to ARCH, DDD, and STORY schemas. Add file existence verification to artifact-lint with glob pattern support.

## Acceptance Criteria

1. Given the architecture, detailed-design, and story schema files, when inspected, then each contains `output_files` in the `optional_fields` list.
2. Given an artifact with `output_files: ["src/specflow/cli.py"]`, when `artifact-lint` runs the `output-files` check, then the file existence is verified relative to the project root.
3. Given an artifact with `output_files: ["nonexistent/file.py"]`, when `artifact-lint` runs, then a warning reports the missing file.
4. Given an artifact with `output_files: ["output/YY_MM_DD_*.json"]`, when `artifact-lint` runs, then no warning is produced (glob patterns are skipped).
5. Given an artifact with no `output_files` field, when `artifact-lint` runs, then no output-files warnings are produced.
6. Given `lint.py` validates artifact frontmatter, then `output_files` is included in the `known_meta` set (no unknown-field warnings).
