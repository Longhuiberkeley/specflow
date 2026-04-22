---
id: STORY-034
title: "Documentation overhaul \u2014 rewrite lifecycle, commands, and README for\
  \ 9-command surface"
type: story
status: verified
priority: high
tags:
- UX
- documentation
- M4-ux
suspect: false
links:
- target: STORY-033
  role: depends_on
- target: UT-009
  role: verified_by
- target: IT-007
  role: verified_by
- target: QT-017
  role: verified_by
created: '2026-04-17'
fingerprint: sha256:55db9741b5bd
version: 1
modified: '2026-04-22'
---

# Documentation overhaul — rewrite lifecycle, commands, and README for 9-command surface

## Description

With the 9-command slash surface in place (STORY-033), rewrite all user-facing documentation to reflect it. SpecFlow's product is the `/specflow-*` slash command surface — the docs should lead with that. The `uv run specflow ...` CLI commands are a power-user appendix.

`/specflow-artifact-review` and `/specflow-change-impact-review` are documented as **separate** Tier 1 slash commands (not merged) — they do functionally different jobs and the project favors explicit naming.

## Deliverables

1. **`docs/lifecycle.md`** — Rewrite with updated flowchart showing:
   - `/specflow-artifact-review` and `/specflow-change-impact-review` as separate nodes
   - `/specflow-audit` as its own node (no longer merged with review)
   - 9 Tier 1 skills in the tiered table
   - Tier 2/3 collapsed into "CLI Reference for Power Users" section
   - No mention of deleted skill directories

2. **`docs/commands.md`** — Rewrite with 9 interface specs:
   - `/specflow-init`
   - `/specflow-discover`
   - `/specflow-plan`
   - `/specflow-execute` (includes phase closure)
   - `/specflow-artifact-review` (per-artifact quality review)
   - `/specflow-change-impact-review` (blast-radius review of recent commits/PRs)
   - `/specflow-audit` (full-project, periodic)
   - `/specflow-ship` (release workflow)
   - `/specflow-pack-author`
   - Remove the status note at top about "documented-but-not-yet-shipped"

3. **`docs/getting-started.md`** — Update tutorial to use the 9-command surface only. No mention of `uv run specflow` commands in the tutorial flow.

4. **`docs/getting-started.md` "Standards and Compliance" section** — Add a section explaining the standards ↔ REQ mental model:
   - Standards (installed via packs or `/specflow-pack-author`) are **immutable reference material** — the source of truth from external bodies (ISO, ASPICE, etc.)
   - REQs are the **project's own requirements** — owned, editable, adaptable. They may be copied from or inspired by standard clauses, then adapted to the project's context
   - The `complies_with` link provides **traceability** ("this REQ exists because of that clause"), not content equivalence
   - `specflow standards gaps` shows coverage (which clauses have no REQs yet)
   - `specflow create --from-standard <clause-id>` scaffolds a draft REQ pre-populated from a clause, ready for the user to adapt
   - The workflow: install pack → run `/specflow-discover` → discover detects uncovered clauses → scaffolds REQs → user adapts

5. **`AGENTS.md` SpecFlow section** — Update the "Commands" table to show 9 Tier 1 slash commands instead of `specflow init`, `specflow status`, `specflow validate`.

6. **`README.md`** — Update to emphasize skill-based workflow. CLI commands mentioned only in "Power Users" section.

7. **Power Users CLI appendix** (either in `docs/commands.md` or new `docs/cli-reference.md`) — Document all CLI commands organized by phase, including the 2 new ones (`standards gaps`, `create --from-standard`), for users who want `uv run specflow` directly.

8. **Remove dead config reference** — Either wire `release_gate.severity` to actual behavior or remove it from `adapters.yaml` template.

9. **`templates/agents-section.md` rewrite** — Replace the current 24-line directory listing with a genuine onboarding paragraph that:
   - Tells the CLI agent what SpecFlow is and its mental model (slash commands as product, CLI as power-user appendix)
   - Lists the 9 Tier 1 slash commands with one-line descriptions
   - Provides the expected lifecycle flow (init → discover → plan → execute → artifact-review / change-impact-review → ship)
   - Notes that `.specflow/` internals should not be edited manually
   - Is concise enough to fit in AGENTS.md without dominating it (target: 30-40 lines)

## Acceptance Criteria

1. `docs/lifecycle.md` flowchart shows `/specflow-artifact-review`, `/specflow-change-impact-review`, and `/specflow-audit` as three separate nodes (not merged into one review/audit super-node)
2. `docs/commands.md` documents exactly 9 Tier 1 slash commands with full interface specs
3. No doc references `/specflow-artifact-lint`, `/specflow-checklist-run`, `/specflow-document-changes`, `/specflow-baseline`, `/specflow-done`, `/specflow-go`, `/specflow-status`, `/specflow-create`, `/specflow-update`, `/specflow-detect`, `/specflow-hook`, `/specflow-fingerprint-refresh`, `/specflow-renumber-drafts`, `/specflow-import`, `/specflow-export`, `/specflow-project-audit`, `/specflow-release` as user-facing slash commands (the underlying CLI commands stay; they're documented in the power-user appendix)
4. `AGENTS.md` and `README.md` are consistent with the new 9-skill surface
5. `docs/getting-started.md` tutorial uses only the 9 slash commands
6. All CLI commands (including `standards gaps` and `create --from-standard`) are documented in a power-user appendix
7. `templates/agents-section.md` is a concise onboarding paragraph (30-40 lines) that gives the CLI agent a working mental model of SpecFlow (slash commands as product, CLI as appendix), not just a directory listing
8. `docs/getting-started.md` includes a "Standards and Compliance" section explaining: standards are immutable reference, REQs are owned copies, `complies_with` is traceability, the scaffold-from-clause workflow

## Out of Scope

- Deleting skill directories (STORY-032)
- Creating/rewriting skills (STORY-033)
- Changing CLI command behavior

## Dependencies

- STORY-033 (skill surface must be finalized before documenting it)
