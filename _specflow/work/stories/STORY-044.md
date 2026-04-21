---
id: STORY-044
title: 'Fix ReqIF round-trip quality: stable UUIDs, schema fix, tests, ARCH/DDD export'
type: story
status: implemented
priority: medium
tags:
- reqif
- interop
- quality
suspect: false
links:
- target: REQ-011
  role: implements
- target: ARCH-001
  role: guided_by
created: '2026-04-21'
modified: '2026-04-21'
fingerprint: sha256:1951bbd87bce
---

# Fix ReqIF round-trip quality: stable UUIDs, schema fix, tests, ARCH/DDD export

Improve ReqIF import/export with stable UUIDs, schema fix, test suite, and extended export coverage for ARCH and DDD artifact types.

## Description

The current ReqIF export generates random UUIDs on each run, lacks test coverage, and only exports REQs. This story makes UUIDs deterministic, adds tests, and extends export to ARCH/DDD types.

## Acceptance Criteria

1. Given the same artifact exported twice via ReqIF, when the UUIDs are compared, then they are identical (deterministic based on artifact ID + content hash)
2. Given a REQ with reqif_metadata in frontmatter, when `specflow artifact-lint` is run, then no schema warning is emitted for reqif_metadata
3. Given a valid ReqIF archive, when imported via `specflow import --adapter reqif`, then correct REQ artifacts are created in _specflow/
4. Given ARCH and DDD artifacts, when `specflow export --adapter reqif` is run, then they appear in the exported ReqIF archive
5. Given the full test suite including new ReqIF tests, when `uv run pytest` is run, then all tests pass

## Out of Scope

- Bidirectional sync with ALM tools (deferred indefinitely)
- Import of ARCH/DDD from ReqIF (export only for now)

## Dependencies

- STORY-040 (reqif_metadata schema fix — may already be done by that story)
