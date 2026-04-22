---
id: ARCH-002
title: Framework Machinery
type: architecture
status: implemented
priority: high
rationale: 'The .specflow/ directory contains all framework internals: configuration,
  state, schemas, impact tracking, and baselines'
tags:
- framework
- internals
- core
suspect: false
fingerprint: sha256:4c258ae314a4
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
modified: '2026-04-21'
version: 1
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
│   ├── defect.yaml
│   ├── audit.yaml
│   └── challenge.yaml
├── impact-log/           # Change detection events (artifact-first naming)
├── checklist-log/        # Checklist execution audit log
├── baselines/            # Immutable project state snapshots
│   └── v0.2.0.yaml       # Baseline: name, git_ref, artifact statuses+fingerprints
├── audits/               # Project audit reports and cache
│   ├── .cache/           # Fingerprint-based audit finding cache
│   └── <TIMESTAMP>/      # Per-audit report directory
│       ├── report.md
│       ├── subagent-horizontal.md
│       ├── subagent-vertical.md
│       └── subagent-cross-cutting.md
├── locks/                # Filesystem locks for parallel operations
└── standards/            # Imported compliance standards
```

## `config.yaml`

Project-level configuration:

```yaml
project:
  name: "specflow"
  created: "2026-04-10"

impact_analysis:
  auto_flag: true
  auto_resolve: false
  remind_after: 7d

artifact_types:
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
  - audit
  - challenge

active_packs: []
```

## `state.yaml`

Workflow state machine:

```yaml
current: complete
history:
  - phase: discovering
    entered: 2026-04-10
    exited: 2026-04-11
  - phase: specifying
    entered: 2026-04-11
    exited: 2026-04-14
  - phase: planning
    entered: 2026-04-14
    exited: 2026-04-15
  - phase: executing
    entered: 2026-04-15
    exited: 2026-04-21
created: 2026-04-10
```

## Schema Directory (`schema/`)

Each schema file defines:
- `type`: Artifact type name
- `prefix`: ID prefix (e.g., `REQ`)
- `id_format`: Regex pattern for valid IDs
- `required_fields`: Mandatory frontmatter fields
- `optional_fields`: Additional allowed fields (e.g., `reqif_metadata`, `review_status`)
- `allowed_status`: Map of status values with allowed predecessors
- `allowed_link_roles`: Valid link roles for this type
- `directory`: Target directory

Schema extensibility: industry packs add new schema files at init time.

## Impact-Log Directory (`impact-log/`)

Records every fingerprint change event:
- **Naming**: `<ARTIFACT-ID>_<ISO-timestamp>.yaml`
- **Content**: Changed artifact, change type, old/new fingerprints, flagged suspects, resolved status
- **Append-only**: Events never deleted, only marked resolved

## Baselines Directory (`baselines/`)

Immutable project state snapshots:
- **Naming**: `<version-name>.yaml`
- **Content**: Artifact name → status + fingerprint mapping, git_ref
- **Immutability**: Baseline files never modified after creation
- **Diff**: `specflow baseline diff v0.1.0 v0.2.0` reports added/removed/modified

## Audits Directory (`audits/`)

Project audit artifacts and caching:
- **`.cache/`**: Fingerprint-based finding cache to skip redundant analysis
- **`<TIMESTAMP>/`**: Per-audit output with report.md and subagent detail files

## Design Principles

1. **Hidden directory**: `.specflow/` keeps internals out of normal browsing
2. **Human-readable**: All files are YAML — inspectable and editable
3. **No cloud dependencies**: Everything is local filesystem
4. **Additive-only**: New fields added over time; existing fields never removed
