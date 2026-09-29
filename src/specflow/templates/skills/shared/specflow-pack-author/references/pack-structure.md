# Pack Structure Reference

A standards pack is a self-contained directory. SpecFlow ships some packs bundled; user-authored packs live at `.specflow/packs/{name}/` in the project, and `specflow init --preset {name}` resolves them by name.

## Directory Layout

```
{name}/
├── pack.yaml              # Pack manifest
├── standards/
│   └── {name}.yaml        # Standard clauses
├── schemas/               # Only if pack adds new artifact types
│   └── {type}.yaml
├── skills/                # Only if pack adds skills (listed in adds_skills)
│   └── {skill}/SKILL.md
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
| `adds_skills` | No | list | Skill directory names; each needs `skills/<name>/SKILL.md` in the pack and is installed with the project's skills |
| `context_snippet` | No | string | A short block injected into the agent instruction file on install (see below) |

### `context_snippet` and its budget

The snippet is always-on context: it is injected into the instruction file alongside the base SpecFlow block, so every word is read on every turn. The base block and all installed pack snippets share one budget of 375 words. Keep a snippet to a heading plus one or two lines: when the pack's skill should engage and the one command to consult. Never repeat a sentence already in the base block.

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
| `category` | No | string | `safety`, `security`, `functional` (default), or `process`; picks the remediation hint `specflow standards gaps` shows for an uncovered clause |
| `severity` | No | string | `high`, `medium` (default), or `low`; high-severity gaps are prioritized |

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

1. SpecFlow locates the pack by name: `.specflow/packs/{name}/` in the project first, then the packs bundled with SpecFlow
2. Copies `schemas/*.yaml` → `.specflow/schema/` (preserves existing files)
3. Creates `_specflow/` directories declared in `adds_directories`
4. Copies `standards/*.yaml` → `.specflow/standards/` (preserves existing files)
5. Copies any `checklists/` subdirectory → `.specflow/checklists/`
6. Installs each `adds_skills` skill and injects `context_snippet` into the instruction file
7. Updates `config.yaml` with new artifact types and active packs

The same command works on a project that is already initialized: `init` runs in merge mode, keeps the existing config, and adds the pack. Never copy pack files into `.specflow/` by hand — the pack would not be registered in `active_packs`, so its skills, context block, and later syncs would be missing. After editing a pack that is already installed, run `specflow refresh --packs --force` to sync it.
