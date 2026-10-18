---
id: ARCH-018
title: File Traceability Layer
type: architecture
status: implemented
suspect: false
links:
- target: REQ-024
  role: derives_from
created: '2026-05-04'
modified: '2026-10-08'
fingerprint: sha256:e53635e33c61
thinking_techniques:
- assumption_surfacing
version: 2
---

# File Traceability Layer

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-033); earlier text described glob entries being skipped by the existence check and `validate_output_files` / `parse_output_files` helpers that do not exist.

Adds an `output_files` field to architecture, detailed design, and story artifact schemas, enabling bidirectional traceability between specification artifacts and the files they produce or govern. Includes filesystem existence verification with glob expansion: literal paths must exist, and a glob must match at least one file.

## Package Structure

```
src/specflow/templates/schemas/         — architecture.yaml, detailed-design.yaml, story.yaml list output_files in optional_fields
src/specflow/lib/lint.py                — known_meta set in validate_artifact_schema() includes output_files
src/specflow/lib/files.py               — expand_output_files(), literal_missing(), glob_entries(), GLOB_CHARS
src/specflow/commands/artifact_lint.py  — _check_output_files() (check `output-files`)
src/specflow/commands/update.py         — --output-files flag (replace semantics; '' clears)
src/specflow/lib/artifacts.py           — Artifact.output_files property; _render_artifact_file() / update_artifact() write the field
```

## Component Responsibilities

1. **Schema Extension**: `output_files` sits in the `optional_fields` list of the ARCH, DDD, and STORY schemas and in lint's `known_meta` set. The field holds a list of path strings or glob patterns, resolved relative to the project root; `Artifact.output_files` normalizes a scalar or list value to `list[str]`.

2. **File Existence Verifier**: `_check_output_files(artifacts, root)` reads `output_files` from frontmatter. Literal entries that do not exist are reported by `files.literal_missing` as warning `output-files/missing`. Entries containing glob characters (`*`, `?`, `[`) are picked out by `files.glob_entries` and expanded by `files.expand_output_files` (`Path.glob`, so `**` works, filtered through the source-file exclude rules); a glob that matches nothing emits warning `output-files/glob-empty`.

3. **CLI Update Flag**: `specflow update <ID> --output-files "a,b"` accepts a comma-separated list, strips blanks, and replaces the existing list; an empty string removes the field. `--set output_files=null` also removes it.

4. **Frontmatter Renderer**: `_render_artifact_file()` writes `output_files` on create when it is passed, and `update_artifact()` writes, replaces, or pops it on update, so the field appears in YAML frontmatter only when present.

## Interfaces

- `files.literal_missing(root, entries) -> list[str]` — literal entries missing on disk
- `files.glob_entries(entries) -> list[str]` — the glob entries of an output_files list
- `files.expand_output_files(root, entries) -> set[Path]` — existing files a list expands to (literals honoured, globs filtered)
- `artifact_lint._check_output_files(artifacts, root) -> dict` — the `output-files` check (warnings only)
- Parsing of `--output-files` is inline in `commands/update.py` (comma split, `''` → remove)
- Schema field: `output_files: list[str]` — optional on ARCH, DDD, STORY

## Dependencies

- Existing schema validation in `lib/lint.py` (`validate_artifact_schema`, `known_meta`)
- Existing artifact frontmatter rendering and update in `lib/artifacts.py`
- `pathlib.Path` for filesystem checks and `Path.glob()` for glob expansion
- `files.GLOB_CHARS` (`*?[`) for glob detection

## Data Flow

1. User adds `output_files` via `specflow update <ID> --output-files "path1,path2"` (replacing any existing list)
2. `update_artifact()` writes the list to the artifact's YAML header
3. `artifact-lint` reads `output_files`, resolving paths relative to root
4. For literal paths: `literal_missing` checks `(root / path).exists()` and each miss warns `output-files/missing`
5. For glob patterns (detected with `GLOB_CHARS`): `expand_output_files` expands the pattern, and zero matches warns `output-files/glob-empty`
6. Report warnings for missing literal paths and empty globs
