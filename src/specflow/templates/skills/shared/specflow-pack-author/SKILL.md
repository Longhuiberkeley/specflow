---
name: specflow-pack-author
description: "Author a standards compliance pack from a PDF, URL, or pasted text."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Pack Author

Guide the user through agent-assisted creation of a standards compliance pack. The pack is written to `.specflow/packs/{name}/`, where `specflow init --preset {name}` resolves it by name.

## Workflow

### Step 1: Source Ingestion

Ask the user what source they want to build the pack from:

| Source | How to handle |
|--------|---------------|
| **PDF file** | Read the PDF with your host's file/PDF reading capability; if it has none, ask the user to paste the text. Extract clause structure (section numbers, titles, descriptions). |
| **URL** | Fetch the URL with your host's web-fetch capability; if it has none, ask the user to paste the page text. Extract clause structure from the page content. |
| **Pasted text** | Ask the user to paste the standard text. Extract clause structure. |

For each source, extract:
- **Standard name** — short identifier (e.g., `iso26262`, `aspice`, `internal-security-policy`)
- **Standard title** — full title
- **Clauses** — list of `{id, title, description}` tuples from the document

### Large Documents

For documents over ~30 pages or multi-part standards (e.g., ISO 26262 Parts 1-12), follow the bounded extraction protocol in `references/large-documents.md`: TOC first, the user picks sections, extract one section at a time, deduplicate, spot-check. If the platform cannot read PDFs natively, ask the user to paste the text or provide a URL — never fail silently. For small documents, extract all clauses directly and run the spot-check.

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

Ask: "Does this standard introduce any new artifact types beyond the built-in ones?" (The installed types are the files in `.specflow/schema/`; `specflow schema <type>` shows one.)

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
# Optional: adds_skills (skill directory names under skills/) and context_snippet (see references/pack-structure.md)
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
    # category: safety | security | functional | process   (optional, default functional)
  # ... all clauses
```

#### `schemas/{type}.yaml` (if applicable)
```yaml
type: {type}
prefix: {PREFIX}
id_format: "^{PREFIX}-\\d{3,5}(\\.\\d{1,3})?$"
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
allowed_status:          # target status: statuses it can be entered from
  draft: []              # entry status
  approved:
    - draft              # approved is reached from draft
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

Run the pack validation command to verify the generated structure is sound:

```
specflow pack-validate .specflow/packs/{name}/
```

The command checks that `pack.yaml` has `name`/`version`/`description`, every `adds_skills` entry has `skills/<name>/SKILL.md`, each `standards/*.yaml` (when shipped) has `standard`/`title`/`clauses`, each `schemas/*.yaml` (when shipped) has `type`/`prefix`/`id_format`/`required_fields`/`allowed_status`/`directory`, and no shipped skill script contains `uv run`. If any check fails, fix it before proceeding.

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
- **New or already-initialized project:** `specflow init --preset {name}` resolves the pack from `.specflow/packs/{name}/` and installs it — standards, schemas, directories, skills, and context block — and registers it in `active_packs`. On an initialized project it runs in merge mode and keeps your config.
- **After editing the pack:** `specflow refresh --packs --force` syncs the changes into the project.
- **Reuse across projects:** copy the whole `.specflow/packs/{name}/` directory into each project's `.specflow/packs/`.
```

**Exit message:** "The pack is at `.specflow/packs/{name}/`. To install it, run `specflow init --preset {name}` (the pack is picked up from that directory), or use `/specflow-init` and name it as the preset."

Next: run `/specflow-discover`, or `specflow create --from-standard <clause-id>` for each uncovered clause that `specflow standards gaps` lists.

## Rules

- Never fabricate clauses that aren't in the source document. If a section is unclear, mark it with a comment `# TODO: verify clause text`.
- Preserve the original clause IDs from the source standard.
- Keep descriptions concise but complete — one to two sentences.
- If the user provides a multi-part standard (e.g., ISO 26262 Parts 1-12), ask which parts to include before extraction.

## References

- `references/schema-template.md` — YAML schema format for new artifact types
- `references/large-documents.md` — bounded extraction protocol for long or multi-part standards
- `references/pack-structure.md` — Detailed explanation of pack directory layout and field semantics
- `references/example-packs.md` — Example pack structures (iso26262-demo, minimal pack)

## Scripts

- `scripts/validate-pack.sh` — Thin wrapper around `specflow pack-validate`
