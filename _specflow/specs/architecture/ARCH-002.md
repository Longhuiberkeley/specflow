---
id: ARCH-002
title: Framework Machinery
type: architecture
status: draft
priority: high
rationale: 'The .specflow/ directory contains all framework internals: configuration,
  state, schemas, impact tracking, and baselines'
tags:
- framework
- internals
- core
suspect: false
fingerprint: sha256:e7baed037004
links:
- target: REQ-002
  role: derives_from
- target: REQ-003
  role: derives_from
- target: REQ-005
  role: derives_from
created: 2026-04-10
checklists_applied:
- checklist: check-ARCH-002
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-ARCH-002
  timestamp: '2026-04-14T17:03:22Z'
modified: '2026-04-14'
---

# Framework Machinery

The `.specflow/` directory contains all framework-internal files and state management, separate from user-facing artifacts in `_specflow/`.

## Directory Structure

```
.specflow/
├── config.yaml           # Project configuration
├── state.yaml            # Workflow state and phase history
├── schema/               # Artifact type schema definitions
│   ├── requirement.yaml
│   ├── architecture.yaml
│   ├── detailed-design.yaml
│   ├── unit-test.yaml
│   ├── integration-test.yaml
│   ├── qualification-test.yaml
│   ├── story.yaml
│   ├── spike.yaml
│   ├── decision.yaml
│   └── defect.yaml
├── impact-log/           # Change detection events (artifact-first naming)
├── checklist-log/        # Checklist execution audit log (timestamp-first naming)
├── baselines/            # Immutable project state snapshots
├── locks/                # Filesystem locks for parallel operations
└── standards/            # Imported compliance standards
```

## `config.yaml`

Project-level configuration:

```yaml
project:
  name: "<project name>"
  created: "<YYYY-MM-DD>"

impact_analysis:
  auto_flag: true          # Automatically flag suspects on fingerprint change
  auto_resolve: false      # Never auto-resolve; requires human review
  remind_after: 7d         # Warn about stale unresolved flags

artifact_types:            # Registered artifact types
  - requirement
  - architecture
  - detailed-design
  - unit-test
  - integration-test
  - qualification-test
  - story
  - spike
  - decision
  - defect

active_packs: []           # Industry packs (e.g., [iso26262])
```

## `state.yaml`

Workflow state machine:

```yaml
current: idle              # Current phase: idle | discovering | specifying | planning | executing | verifying | complete
history:                   # Phase transition history
  - phase: discovering
    entered: 2026-03-15
    exited: 2026-03-16
  - phase: specifying
    entered: 2026-03-16
created: 2026-03-15        # Project creation date
```

State transitions follow the phase-gate system — a transition checklist must pass before the phase advances.

## Schema Directory (`schema/`)

Contains YAML schema files defining each artifact type:

### Schema Structure
Each schema file defines:
- `type`: Artifact type name (e.g., `requirement`)
- `prefix`: ID prefix (e.g., `REQ`)
- `id_format`: Regex pattern for valid IDs
- `required_fields`: List of mandatory frontmatter fields
- `optional_fields`: List of additional allowed frontmatter fields
- `allowed_status`: Map of status values with allowed predecessor statuses
- `allowed_link_roles`: List of valid link roles for this artifact type
- `directory`: Target directory for artifacts of this type

### Schema File Locations
- **Distribution**: Stored in `src/specflow/templates/schemas/` in the package
- **Runtime**: Copied to `.specflow/schema/` during `specflow init`
- **Validation**: Loaded by `lib/schema_validator.py` to validate artifacts

## Impact-Log Directory (`impact-log/`)

Records every fingerprint change event as individual YAML files:
- **Naming**: `<ARTIFACT-ID>_<ISO-timestamp>.yaml` (artifact-first for fast querying)
- **Content**: Changed artifact, change type, old/new fingerprints, flagged suspects, resolved status
- **Append-only**: Events are never deleted, only marked resolved

## Checklist-Log Directory (`checklist-log/`)

Records every checklist execution:
- **Naming**: `<ISO-timestamp>_<CHECKLIST-ID>.yaml` (timestamp-first for chronological ordering)
- **Content**: Checklist ID, items checked, pass/fail results, timestamp

## Baselines Directory (`baselines/`)

Immutable project state snapshots:
- **Naming**: `<version-name>.yaml` (e.g., `v1.0.yaml`, `release-candidate.yaml`)
- **Content**: Artifact name → status + fingerprint mapping, test summary
- **Immutability**: Once created, baseline files are never modified

## Locks Directory (`locks/`)

Filesystem locks preventing concurrent artifact modification:
- **Naming**: `<ARTIFACT-ID>.lock`
- **Content**: PID of the process holding the lock
- **Protocol**: Check for lock file → create with current PID → do work → remove lock file

## Standards Directory (`standards/`)

Imported compliance standards:
- Populated by industry packs or manual import
- YAML files defining standard clauses with IDs and descriptions
- Referenced by artifacts via `complies_with` link role

## Design Principles

1. **Hidden directory**: The `.specflow/` prefix keeps internals out of the way of normal file browsing
2. **Human-readable**: All internal files are YAML — inspectable and editable by humans if needed
3. **No cloud dependencies**: Everything is local filesystem operations
4. **Additive-only**: New fields added to configs/states over time; existing fields never removed (lazy migration)
