---
id: ARCH-004
title: Compliance & Exchange Subsystem
type: architecture
status: implemented
rationale: Architecture for ReqIF interchange, standards packs, baselines, and change
  records
suspect: false
links:
- target: REQ-005
  role: derives_from
- target: REQ-011
  role: derives_from
- target: REQ-015
  role: derives_from
- target: REQ-016
  role: derives_from
- target: REQ-017
  role: derives_from
created: '2026-04-21'
modified: '2026-04-21'
fingerprint: sha256:9358bc85b477
version: 1
---

# Compliance & Exchange Subsystem

Provides supply-chain interchange, compliance tracking, and immutable project snapshots for regulated industries.

## Components

### 1. ReqIF Import/Export (`reqif.py`)

**Purpose**: Round-trip interchange with DOORS, Polarion, and other ALM tools.

**Import path** (`specflow import --adapter reqif`):
1. Parse ReqIF 1.2 XML archive
2. Map ReqIF `<SPEC-OBJECT>` to SpecFlow artifact types (REQ, ARCH, DDD)
3. Preserve unmapped attributes in `reqif_metadata` frontmatter field
4. Generate deterministic SpecFlow IDs from ReqIF identifiers
5. Create artifacts in appropriate `_specflow/specs/` directories

**Export path** (`specflow export --adapter reqif`):
1. Collect artifacts by type (REQ, ARCH, DDD, UT, IT, QT)
2. Generate deterministic UUIDs: `uuid5(NAMESPACE_OID, artifact_id + content_hash)`
3. Map SpecFlow frontmatter to ReqIF `<ATTRIBUTE-VALUE-*>` elements
4. Preserve `reqif_metadata` as custom attributes
5. Package as `.reqifz` ZIP archive

**Deterministic UUIDs**: Same artifact always produces same UUID across exports, enabling idempotent round-trips.

### 2. Standards Packs (`standards.py`)

**Purpose**: Bring-your-own-compliance via YAML schema definitions.

**Pack Structure**:
```
standards/
├── iso26262/
│   ├── pack.yaml           # Pack metadata, artifact type extensions
│   ├── clauses/            # Individual standard clauses
│   │   ├── 3-7.yaml
│   │   └── 4-2.yaml
│   └── checklists/         # Compliance checklists
└── iec62304/
    └── ...
```

**Gap Analysis v2** (`specflow standards gaps`):
1. Load installed standards from `.specflow/standards/`
2. Map existing artifacts to clauses via `complies_with` links
3. Compute coverage score per standard: `(covered_clauses / total_clauses) * 100`
4. Sort uncovered clauses by severity (high/medium/low) with priority tiebreak
5. Generate rule-based remediation suggestions per category (missing_architecture, missing_implementation, missing_verification)
6. Display summary dashboard with per-standard scores, gap counts, and top remediation actions
7. Support `--json` flag for machine-readable output

**Optional Artifact Type Schemas** (`specflow init --with-types`):
1. Detect optional schemas in `src/specflow/schemas/optional/` (hazard, risk, control)
2. Copy selected schemas into `.specflow/schema/` at init time
3. Create corresponding directories in `_specflow/specs/`
4. Register selected types in `.specflow/config.yaml`
5. New types integrate with `create`, `trace`, and `artifact-lint` via the shared `TYPE_TO_PREFIX` mapping

**Pack Authoring** (`/specflow-pack-author` skill):
1. Extract table of contents from source document (PDF/URL/text)
2. Scope extraction to selected sections
3. Chunk by section boundaries, preserving clause numbering
4. Generate `{id, title, description}` YAML per chunk
5. Verification layer: spot-check 2-3 sections against source

### 3. Baselines (`baselines.py`)

**Purpose**: Immutable project state snapshots for audit trails.

**Baseline Structure** (`v0.2.0.yaml`):
```yaml
name: v0.2.0
created_at: '2026-04-21T10:59:03Z'
git_ref: a8e0d739f55a9571ebbd9048a86922cb8583b526
artifacts:
  REQ-001:
    status: approved
    fingerprint: sha256:c84eb2dd9906
    title: CLI Interface
    type: requirement
```

**Operations**:
- `specflow baseline create <name>` — Snapshot current state
- `specflow baseline diff <name1> <name2>` — Compare snapshots
- Baselines are immutable: created once, never modified

### 4. Change Records (`document_changes.py`)

**Purpose**: Retroactive narrative of what changed between releases.

**Generation** (`specflow document-changes --since <ref>`):
1. Read git log since reference commit/tag
2. Extract changed files in `_specflow/` directories
3. For each commit affecting spec artifacts: create `DEC-*` artifact
4. DEC contains: commit hash, author, date, changed artifacts, impact events

**Linking**:
- Each DEC links to affected artifacts via `addresses` role
- DECs are tagged `change-record` and `auto-generated`

## Acceptance Criteria

1. `specflow export --adapter reqif` produces valid ReqIF 1.2 with deterministic UUIDs
2. `specflow import --adapter reqif` recreates artifacts with preserved `reqif_metadata`
3. `specflow standards-gaps` shows per-standard coverage percentage
4. `specflow baseline create v1.0` produces immutable snapshot
5. `specflow document-changes --since v0.1.0` generates DEC artifacts for all spec changes
