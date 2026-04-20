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

### Large Document Strategy

For documents over ~30 pages or multi-part standards (e.g., ISO 26262 Parts 1-12), follow this structured extraction protocol. The goal is to constrain the LLM to predictable, bounded tasks rather than unbounded whole-document reasoning.

#### Phase 1: Table of Contents Extraction

1. **Extract the TOC first.** If reading a PDF, most standards documents have a structured table of contents. Extract only section numbers and titles — nothing else. If the platform cannot read PDFs natively, ask the user to paste the TOC or provide a URL.
2. **Present TOC as a selection menu.** Show the user the full section list and ask: "Which sections should this pack cover?" For multi-part standards, suggest one pack per part.
3. **One pack per standard, not per PDF.** If the source is a multi-part standard, suggest creating one pack per part or a combined pack with clauses from selected parts. Ask the user which approach they prefer.

#### Phase 2: Section-by-Section Extraction

For each user-selected section:

1. **Chunk by section boundaries, not page ranges.** Extract one section at a time using its heading boundaries (e.g., Section 3.1 heading through Section 3.2 heading). Never chunk by page number — page breaks are arbitrary in standards documents.
2. **Constrain output per chunk.** For each section, produce only `{id, title, description}` tuples. No analysis, no interpretation, no adding requirements that aren't explicitly stated. If a section is unclear, output the clause with a `# TODO: verify clause text` comment rather than guessing.
3. **Preserve hierarchy.** Maintain the original clause numbering (e.g., `ISO26262-3.7`, `ISO26262-4.6.2`) so traceability maps back to the source document.
4. **Summarize, don't copy.** Clause descriptions should be one to two sentences capturing the normative requirement, not verbatim copies of long explanatory text. The goal is traceability, not reproduction.

#### Phase 3: Deduplication Pass

After all sections are extracted:

1. **Check for overlaps.** Adjacent sections may produce clauses that overlap (e.g., a clause referenced in both Section 3.1 and 3.2 summaries). Merge any duplicate clause IDs, keeping the more complete description.
2. **Verify ID uniqueness.** Ensure no two clauses share the same `id` field.

#### Phase 4: Verification (Spot-Check)

After extraction and dedup:

1. **Random spot-check.** Select 2-3 source sections at random. Re-read them and compare against the extracted clauses. Report any sections where:
   - Clauses visible in the source were not extracted
   - Extracted clause count doesn't match the number of visible headings
2. **Emit verification comments.** Add a comment block at the top of the generated `standards/{name}.yaml`:
   ```yaml
   # VERIFY: spot-checked sections {X}, {Y}, {Z} — {N} clauses found vs {M} extracted
   # If N != M, discrepancies are noted below.
   ```
3. **Report discrepancies to the user.** If any spot-check reveals missing clauses, present them and ask: "I found clauses in section X that weren't extracted. Should I add them?"

#### Platform Awareness

- If the AI platform has native PDF reading (Claude Code, Gemini CLI, etc.), use the `Read` tool directly on the PDF file.
- If the platform cannot read PDFs, fall back to asking the user to paste text or provide a URL. Never fail silently — always tell the user what's needed.

For small documents (under ~30 pages), skip the full protocol: extract all clauses directly, run the verification spot-check, and proceed.

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
- **For reuse across projects:** Copy the entire `.specflow/packs/{name}/` directory into `src/specflow/packs/` of your SpecFlow installation.
```

**Exit message:** Recommend the next step to the user: "Run `/specflow-init` to install this pack into a project using `--preset {name}`."

## Rules

- Never fabricate clauses that aren't in the source document. If a section is unclear, mark it with a comment `# TODO: verify clause text`.
- Preserve the original clause IDs from the source standard.
- Keep descriptions concise but complete — one to two sentences.
- If the user provides a multi-part standard (e.g., ISO 26262 Parts 1-12), ask which parts to include before extraction.
- **Adapter framework (optional):** If `src/specflow/lib/adapters/base.py` is present, use `StandardsAdapter.ingest_standard(source, source_type)` for clause extraction — it returns a structured list of `{id, title, description}` dicts. Falls back to direct LLM parsing if the adapter is unavailable or returns empty results.

## References

- `references/schema-template.md` — YAML schema format for new artifact types
- `references/pack-structure.md` — Detailed explanation of pack directory layout and field semantics
- `references/example-packs.md` — Example pack structures (iso26262-demo, minimal pack)

## Scripts

- `scripts/validate-pack.sh` — Deterministic validation of a pack directory structure
