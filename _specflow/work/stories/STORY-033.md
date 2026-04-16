---
id: STORY-033
title: "Build the 8 Tier 1 conversational skills \u2014 init, review, audit, ship"
type: story
status: draft
priority: high
tags:
- UX
- skills
- M4-ux
suspect: false
links:
- target: STORY-032
  role: depends_on
created: '2026-04-17'
---

# Build the 8 Tier 1 conversational skills — init, review, audit, ship

## Description

With the over-exposed skill directories removed (STORY-032), build the target skill surface: **8 Tier 1 conversational skills** that give users a seamless, productive experience. The CLI surface (25 commands) stays unchanged — this story only creates/rewrites the SKILL.md prompts and their reference/script directories.

## Target Skill Surface

| # | Skill | Action | Composes CLI commands |
|---|-------|--------|-----------------------|
| 1 | `/specflow-init` | **New** | `init`, `hook install`, `ci generate`, installs skill facades |
| 2 | `/specflow-discover` | Keep as-is | (already ships) |
| 3 | `/specflow-plan` | Keep as-is | (already ships) |
| 4 | `/specflow-execute` | **Modify** — absorb `done` as final step | `go`, `update`, `create --type ut/it/qt`, `done` |
| 5 | `/specflow-review` | **New** — merges artifact-review + change-impact-review | `artifact-lint`, `checklist-run`, `artifact-review`, `change-impact`, `detect` |
| 6 | `/specflow-audit` | **Rewrite** from project-audit | `project-audit`, adversarial wings |
| 7 | `/specflow-ship` | **New** | `baseline create`, `document-changes`, `project-audit --quick` |
| 8 | `/specflow-pack-author` | Keep as-is | (already ships) |

## Deliverables

### Template unification

- Delete `src/specflow/templates/skills/gemini/` and `src/specflow/templates/skills/opencode/`
- Rename `src/specflow/templates/skills/claude/` to `src/specflow/templates/skills/shared/`
- Update `src/specflow/lib/platform.py`: `get_skills_platform_dir()` returns the same `shared/` directory regardless of platform — only the *target install directory* differs (`.claude/skills/`, `.opencode/skills/`, `.gemini/skills/`)
- The single canonical SKILL.md (currently the Claude version, the most complete) is the source of truth for all platforms
- Ensure `references/` subdirectories ship with the shared templates

### `/specflow-init` (new)
- Conversational bootstrap: asks about project type, preset, CI provider, standards packs
- Calls `specflow init` with appropriate flags
- Installs git hook via `specflow hook install`
- Optionally generates CI workflow via `specflow ci generate`
- Reports what was scaffolded and recommends `/specflow-discover`

### `/specflow-execute` (modify)
- Add final step: after all stories are implemented, offer phase closure
- Calls `specflow done` to extract prevention patterns and transition state
- User can skip this with "not yet" — closure is not forced

### `/specflow-review` (new — replaces artifact-review + change-impact-review)
- **Scoped conversationally** — the skill determines depth from user intent:
  - "review REQ-001" → runs `artifact-review --depth normal` on that artifact
  - "review recent changes" → discovers unreviewed DECs, runs `change-impact` pipeline
  - "review everything changed this sprint" → broader scope
- Composes: `artifact-lint` → `checklist-run` → `artifact-review` → optional adversarial lenses
- Reports findings by severity, offers remediation commands
- The key UX: user says "review" and the skill figures out the right composition

### `/specflow-audit` (rewrite from project-audit)
- Full-project health review
- Zero-question core: runs `project-audit` deterministically (horizontal + vertical + cross-cutting)
- Optional adversarial wings (16 lenses via 2 parallel subagents)
- Creates AUD and CHL artifacts

### `/specflow-ship` (new — replaces the missing `/specflow-release`)
- Release workflow: `baseline create <tag>` → `document-changes --since <prev>` → `project-audit --quick`
- Presents release summary with links to baseline, DECs, audit report
- Advisory if audit severity ≥ error — user must confirm to proceed

## Acceptance Criteria

1. All 8 skill directories exist in `.claude/skills/` with valid `SKILL.md` files
2. Each `SKILL.md` follows `docs/skill-standards.md` conventions (under 500 lines, references in `references/`, scripts in `scripts/`)
3. `/specflow-review` correctly scopes to artifact-level OR change-impact based on user input
4. `/specflow-execute` offers phase closure via `specflow done` as a final step
5. `/specflow-ship` produces a baseline, DECs, and audit report in sequence
6. `/specflow-init` conversational flow covers: project type → preset → CI → standards → skill install
7. No skill references a deleted skill directory
8. Existing skills (discover, plan, pack-author) are untouched
9. Every skill that offers the user a choice includes "(Recommended)" labels on the suggested default
10. `/specflow-discover` has a documented question cap of 15-20 questions; if more are needed, the skill suggests the user may want to refine requirements first (which likely means the discover→plan pipeline needs restructuring)
11. `/specflow-discover` includes an explicit escape hatch rule: "If the user signals they've provided enough context (e.g., 'that's enough', 'move on', 'skip'), immediately proceed to artifact generation with what you have"
12. `/specflow-pack-author` ends with a next-step recommendation (e.g., "Run `/specflow-init` to install this pack into a project")
13. `/specflow-execute` phase closure step includes a proper conversational flow (not a thin stub) — summarize accomplishments, extract prevention patterns, recommend archival
14. `/specflow-review` (which absorbs change-impact-review) presents a Human-Review Summary before filing any CHL artifacts
15. Only one canonical SKILL.md per skill exists in `templates/skills/shared/` — no platform-specific variants

## Out of Scope

- Changing any CLI command behavior
- Deleting old skill directories (STORY-032)
- Updating documentation (STORY-034)

## Dependencies

- STORY-032 (over-exposed skill dirs must be deleted first to avoid confusion)
