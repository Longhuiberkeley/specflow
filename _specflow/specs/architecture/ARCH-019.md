---
id: ARCH-019
title: Reverse Impact Engine
type: architecture
status: implemented
suspect: false
links:
- target: REQ-025
  role: derives_from
- target: ARCH-018
  role: derives_from
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:c8d3e4d5924b
---

# Reverse Impact Engine

Extends the impact analysis system to map source code and data product changes back to spec artifacts via the `output_files` field. Closes the bidirectional traceability loop: spec → code (via output_files) and code → spec (via reverse impact).

## Package Structure

```
src/specflow/lib/impact.py            — reverse_impact() function, glob matching
src/specflow/commands/change_impact.py — extended report with source file section
src/specflow/commands/document_changes.py — expanded to read source file changes
```

## Component Responsibilities

1. **Source Change Detector**: Reads `git diff` output to identify modified files outside `_specflow/`. Extracts added, modified, and deleted file paths.

2. **Output File Index**: Builds an in-memory reverse index mapping file paths → artifact IDs by scanning all artifacts' `output_files` fields. Handles glob patterns by matching against actual file paths.

3. **Suspect Propagator**: For each changed file matching an artifact's `output_files`, sets `suspect: true` on that artifact and propagates through the downstream link graph.

## Interfaces

- `impact.build_output_file_index(root) -> dict[str, list[str]]` — maps file path → artifact IDs
- `impact.reverse_impact(root, changed_files) -> list[(artifact_id, matched_files)]` — returns affected artifacts
- Extended `change-impact` report with "Source File Impact" section

## Dependencies

- `output_files` field on ARCH, DDD, STORY (from ARCH-018 / REQ-024)
- Existing suspect flag propagation in `impact.py`
- `git_utils.py` for git diff parsing

## Data Flow

1. `change-impact` or `document-changes` detects git commit with file changes
2. Source Change Detector filters non-_specflow file paths
3. Output File Index maps each changed file to governing artifacts
4. Suspect Propagator flags matching artifacts and propagates downstream
