---
name: specflow-pack-author
description: Use when the user wants to author a new standards compliance pack — from a PDF file, URL, or pasted text. Generates a complete pack directory with pack.yaml, standards clauses, and optional schemas.
---

# SpecFlow Pack Author

Guide the user through LLM-assisted creation of a standards compliance pack. The pack can later be installed into a SpecFlow project via `specflow init --preset` or manual copy.

## Workflow

### Step 1: Source Ingestion

Ask the user what source they want to build the pack from:

| Source | How to handle |
|--------|---------------|
| **PDF file** | Read the PDF with the `Read` tool. Extract clause structure (section numbers, titles, descriptions). |
| **URL** | Fetch the URL with the `WebFetch` tool. Extract clause structure from the page content. |
| **Pasted text** | Ask the user to paste the standard text. Extract clause structure. |

For each source, extract:
- **Standard name** — short identifier (e.g., `iso26262`, `aspice`, `internal-security-policy`)
- **Standard title** — full title
- **Clauses** — list of `{id, title, description}` tuples from the document

If the source is large, extract clauses progressively — ask the user which sections or parts they want to include, rather than trying to parse the entire document at once.

### Step 2: Confirm Pack Metadata

Present the extracted information to the user for confirmation:

```
## Pack Preview

**Pack name:** {name}
**Standard title:** {title}
**Clauses found:** {count}

### Sample clauses (first 3)
1. {clause-id} — {clause-title}: {description-preview}
2. ...
3. ...
```

Ask: "Does this look correct? Any clauses to add, remove, or merge?"

### Step 3: Schema Scaffolding (Optional)

Ask: "Does this standard introduce any new artifact types beyond the built-in ones (requirement, story, test, hazard, decision, spike, defect, audit, challenge)?"

- **If no:** Skip to Step 4.
- **If yes:** Ask what artifact type(s) and what fields they need. Read `references/schema-template.md` for the schema format. Generate one `.yaml` schema file per new type.

### Step 4: Generate Pack Directory

Create the pack directory at `.specflow/packs/{name}/` with the following structure:

```
.specflow/packs/{name}/
├── pack.yaml
├── standards/{name}.yaml
├── schemas/          (only if new artifact types in Step 3)
│   └── {type}.yaml
└── README.md
```

Generate each file:

#### `pack.yaml`
```yaml
name: {name}
version: "0.1.0"
description: "{short description}"
adds_artifact_types:
  - {type1}      # only if Step 3 created schemas
  - {type2}
adds_directories:
  - specs/{dir1}  # one per new artifact type
```

#### `standards/{name}.yaml`
```yaml
standard: {name}
title: "{full title}"
version: "{version from source}"
clauses:
  - id: "{clause-id}"
    title: "{clause-title}"
    description: "{clause-description}"
  # ... all clauses
```

#### `schemas/{type}.yaml` (if applicable)
```yaml
type: {type}
prefix: {PREFIX}
id_format: "^{PREFIX}-\\d{3}(\\.\\d{1,3})?$"
required_fields:
  - id
  - title
  - type
  - status
  - created
optional_fields:
  - priority
  - version
  - rationale
  - tags
  - suspect
  - fingerprint
  - links
  - modified
allowed_status:
  draft: []
  approved:
    - draft
allowed_link_roles:
  - refined_by
  - derives_from
  - complies_with
  - verified_by
directory: _specflow/specs/{dir}/
```

Use `type: {type}` and `prefix: {PREFIX}` based on the artifact type name (e.g., `type: hazard`, `prefix: HAZ`).

#### `README.md`
A brief description of the pack, its source, and what it covers.

### Step 5: Validate Pack

Run the pack validation script to verify the generated structure is sound:

```
bash .claude/skills/specflow-pack-author/scripts/validate-pack.sh .specflow/packs/{name}/
```

The script checks that `pack.yaml` has `name`/`version`/`description`, each `standards/*.yaml` has `standard`/`title`/`clauses`, and each `schemas/*.yaml` (if any) has `type`/`prefix`/`id_format`/`required_fields`/`allowed_status`/`directory`. If any check fails, fix it before proceeding.

### Step 6: Preview and Install

Present a summary to the user:

```
## Pack Generated: {name}

**Location:** `.specflow/packs/{name}/`
**Files:**
  - pack.yaml
  - standards/{name}.yaml ({clause_count} clauses)
  - schemas/*.yaml ({schema_count} types) ← only if applicable
  - README.md

### To install this pack:
- **For this project:** Copy `standards/*.yaml` → `.specflow/standards/` and `schemas/*.yaml` → `.specflow/schema/`
- **For reuse across projects:** Copy the entire `.specflow/packs/{name}/` directory into `src/specflow/packs/` of your SpecFlow installation, then run `specflow init --preset {name}`
```

Wait for user acknowledgement.

## Rules

- Never fabricate clauses that aren't in the source document. If a section is unclear, mark it with a comment `# TODO: verify clause text`.
- Preserve the original clause IDs from the source standard.
- Keep descriptions concise but complete — one to two sentences.
- If the user provides a multi-part standard (e.g., ISO 26262 Parts 1-12), ask which parts to include before extraction.
- If the adapter framework (STORY-026) is available in the codebase, use its standards-ingestion axis for clause extraction. Otherwise, extract clauses directly via LLM parsing as described above.

## References

- `references/schema-template.md` — YAML schema format for new artifact types
- `references/pack-structure.md` — Detailed explanation of pack directory layout and field semantics
- `references/example-packs.md` — Example pack structures (iso26262-demo, minimal pack)

## Scripts

- `scripts/validate-pack.sh` — Deterministic validation of a pack directory structure
