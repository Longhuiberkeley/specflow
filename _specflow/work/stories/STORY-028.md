---
id: STORY-028
title: "Compliance rework \u2014 BYOC with /specflow-pack-author"
type: story
status: implemented
priority: medium
tags:
- compliance
- BYOC
- M2-extensible
suspect: false
created: '2026-04-14'
checklists_applied:
- checklist: check-STORY-028
  timestamp: '2026-04-14T17:03:23Z'
---

# Compliance rework — BYOC with /specflow-pack-author

## Description

Fix the BYOS (Bring-Your-Own-Standard) gap identified in retrospective §10. The mechanism works but the ecosystem is empty — one demo pack with stub clauses. Ship `/specflow-pack-author` skill for LLM-assisted pack creation from PDF/URL/text. Relabel the ISO 26262 pack honestly. Write the manual pack-authoring guide.

### Deliverables

1. **`/specflow-pack-author` skill** — LLM-assisted authoring of a standards pack from PDF, URL, or pasted text. Composes: source ingestion → clause extraction → schema scaffolding → pack manifest generation → optional install. Uses the standards-ingestion axis of the adapter framework (STORY-026).

2. **Relabel ISO 26262 pack** — Rename `src/specflow/packs/iso26262/` → `src/specflow/packs/iso26262-demo/` with honest README: "5 stub clauses from ISO 26262, for framework testing only. Not a compliance pack."

3. **`docs/authoring-a-pack.md`** — Manual path for users who don't want LLM assistance. Step-by-step guide to creating a pack directory with YAML schemas and standards definitions.

4. **Update `docs/plan.md`** — Scope BYOS from "PDF ingestion" to "LLM-assisted pack authoring + manual YAML path" per retrospective §10.

## Acceptance Criteria

1. `/specflow-pack-author` skill exists in `.claude/skills/specflow-pack-author/` and can ingest a PDF file, extract clauses, and generate a complete pack directory structure (`pack.yaml`, `standards/*.yaml`, `schemas/*.yaml`, `README.md`)

2. The ISO 26262 pack directory is renamed to `iso26262-demo` and its README clearly states it contains stub clauses for testing only

3. `docs/authoring-a-pack.md` exists and documents the manual YAML path for creating a pack without LLM assistance

4. `specflow init --preset iso26262-demo` works (updated preset name)

5. The pack-install mechanism (`lib/scaffold.py:92-168`) continues to work unchanged

## Out of Scope

- PDF parser library integration (replaced by LLM-assisted approach)
- Additional standards packs (ISO 14971, ASPICE, etc.) — community territory
- `/specflow-project-audit` compliance scope (STORY-030)

## Dependencies

- STORY-026 (adapter framework — pack-author uses the standards-ingestion axis)
- STORY-022 (command rename — ensure consistent naming)
