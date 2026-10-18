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
modified: '2026-10-08'
fingerprint: sha256:0e2f8343d2cb
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 2
---

# Reverse Impact Engine

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-108); earlier text described document-changes reading source files, a `list[str]` index, and automatic suspect flagging (flagging now happens only with `change-impact --flag`; the default report is informational).

Extends the impact analysis system to map source code and data product changes back to spec artifacts via the `output_files` field. Closes the bidirectional traceability loop: spec → code (via output_files) and code → spec (via reverse impact).

## Package Structure

```
src/specflow/lib/impact.py             — build_output_file_index(), query_reverse_impact(), flag_suspects_from_matches(), FileArtifactMatch, _glob_match()
src/specflow/commands/change_impact.py — _detect_source_file_changes(); "Source File Impact" report section; --flag
src/specflow/lib/git_utils.py          — get_current_sha(), get_changed_files(), get_commit_timestamp()
```

`commands/document_changes.py` is not part of this engine: it filters changed paths with `git_utils.is_spec_artifact_path` and builds change-record DECs from spec artifacts only.

## Component Responsibilities

1. **Source Change Detector**: `_detect_source_file_changes(root)` takes the files changed by the HEAD commit (`git diff-tree --name-only` via `git_utils.get_changed_files`) and keeps the paths outside `_specflow/`. It returns `(files, sha, commit_timestamp)`; outside a git repo it returns nothing.

2. **Output File Index**: `build_output_file_index(root)` builds an in-memory reverse index by scanning every artifact's `output_files`. Literal entries are keyed by normalized path, glob entries by the pattern itself; each value is a list of `(artifact_id, match_type, pattern)` tuples. `query_reverse_impact` matches changed files against literal keys directly and against glob patterns with `_glob_match` (`fnmatch`, plus `**` recursive support). It is a pure query.

3. **Suspect Propagator**: With `specflow change-impact --flag`, `flag_suspects_from_matches(root, matches)` sets `suspect: true` on each matched artifact and on all of its transitive downstream artifacts, returning the deduplicated flagged ids. Without `--flag` the Source File Impact section is informational and modifies nothing.

## Interfaces

- `impact.build_output_file_index(root) -> dict[str, list[tuple[str, str, str]]]` — normalized path or glob → `(artifact_id, match_type, pattern)` entries
- `impact.query_reverse_impact(root, changed_files, index=None) -> list[FileArtifactMatch]` — read-only matches (`file_path`, `artifact_id`, `match_type` literal|glob, `pattern`)
- `impact.flag_suspects_from_matches(root, matches) -> list[str]` — flags matches plus transitive downstream
- `impact.reverse_impact(root, changed_files, index=None) -> list[FileArtifactMatch]` — query-then-flag convenience wrapper; no command calls it
- `change-impact` report "Source File Impact" section (first 20 artifacts listed in full, the rest summarised); `--flag` turns it from informational into flagging

## Dependencies

- `output_files` field on ARCH, DDD, STORY (from ARCH-018 / REQ-024)
- Existing downstream traversal in `impact.py` (`_find_all_downstream_recursive`) and frontmatter writer (`_update_frontmatter_field`)
- `git_utils.py` for the HEAD commit's changed files and timestamp

## Data Flow

1. `change-impact` detects the files changed by the HEAD commit
2. Source Change Detector drops `_specflow/` paths
3. Output File Index maps each changed file to governing artifacts (`query_reverse_impact`)
4. The report prints matches per artifact; with `--flag`, Suspect Propagator flags matching artifacts and their downstream
