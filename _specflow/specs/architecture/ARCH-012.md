---
id: ARCH-012
title: Change-Audit & Pack-Author Pipelines
type: architecture
status: implemented
suspect: false
links:
- target: REQ-020
  role: derives_from
- target: IT-014
  role: verified_by
created: '2026-04-22'
fingerprint: sha256:dd2fd3fceb73
thinking_techniques: [assumption-surfacing, devil's-advocate]
version: 1
modified: '2026-06-15'
---

# Change-Audit & Pack-Audit Pipelines

## Component

Two specialized pipelines extend SpecFlow's compliance capabilities beyond the core lifecycle:

1. **Change-Audit pipeline** (`specflow-change-impact-review` skill + `lib/impact.py`): Analyzes the blast radius of recent DEC artifacts by walking link chains, computing affected downstream artifacts, and generating CHL (challenge) findings for unreviewed impacts.
2. **Pack-Author pipeline** (`specflow-pack-author` skill + `lib/scaffold.py`): Generates complete pack directory structures from a PDF, URL, or pasted standards text, producing `pack.yaml`, schema files, and optional checklist YAML.

## Data Flow

- **Change-Audit**: Recent commits → DEC artifact discovery → link-chain traversal (`lib/artifacts.py:trace_chain`) → impact cone computation → CHL artifact creation.
- **Pack-Author**: Source document → clause extraction → schema YAML generation → `pack.yaml` manifest assembly → directory scaffolding.

## Responsibility

- The change-audit pipeline ensures that every DEC artifact's downstream impact is explicitly reviewed before release.
- The pack-author pipeline enables users to import external compliance standards (ISO 26262, ASPICE, custom) as executable SpecFlow packs without manual YAML authoring.
- Both pipelines produce artifacts (CHL, pack directories) that integrate with the existing status and traceability systems.

## Dependencies

- `lib/impact.py` for blast-radius computation and suspect-flag propagation.
- `lib/scaffold.py` for directory and file generation during pack authoring.
- `lib/artifacts.py` for link traversal and frontmatter parsing.
