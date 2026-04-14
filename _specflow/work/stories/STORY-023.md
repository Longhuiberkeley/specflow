---
id: STORY-023
title: Archive docs/phases and restructure docs/ directory
type: story
status: draft
priority: medium
tags:
  - documentation
  - M1-clarity
suspect: false
created: '2026-04-14'
---

# Archive docs/phases and restructure docs/ directory

## Description

Move the P0–P8 phase docs from `docs/phases/` to `docs/.archive/phases/` with a one-line README explaining their historical nature. Restructure the docs directory to be user-facing rather than maintainer-facing. Create new docs: `lifecycle.md`, `commands.md`. Populate `README.md` with a proper project overview. Defer `getting-started.md` until M2 lands.

### Target docs/ structure

```
docs/
├── lifecycle.md              (new; flowchart + tiered command table)
├── commands.md               (new; interface spec per featured skill)
├── architecture.md           (existing; trim to maintainer essentials)
├── decisions.md              (existing; keep)
├── skill-standards.md        (existing; keep)
├── plan.md                   (existing; update BYOS scope per §10)
└── .archive/
    └── phases/               (old P0–P8 docs + README)
```

### README.md (repo root)

One-paragraph what-is, install line, link to docs/lifecycle.md.

## Acceptance Criteria

1. All P0–P8 phase docs are moved to `docs/.archive/phases/` with a README explaining they are historical

2. `docs/lifecycle.md` contains the flowchart from retrospective §2 and the tiered command table with new names

3. `docs/commands.md` contains one section per Tier 1 skill with the interface spec from retrospective §4 (reads, writes, side effects, exit behavior)

4. `README.md` is no longer empty — contains project description, install line, and link to docs

5. No broken internal links across docs (all cross-references use new command names from STORY-022)

6. `docs/plan.md` is updated to scope BYOS from "PDF ingestion" to "LLM-assisted pack authoring + manual YAML path" per retrospective §10

## Out of Scope

- `docs/getting-started.md` tutorial (deferred until M2 lands per retrospective §13.3)
- `docs/authoring-a-pack.md` (STORY-028)
- `docs/authoring-an-adapter.md` (STORY-026)

## Dependencies

- STORY-022 (command rename) — docs must reference new command names
