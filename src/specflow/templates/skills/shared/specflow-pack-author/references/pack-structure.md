# Pack Structure Reference

A standards pack is a self-contained directory under `src/specflow/packs/{name}/` (bundled) or `.specflow/packs/{name}/` (user-authored).

## Directory Layout

```
{name}/
├── pack.yaml              # Pack manifest
├── standards/
│   └── {name}.yaml        # Standard clauses
├── schemas/               # Only if pack adds new artifact types
│   └── {type}.yaml
└── README.md
```

## pack.yaml — Pack Manifest

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Pack identifier (lowercase, hyphenated) |
| `version` | Yes | string | Semantic version |
| `description` | Yes | string | One-line description of what this pack provides |
| `adds_artifact_types` | No | list | Artifact type IDs introduced by this pack |
| `adds_directories` | No | list | `_specflow/` subdirectories to create on install |

### Example

```yaml
name: iso26262-demo
version: "0.1-demo"
description: "ISO 26262 demo pack — minimal stubs to prove pack architecture. NOT a real compliance pack."
adds_artifact_types:
  - hazard
adds_directories:
  - specs/hazards
```

## standards/{name}.yaml — Standard Clauses

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `standard` | Yes | string | Standard identifier (matches pack name) |
| `title` | Yes | string | Full title of the standard |
| `version` | Yes | string | Version of the standard |
| `clauses` | Yes | list | List of clause objects |

### Clause Object

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | Yes | string | Clause identifier from the source standard |
| `title` | Yes | string | Clause title |
| `description` | Yes | string | Clause description or requirement text |

### Example

```yaml
standard: iso26262-demo
title: "Road vehicles — Functional safety (demo stub)"
version: "0.1-demo"
clauses:
  - id: "ISO26262-3.7"
    title: "Hazard analysis and risk assessment"
    description: "Identify and classify hazards that could be caused by malfunctioning system behaviour."
  - id: "ISO26262-4.6"
    title: "Safety goals"
    description: "Derive top-level safety requirements from identified hazards."
```

## schemas/{type}.yaml — Artifact Schema

See `references/schema-template.md` for the full schema format.

## README.md

A human-readable description of the pack. Should include:
- What standard the pack covers
- Whether it's a real compliance pack or a demo/stub
- How many clauses are included
- A pointer to `/specflow-pack-author` for users who want to build their own

## How Packs Are Installed

When a user runs `specflow init --preset {name}`:

1. `apply_pack()` in `lib/scaffold.py` locates the pack under the bundled `packs/` directory
2. Copies `schemas/*.yaml` → `.specflow/schema/` (preserves existing files)
3. Creates `_specflow/` directories declared in `adds_directories`
4. Copies `standards/*.yaml` → `.specflow/standards/` (preserves existing files)
5. Copies any `checklists/` subdirectory → `.specflow/checklists/`
6. Updates `config.yaml` with new artifact types and active packs

For user-authored packs in `.specflow/packs/`, the user must manually copy standards and schemas to the appropriate `.specflow/` locations, or copy the pack to the bundled `src/specflow/packs/` directory for use with `--preset`.
