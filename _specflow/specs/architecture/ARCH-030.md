---
id: ARCH-030
title: 'Skills subsystem: router anatomy, reference layering, and CLI invocation contract'
type: architecture
status: approved
rationale: 'Companion architecture to DEC-083: the structure every SpecFlow skill
  follows so context cost stays bounded and deterministic work runs in the CLI (REQ-042).'
tags:
- skills
- architecture
- context-audit
suspect: false
links:
- target: REQ-042
  role: derives_from
- target: DEC-083
  role: guided_by
created: '2026-09-13'
fingerprint: sha256:41c75db94fdb
modified: '2026-09-13'
---

# Skills subsystem: router anatomy, reference layering, and CLI invocation contract

## Anatomy

A skill directory strictly contains:

```text
<skill>/
├── SKILL.md       # Required: router — frontmatter + imperative workflow
├── references/    # Optional: domain knowledge loaded ON DEMAND
└── scripts/       # Optional: genuine per-skill tooling only (exception: specflow-pack-author)
```

## Router model (SKILL.md)

- **Frontmatter:** `name` + `description`. The description is the only always-on routing surface: one narrow line stating when the skill is REQUIRED.
- **Body:** minimal router under 500 lines — workflow steps, hard invariants, and contextual pointers into `references/` ("if X, read references/Y.md"). No domain essays, no recipes restating CLI output.
- **References:** each file states its consult-when trigger up front and dedupes to invariants; sibling references cross-point instead of repeating.

## Invocation contract

Deterministic operations (link validation, fingerprints, ranking, wave computation, checklist assembly) run in the Python CLI. Skills call bare `specflow <cmd>` (e.g. `specflow artifact-lint`, `specflow trace`, `specflow brief`) — never `uv run specflow`, which breaks in consuming projects that install via `uv tool install git+...` (see the bootstrap bug in AGENTS.md section 6).

## Layering

`src/specflow/templates/skills/shared/<skill>/` (shipped, byte-identical mirror of `.claude/skills/<skill>/` dogfood copy) → `specflow init`/`refresh` copies to each host platform's skill dir. Pack skills ship in `src/specflow/packs/<pack>/skills/` and install via `apply_pack`, which never overwrites user-edited files.

## Enforcement

Caps and shape are pinned by tests (e.g. adoption pack SKILL.md <500 lines), not prompt text — I3: enforcement lives in CLI and tests.
