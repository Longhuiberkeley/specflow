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
modified: '2026-10-08'
fingerprint: sha256:665f4ab48469
thinking_techniques:
- assumption_surfacing
- devils_advocate
- premortem
- worst_case_user
version: 5
---

# Compliance & Exchange Subsystem

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-028, R1-103); earlier text described uuid5 UUIDs, a `.reqifz` ZIP archive, a `standards-gaps` command, `src/specflow/schemas/optional/` and a per-clause pack tree. AC1 now names the shipped deterministic identifiers (sha256 `_new_id` plus artifact-ID SPEC-OBJECT identifiers) instead of UUIDs.

Provides supply-chain interchange, compliance tracking, and immutable project snapshots for regulated industries.

## Components

### 1. ReqIF Import/Export (`reqif.py`)

**Purpose**: Round-trip interchange with DOORS, Polarion, and other ALM tools. The `reqif` adapter (`lib/adapters/reqif.py`) delegates to `lib/reqif.import_reqif()` and `lib/reqif.export_reqif()`.

**Import path** (`specflow import --adapter reqif <file>`):
1. Parse a ReqIF 1.2 XML file (namespaced, with a namespace-free fallback)
2. Map each ReqIF `<SPEC-OBJECT>` to a SpecFlow requirement (REQ); `ReqIF.Name`, `ReqIF.Text`, `ReqIF.Description` and the `SpecFlow.*` attributes fill title, body, rationale, status, priority and tags
3. Preserve unmapped attributes in the `reqif_metadata` frontmatter field
4. Assign the next sequential REQ ID via `create_artifact()`; the source ReqIF identifier is kept in `reqif_metadata.identifier`, and a status outside draft/approved/implemented/verified falls back to `draft`
5. Create artifacts in `_specflow/specs/requirements/`

**Export path** (`specflow export --adapter reqif --output <file>`):
1. Collect artifacts by type (REQ, ARCH, DDD)
2. Use the SpecFlow artifact ID directly as each `SPEC-OBJECT` IDENTIFIER; generate the remaining element identifiers deterministically with `_new_id(prefix, seed)` = `_<prefix>-` + `sha256("<prefix>:<seed>")[:10]` (lib/reqif.py)
3. Map SpecFlow frontmatter to ReqIF `<ATTRIBUTE-VALUE-STRING>` elements (`ReqIF.Name`, `ReqIF.Text`, `ReqIF.Description`, `SpecFlow.Status`, `SpecFlow.Priority`, `SpecFlow.Tags`, `SpecFlow.Type`)
4. Preserve `reqif_metadata` as custom attributes
5. Write plain ReqIF XML with an XML declaration (no archive)

**Deterministic identifiers**: The same artifact always exports with the same SPEC-OBJECT IDENTIFIER and the same type, attribute-definition and hierarchy identifiers, so identifiers are stable across exports. The header's `CREATION-TIME` is the export time, so the file bytes are not identical between runs.

### 2. Standards Packs (`standards.py`)

**Purpose**: Bring-your-own-compliance via YAML schema definitions.

**Pack Structure** (authored by `/specflow-pack-author` into `.specflow/packs/<name>/`; the bundled `iso26262-demo` pack has the same shape):
```
.specflow/packs/<name>/
├── pack.yaml               # name, version, description, adds_artifact_types, adds_directories
├── standards/<name>.yaml   # standard, title, version, flat `clauses:` list
├── schemas/                # Only when the pack adds artifact types
│   └── <type>.yaml
└── README.md
```

Applying a pack (`specflow init --preset <name>`, `scaffold.apply_pack()`) copies its `standards/*.yaml` into `.specflow/standards/` without overwriting existing files. `lib/standards.py` reads `.specflow/standards/<name>.yaml`.

**Gap Analysis v2** (`specflow standards gaps`):
1. Load installed standards from `.specflow/standards/` (`--standard <name>` picks one when several are installed)
2. Map existing artifacts to clauses via `complies_with` links (`check_compliance()`)
3. Compute coverage score per standard: `(covered_clauses / total_clauses) * 100`, rounded to one decimal
4. Sort uncovered clauses by severity (high/medium/low) with priority tiebreak
5. Generate rule-based remediation suggestions per clause category (safety, security, functional, process), each with the scaffolding command `specflow create --from-standard <clause-id>`
6. Display summary dashboard with the standard's total, covered and uncovered counts, score, and the uncovered clauses with their remediation
7. Support `--json` flag for machine-readable output

**Optional Artifact Type Schemas** (`specflow init --with-types`):
1. Detect optional schemas in `src/specflow/templates/schemas/optional/` (hazard, risk, control)
2. Copy selected schemas into `.specflow/schema/` at init time
3. Create corresponding directories (with an empty `_index.yaml`) under `_specflow/`
4. Register selected types in `.specflow/config.yaml` (`artifact_types`)
5. New types integrate with `create`, `trace`, and `artifact-lint` via the shared `TYPE_TO_PREFIX` mapping

**Pack Authoring** (`/specflow-pack-author` skill):
1. Extract table of contents from source document (PDF/URL/text)
2. Scope extraction to selected sections
3. Chunk by section boundaries, preserving clause numbering
4. Generate `{id, title, description}` YAML per chunk
5. Verification layer: spot-check 2-3 sections against source

### 3. Baselines (`baselines.py`)

**Purpose**: Immutable project state snapshots for audit trails.

**Baseline Structure** (`.specflow/baselines/v0.2.0.yaml`):
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
- `specflow baseline create <name>` — Snapshot current state (`--evidence` also writes a compliance evidence report)
- `specflow baseline diff <name1> <name2>` — Compare snapshots
- Baselines are immutable: created once by exclusive create, never overwritten

### 4. Change Records (`document_changes.py`)

**Purpose**: Retroactive narrative of what changed between releases.

**Generation** (`specflow document-changes --since <ref>`):
1. Read git log since reference commit/tag
2. Extract changed files in `_specflow/` directories
3. For each commit affecting spec artifacts: create `DEC-*` artifact (commits already recorded in an existing DEC are skipped)
4. DEC contains: commit hash, author, date, changed artifacts, impact events

**Linking**:
- Each DEC links to affected artifacts via `addresses` role
- DECs are tagged `change-record` and `auto-generated`

## Acceptance Criteria

1. `specflow export --adapter reqif` produces valid ReqIF 1.2 with deterministic identifiers (artifact IDs as SPEC-OBJECT identifiers, sha256-derived `_new_id` for the rest)
2. `specflow import --adapter reqif` recreates artifacts with preserved `reqif_metadata`
3. `specflow standards gaps` shows per-standard coverage percentage
4. `specflow baseline create v1.0` produces immutable snapshot
5. `specflow document-changes --since v0.1.0` generates DEC artifacts for all spec changes
