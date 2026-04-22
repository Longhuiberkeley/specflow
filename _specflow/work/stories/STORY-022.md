---
id: STORY-022
title: Ship command rename and thin-skill wrappers for all Tier 2/3 CLI commands
type: story
status: verified
priority: high
tags:
- rename
- CLI
- skills
- M1-clarity
suspect: false
links:
- target: REQ-018
  role: implements
- target: ARCH-010
  role: guided_by
- target: DDD-007
  role: specified_by
- target: QT-019
  role: verified_by
- target: IT-012
  role: verified_by
- target: UT-013
  role: verified_by
created: '2026-04-14'
checklists_applied:
- checklist: check-STORY-022
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:ea3bae1e6e1b
version: 1
---

# Ship command rename and thin-skill wrappers for all Tier 2/3 CLI commands

## Description

Execute the full command rename from retrospective §3 (Appendix A). This is a single coordinated pass touching CLI registration (cli.py), command module filenames, lib module filenames (validation.py → lint.py), shell wrappers in scripts/, skill directory names, and all internal cross-references. After the rename, add thin-skill wrappers for Tier 2 and Tier 3 CLI commands under the `/cmd [optional message]` pattern (~10-20 lines each).

### Renames required

- `specflow validate` → `specflow artifact-lint`
- `specflow check` → `specflow checklist-run`
- `specflow verify` → `specflow artifact-review`
- `specflow audit` → `specflow project-audit`
- `specflow compliance` → removed (folded into project-audit)
- `specflow impact` → `specflow change-impact`
- `specflow tweak` → `specflow fingerprint-refresh`
- `specflow sequence` → `specflow renumber-drafts`

### File renames

- `lib/validation.py` → `lib/lint.py`
- `commands/validate.py` → `commands/artifact_lint.py`
- `commands/verify.py` → `commands/artifact_review.py`
- `commands/check.py` → `commands/checklist_run.py`
- `commands/impact.py` → `commands/change_impact.py`
- `commands/tweak.py` → `commands/fingerprint_refresh.py`
- `commands/sequence.py` → `commands/renumber_drafts.py`
- `.claude/skills/specflow-verify/` → `.claude/skills/specflow-artifact-review/`

### Shell script renames

- `scripts/validate.sh` → `scripts/artifact-lint.sh`
- `scripts/check.sh` → `scripts/checklist-run.sh`
- `scripts/impact.sh` → `scripts/change-impact.sh`
- `scripts/tweak.sh` → `scripts/fingerprint-refresh.sh`
- `scripts/sequence.sh` → `scripts/renumber-drafts.sh`
- `scripts/compliance.sh` → deleted
- `scripts/validate-*.sh` → update references to new command names

### Thin-skill wrappers

Create minimal skill directories under `.claude/skills/` for Tier 2/3 commands that don't have dedicated skills: `specflow-baseline`, `specflow-status`, `specflow-create`, `specflow-update`, `specflow-go`, `specflow-done`, `specflow-fingerprint-refresh`, `specflow-renumber-drafts`, `specflow-import`, `specflow-export`, `specflow-hook`, `specflow-artifact-lint`, `specflow-checklist-run`, `specflow-detect`. Each is ~10-20 lines following the `/cmd [optional message]` pattern.

## Acceptance Criteria

1. All old command names still work as hidden aliases (print deprecation warning to stderr) for one release cycle

2. `specflow --help` lists all commands using new names only, grouped by workflow phase (Discover / Plan / Execute / Review / Release / CI) using argparse subparser groups

3. Every import of renamed modules is updated across the entire codebase — `grep -r "from specflow.commands.validate"` returns zero hits

4. All shell scripts in scripts/ call the new command names via `exec uv run specflow <new-name>`

5. The specflow-verify skill directory is renamed to specflow-artifact-review and its SKILL.md references are updated

6. `commands/compliance.py` and `scripts/compliance.sh` are deleted (functionality folded into project-audit)

7. Thin-skill wrappers exist for all Tier 2/3 commands and follow the skill-standards.md guidelines

8. Existing tests (if any) pass with the new command names

9. `compute_fingerprint()` in `lib/artifacts.py` truncates SHA256 output to 12 hex chars (48 bits), reducing stored fingerprint from 71 to 19 characters (e.g., `sha256:6ae8a7555520`). A `specflow fingerprint-refresh --all` pass refreshes existing fingerprints in `_index.yaml` and artifact frontmatter during the rename.

## Out of Scope

- Writing docs/getting-started.md (STORY-023)
- Artifact-review depth/lenses feature (STORY-024)
- Adapter framework (STORY-026)

## Dependencies

- None (but coordinate with STORY-021 so the SKILL.md rewrites reference new names)
