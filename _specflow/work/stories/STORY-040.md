---
id: STORY-040
title: Remove deprecated CLI aliases and fix requirement schema
type: story
status: implemented
priority: high
tags:
- cleanup
- deprecation
- schema
suspect: false
links:
- target: REQ-014
  role: implements
- target: ARCH-001
  role: guided_by
- target: IT-001
  role: verified_by
created: '2026-04-21'
modified: '2026-04-21'
fingerprint: sha256:d87a2091f072
---

# Remove deprecated CLI aliases and fix requirement schema

Remove the 8 deprecated CLI alias subcommands from cli.py and add reqif_metadata to the requirement schema optional_fields.

## Description

The CLI has 8 hidden aliases (validate, check, impact, tweak, sequence, verify, audit, compliance) that were deprecated in favor of their modern equivalents. These aliases create maintenance burden and confusion. This story removes them and also fixes the requirement schema to include reqif_metadata as an optional field.

## Acceptance Criteria

1. Given the codebase with 8 deprecated aliases, when `specflow validate` is run, then the command is not recognized and exits with an error
2. Given the codebase after cleanup, when `specflow artifact-lint` is run, then `reqif_metadata` on REQ frontmatter does not trigger a schema warning
3. Given the codebase after cleanup, when `specflow --help` is run, then only the canonical command names appear (no deprecated aliases)
4. Given the full test suite, when `uv run pytest` is run, then all existing tests pass

## Out of Scope

- Adding new CLI commands or features
- Changes to the behavior of canonical commands
- ARCH/DDD export in ReqIF (that is REQ-011)

## Dependencies

- None — this is a pure cleanup story
