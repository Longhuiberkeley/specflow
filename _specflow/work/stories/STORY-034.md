---
id: STORY-034
title: "Documentation overhaul \u2014 rewrite lifecycle, commands, and README for\
  \ 8-command surface"
type: story
status: draft
priority: high
tags:
- UX
- documentation
- M4-ux
suspect: false
links:
- target: STORY-033
  role: depends_on
created: '2026-04-17'
---

# Documentation overhaul — rewrite lifecycle, commands, and README for 8-command surface

## Description

With the 8-command skill surface in place (STORY-033), rewrite all user-facing documentation to reflect it. The docs should present SpecFlow as a seamless conversational experience, not a CLI tool. Power-user CLI commands are documented in an appendix.

## Deliverables

1. **`docs/lifecycle.md`** — Rewrite with updated flowchart showing:
   - Review and audit as **separate** nodes (not merged)
   - 8 Tier 1 skills in the tiered table
   - Tier 2/3 collapsed into "CLI Reference for Power Users" section
   - No mention of deleted skill directories

2. **`docs/commands.md`** — Rewrite with 8 interface specs:
   - `/specflow-init`
   - `/specflow-discover`
   - `/specflow-plan`
   - `/specflow-execute` (includes phase closure)
   - `/specflow-review` (scoped conversationally)
   - `/specflow-audit` (full-project, periodic)
   - `/specflow-ship` (release workflow)
   - `/specflow-pack-author`
   - Remove the status note at top about "documented-but-not-yet-shipped"

3. **`docs/getting-started.md`** — Update tutorial to use the 8-command surface only. No mention of `uv run specflow` commands in the tutorial flow.

4. **`AGENTS.md` SpecFlow section** — Update the "Commands" table to show 8 Tier 1 skills instead of `specflow init`, `specflow status`, `specflow validate`.

5. **`README.md`** — Update to emphasize skill-based workflow. CLI commands mentioned only in "Power Users" section.

6. **Power Users CLI appendix** (either in `docs/commands.md` or new `docs/cli-reference.md`) — Document all 25 CLI commands organized by phase, for users who want `uv run specflow` directly.

7. **Remove dead config reference** — Either wire `release_gate.severity` to actual behavior or remove it from `adapters.yaml` template.

8. **`templates/agents-section.md` rewrite** — Replace the current 15-line directory listing with a genuine onboarding paragraph that:
   - Tells the CLI agent what SpecFlow is and its mental model
   - Lists the 8 Tier 1 skills with one-line descriptions
   - Provides the expected lifecycle flow (init → discover → plan → execute → review → ship)
   - Notes that `.specflow/` internals should not be edited manually
   - Is concise enough to fit in AGENTS.md without dominating it (target: 30-40 lines)

## Acceptance Criteria

1. `docs/lifecycle.md` flowchart shows review and audit as separate skills
2. `docs/commands.md` documents exactly 8 Tier 1 skills with full interface specs
3. No doc references `/specflow-artifact-lint`, `/specflow-checklist-run`, `/specflow-change-impact-review`, `/specflow-document-changes`, `/specflow-baseline`, `/specflow-done`, `/specflow-go`, `/specflow-status`, `/specflow-create`, `/specflow-update`, `/specflow-detect`, `/specflow-hook`, `/specflow-fingerprint-refresh`, `/specflow-renumber-drafts`, `/specflow-import`, `/specflow-export` as user-facing skills (they are CLI commands for power users)
4. `AGENTS.md` and `README.md` are consistent with the new surface
5. `docs/getting-started.md` tutorial uses only the 8 skills
6. All 25 CLI commands are documented in a power-user appendix
7. `templates/agents-section.md` is a concise onboarding paragraph (30-40 lines) that gives the CLI agent a working mental model of SpecFlow, not just a directory listing

## Out of Scope

- Deleting skill directories (STORY-032)
- Creating/rewriting skills (STORY-033)
- Changing CLI command behavior

## Dependencies

- STORY-033 (skill surface must be finalized before documenting it)
