---
id: STORY-033
title: "Build the 9 Tier 1 conversational skills \u2014 init, audit, ship + modifications"
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
fingerprint: sha256:e150f32f8b00
version: 1
---

# Build the 9 Tier 1 conversational skills — init, audit, ship + modifications

## Description

With the over-exposed skill directories removed (STORY-032), build the target slash command surface: **9 Tier 1 conversational `/specflow-*` slash commands**. The slash command surface is the product; the `uv run specflow ...` Python CLI is a power-user appendix.

`/specflow-artifact-review` and `/specflow-change-impact-review` are kept as **separate** Tier 1 slash commands. They do functionally different jobs (per-artifact quality review vs. blast-radius review of recent commits/PRs); the project favors explicit naming over a merged "smart" review skill.

This story also adds **2 small CLI commands** (`standards gaps`, `create --from-standard`) that the `/specflow-discover` skill calls to make standards-aware discovery work deterministically.

## Target Slash Command Surface

| # | Slash command | Action | Composes CLI commands |
|---|-------|--------|-----------------------|
| 1 | `/specflow-init` | **New** | `init`, `hook install`, `ci generate`, installs skill facades |
| 2 | `/specflow-discover` | **Modify** — add standards-aware step | `standards gaps`, `create --from-standard`, (already ships) |
| 3 | `/specflow-plan` | Keep as-is | (already ships) |
| 4 | `/specflow-execute` | **Modify** — absorb `done` as final step | `go`, `update`, `create --type ut/it/qt`, `done` |
| 5 | `/specflow-artifact-review` | Keep as-is | `artifact-lint`, `checklist-run`, `artifact-review` |
| 6 | `/specflow-change-impact-review` | Keep as-is | `change-impact`, optional `document-changes` precondition |
| 7 | `/specflow-audit` | **Rewrite** from project-audit | `project-audit`, adversarial wings |
| 8 | `/specflow-ship` | **New** | `baseline create`, `document-changes`, `project-audit --quick` |
| 9 | `/specflow-pack-author` | Keep as-is | (already ships) |

## Deliverables

### Template unification

- Delete `src/specflow/templates/skills/gemini/` and `src/specflow/templates/skills/opencode/`
- Rename `src/specflow/templates/skills/claude/` to `src/specflow/templates/skills/shared/`
- Update `src/specflow/lib/platform.py`:
  - Keep `get_skills_platform_dir(platform: str) → str` with its current semantics — it returns the **target install subdirectory** name (`.claude` / `.opencode` / `.gemini`). Do not change call sites.
  - Add a new helper `get_skills_template_dir() → str` that returns the **source template subdirectory** name (`"shared"`), used by the scaffolder to locate the canonical SKILL.md files.
  - Update `get_skill_names()` (currently hardcoded to 4 names at `platform.py:35-37`) to return all **9** Tier 1 skill names: `specflow-init`, `specflow-discover`, `specflow-plan`, `specflow-execute`, `specflow-artifact-review`, `specflow-change-impact-review`, `specflow-audit`, `specflow-ship`, `specflow-pack-author`.
- The single canonical SKILL.md (currently the Claude version, the most complete) is the source of truth for all platforms
- Ensure `references/` subdirectories ship with the shared templates

### `/specflow-init` (new)
- Conversational bootstrap: asks about project type, preset, CI provider, standards packs
- Calls `specflow init` with appropriate flags
- Installs git hook via `specflow hook install`
- Optionally generates CI workflow via `specflow ci generate`
- Reports what was scaffolded and recommends `/specflow-discover`

### `/specflow-discover` (modify — add standards-aware discovery)

The existing discover flow is unchanged, with one new step inserted after the readiness check:

**New step: standards gap check.** After the initial readiness assessment, the skill silently runs `specflow standards gaps`. If uncovered standard clauses are found, the skill offers to scaffold REQs for them:

1. Present: "You have N uncovered standard clauses (e.g., ISO26262-3.7: Hazard analysis). Want me to scaffold REQs for them?"
2. User can accept all, pick specific clauses, or skip
3. For each accepted clause, the skill calls `specflow create --from-standard <clause-id>`, which creates a draft REQ pre-populated with the clause's title, description, and a `complies_with` link
4. The user then adapts the REQ text during the normal discover review flow — they own the REQ, the standard is just the immutable reference it traces to

This is a step insertion, not a rewrite. The existing lean/full discovery paths proceed normally after this step.

### New CLI commands (deterministic backend for the discover enhancement)

**`specflow standards gaps`** — Lists uncovered standard clauses (clauses in `.specflow/standards/` with no REQ linking to them via `complies_with`).

- Uses existing `standards.check_compliance()` (already returns covered/uncovered lists)
- Output: table of clause ID, title, description for each uncovered clause
- Exit 0 always — informational, not blocking
- Power users can run this directly; the discover skill calls it silently

**`specflow create --from-standard <clause-id>`** — Creates a draft REQ pre-populated from a standard clause.

- Reads the clause from installed standards by ID (e.g., `ISO26262-3.7`)
- Pre-populates: `title` from clause title, description body from clause description, `complies_with` link to the clause
- Status: `draft` — user adapts from there
- Works with existing `specflow create` infrastructure, just adds a `--from-standard` flag that overrides `--title` and `--type` (always `requirement`)
- Fails with clear error if clause ID not found in installed standards

### `/specflow-execute` (modify)
- Add final step: after all stories are implemented, offer phase closure
- Calls `specflow done` to extract prevention patterns and transition state
- User can skip this with "not yet" — closure is not forced

### `/specflow-artifact-review` (keep as-is)
- No structural change in this story. The existing skill stays in place.
- Continues to compose `artifact-lint` → `checklist-run` → `artifact-review` for one or more named artifacts.

### `/specflow-change-impact-review` (keep as-is)
- No structural change in this story. The existing skill stays in place.
- Continues to discover unreviewed DECs, run the `change-impact` pipeline, and present the Human-Review Summary before filing CHL artifacts.
- May call `document-changes` as a precondition if no unreviewed DECs are found.

### `/specflow-audit` (rewrite from project-audit)
- Full-project health review
- Zero-question core: runs `project-audit` deterministically (horizontal + vertical + cross-cutting)
- Optional adversarial wings (16 lenses via 2 parallel subagents)
- Creates AUD and CHL artifacts

### `/specflow-ship` (new — replaces the missing `/specflow-release`)
- Release workflow: `baseline create <tag>` → `document-changes --since <prev>` → `project-audit --quick`
- `document-changes` is invoked here (not in any review skill) so each release ships its own DEC trail before the audit runs
- Presents release summary with links to baseline, DECs, audit report
- Advisory if audit severity ≥ error — user must confirm to proceed

## Acceptance Criteria

1. All 9 skill directories exist in `.claude/skills/` with valid `SKILL.md` files: `specflow-init`, `specflow-discover`, `specflow-plan`, `specflow-execute`, `specflow-artifact-review`, `specflow-change-impact-review`, `specflow-audit`, `specflow-ship`, `specflow-pack-author`
2. Each `SKILL.md` follows `docs/skill-standards.md` conventions (under 500 lines, references in `references/`, scripts in `scripts/`)
3. `specflow init` installs all 9 skill directories into the platform-appropriate target dir (`.claude/skills/`, `.opencode/skills/`, or `.gemini/skills/`); verified by directory presence in a clean fixture
4. `/specflow-execute` offers phase closure via `specflow done` as a final step
5. `/specflow-ship` produces a baseline, DECs, and audit report in sequence
6. `/specflow-init` conversational flow covers: project type → preset → CI → standards → skill install
7. No skill references a deleted skill directory
8. Existing skills (discover, plan, artifact-review, change-impact-review, pack-author) are structurally untouched — discover gets a new standards-aware step but its existing flow is preserved; artifact-review and change-impact-review are unchanged
9. Every skill that offers the user a choice includes "(Recommended)" labels on the suggested default
10. `/specflow-discover` has a documented question cap of 15-20 questions; if more are needed, the skill suggests the user may want to refine requirements first (which likely means the discover→plan pipeline needs restructuring)
11. `/specflow-discover` includes an explicit escape hatch rule: "If the user signals they've provided enough context (e.g., 'that's enough', 'move on', 'skip'), immediately proceed to artifact generation with what you have"
12. `/specflow-pack-author` ends with a next-step recommendation (e.g., "Run `/specflow-init` to install this pack into a project")
13. `/specflow-execute` phase closure step includes a proper conversational flow (not a thin stub) — summarize accomplishments, extract prevention patterns, recommend archival
14. Only one canonical SKILL.md per skill exists in `templates/skills/shared/` — no platform-specific variants
15. `specflow standards gaps` lists uncovered clauses from installed standards without error
16. `specflow create --from-standard <clause-id>` creates a draft REQ with pre-populated title, description, and `complies_with` link
17. `/specflow-discover` runs `specflow standards gaps` silently after readiness check and offers to scaffold REQs from uncovered clauses
18. `specflow create --from-standard` fails with a clear error message when the clause ID is not found in installed standards
19. `src/specflow/lib/platform.py` exposes both `get_skills_platform_dir()` (target install dir, unchanged) and `get_skills_template_dir()` (returns `"shared"`); `get_skill_names()` returns all 9 skill names

## Out of Scope

- Deleting old skill directories (STORY-032)
- Updating documentation (STORY-034)
- Changing existing CLI command behavior (except adding the 2 new commands and `--from-standard` flag)
- Language-specific static analysis or linter integration

## Dependencies

- STORY-032 (over-exposed skill dirs must be deleted first to avoid confusion)
