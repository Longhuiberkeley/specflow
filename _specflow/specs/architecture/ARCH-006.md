---
id: ARCH-006
title: Pack-Author Pipeline
type: architecture
status: implemented
priority: high
rationale: Architecture for the LLM-assisted standards pack authoring workflow, from
  source ingestion through validation to installation
tags:
- packs
- skills
- standards
- quality
suspect: false
links:
- target: REQ-006
  role: derives_from
- target: REQ-004
  role: derives_from
created: '2026-04-21'
modified: '2026-04-21'
fingerprint: sha256:placeholder
---

# Pack-Author Pipeline

The `/specflow-pack-author` skill is an interactive, LLM-assisted wizard that transforms external standards documents (PDF, URL, or pasted text) into structured YAML compliance packs. It is a **pure AI skill** — the agent performs extraction and file generation directly, then validates the output with a deterministic shell script.

## Pipeline Stages

| Stage | Actor | Mechanism |
|-------|-------|-----------|
| 1. Source Ingestion | AI agent | Read PDF via tool, fetch URL, or accept pasted text |
| 2. TOC Extraction & Scoping | AI agent | Present table of contents as selection menu |
| 3. Section Chunking | AI agent | Extract `{id, title, description}` per section |
| 4. Pack Generation | AI agent | Write `pack.yaml`, `standards/*.yaml`, optional `schemas/` |
| 5. Validation | Shell script | `validate-pack.sh` checks structural integrity |
| 6. Installation | CLI | `specflow init --preset {name}` calls `apply_pack()` |

## Components

### Skill Definition (`specflow-pack-author/`)

```
specflow-pack-author/
├── SKILL.md                    # 6-step workflow instructions
├── scripts/
│   └── validate-pack.sh        # Deterministic pack validation
└── references/
    ├── pack-structure.md       # Pack directory layout
    ├── schema-template.md      # Artifact schema YAML format
    └── example-packs.md        # Example pack structures
```

### Pack Directory Structure

```
{pack-name}/
├── pack.yaml                   # Manifest: name, version, adds_artifact_types, adds_directories
├── standards/
│   └── {pack-name}.yaml        # Clause list: standard, title, version, clauses[{id, title, description}]
├── schemas/                    # Only if pack adds new artifact types
│   └── {type}.yaml
├── checklists/                 # Optional compliance checklists
└── README.md
```

### Pack Installation (`lib/scaffold.py`)

`apply_pack(root, pack_name, packs_dir)`:
1. Load `pack.yaml` manifest
2. Copy `schemas/*.yaml` → `.specflow/schema/` (never overwrite)
3. Create `_specflow/{dir}/` for each `adds_directories` entry
4. Copy `checklists/**/*.yaml` → `.specflow/checklists/` (never overwrite)
5. Copy `standards/*.yaml` → `.specflow/standards/` (never overwrite)
6. Update `config.yaml` with `active_packs` and `artifact_types`

### Gap Analysis (`lib/standards.py`)

`check_compliance(root, standard_name)`:
1. Load standard YAML from `.specflow/standards/`
2. Scan all artifacts for `complies_with` links
3. Cross-reference: clauses with zero linking artifacts are "uncovered"
4. Return covered/uncovered lists with coverage percentage

## Platform Awareness

The skill adapts to AI platform capabilities:
- **Native PDF support** (Claude, Gemini): Read PDF directly
- **No PDF support**: Fall back to URL fetch or pasted text

## Design Principles

1. **LLM does the extraction** — no deterministic parser for arbitrary PDFs
2. **Deterministic validation** — `validate-pack.sh` checks structure, not content
3. **Never overwrite** — pack installation is additive only
4. **Clause fidelity** — extraction protocol minimizes hallucination via TOC-first scoping and spot-check verification
