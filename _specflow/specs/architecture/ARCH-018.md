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
modified: '2026-05-04'
fingerprint: sha256:34da9eef4d92
---

# File Traceability Layer

Adds an `output_files` field to architecture, detailed design, and story artifact schemas, enabling bidirectional traceability between specification artifacts and the files they produce or govern. Includes filesystem existence verification with glob pattern support.

## Package Structure

```
src/specflow/templates/schemas/         — Updated schemas: architecture.yaml, detailed-design.yaml, story.yaml
src/specflow/lib/lint.py                — Updated known_meta set, new file existence validator
src/specflow/commands/artifact_lint.py  — New check: output-files
src/specflow/commands/update.py         — New --output-files flag
src/specflow/lib/artifacts.py           — Updated render to include output_files in frontmatter
```

## Component Responsibilities

1. **Schema Extension**: Adds `output_files` to the `optional_fields` list in ARCH, DDD, and STORY schemas. The field holds a list of path strings, resolved relative to the project root.

2. **File Existence Verifier**: New lint check that reads `output_files` from artifact frontmatter. For each entry: if it contains glob characters (`*`, `?`, `[`), skip the check; otherwise, verify the file exists relative to the project root.

3. **CLI Update Flag**: Extends `specflow update <ID>` with `--output-files` flag accepting a comma-separated list of paths. Parses and writes to the artifact's frontmatter.

4. **Frontmatter Renderer**: Updates `_render_artifact_file()` to include `output_files` in YAML frontmatter when the field is present and non-empty.

## Interfaces

- `lint.validate_output_files(root, artifact) -> list[str]` — returns list of warnings for missing files
- `update.parse_output_files(value: str) -> list[str]` — parses comma-separated paths
- Schema field: `output_files: list[str]` — optional on ARCH, DDD, STORY

## Dependencies

- Existing schema validation in `lint.py`
- Existing artifact frontmatter rendering in `artifacts.py`
- `pathlib.Path` for filesystem checks
- `glob.glob()` for glob pattern detection

## Data Flow

1. User adds `output_files` via `specflow update <ID> --output-files "path1,path2"`
2. Frontmatter renderer writes the list to the artifact's YAML header
3. `artifact-lint` reads `output_files`, resolves paths relative to root
4. For literal paths: check `Path(root, path).exists()`
5. For glob patterns: detect with `any(c in path for c in '*?[')`, skip check
6. Report warnings for any missing literal paths
