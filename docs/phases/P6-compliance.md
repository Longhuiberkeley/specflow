# P6: Compliance & Standards

> **Stub** — Detailed design to be fleshed out when P4 is near completion.

## Goal

Enable industry-specific compliance by introducing standards packs that add artifact types, checklists, and gap analysis. Make SpecFlow viable for ISO 26262, ASPICE, DO-178C, IEC 62304, and SOX regulated projects.

## Rough Scope

### Standards pack architecture

- `specflow init --preset iso26262` / `--preset do178c` / `--preset iec62304` / `--preset sox`
- Each pack ships as a Python package under `packs/<name>/` with:
  - `manifest.yaml` (metadata, artifact types, additional frontmatter fields, link roles)
  - `standards/` (pre-parsed standard clauses as STD-* artifacts)
  - `schemas/` (additional artifact type definitions)
  - `checklists/` (domain-specific checklists)
  - `templates/` (HARA, FMEA, safety-case templates)

### ISO 26262 specific

- Hazard/SG/SR hierarchy: HAZ-* -> SG-* -> SR-* -> REQ-*
- ASIL criticality metadata on artifact frontmatter
- HARA and FMEA templates as structured checklists
- ASIL enforcement: ASIL-D requirements must have full V-model coverage

### Compliance gap analysis

- `specflow-compliance --standard iso26262` walks link graph
- Reports every standard clause with no project artifact satisfying it
- Coverage/traceability matrix output

### Baselines

- `specflow-baseline create v1.0` snapshots artifact state, fingerprints, test summaries
- `specflow-baseline diff v1.0 v2.0` compares two baselines
- Baselines stored as individual immutable YAML files in `.specflow/baselines/`

### Retroactive change records

- `specflow-document-changes --since HEAD~3` synthesizes CR/DEC from git diffs + impact-log
- CR is a projection, not a separate maintenance burden

## Dependencies

- P4 (traceability engine, impact-log, fingerprints needed for gap analysis and baselines)
