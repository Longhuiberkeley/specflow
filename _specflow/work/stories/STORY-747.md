---
id: STORY-747
title: 'W-2 docs: correct all SPIKE-008 docs-code sites (architecture, authoring guides,
  decisions, commands, comparison, getting-started, cli-reference, team-setup, lifecycle,
  README, ROADMAP)'
type: story
status: verified
tags:
- consistency
- v1.17.7
suspect: false
links:
- target: REQ-070
  role: implements
- target: SPIKE-008
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:25a8c51f8e97
modified: '2026-10-18'
output_files:
- .claude/skills/specflow-init/SKILL.md
- README.md
- ROADMAP.md
- docs/architecture.md
- docs/authoring-a-pack.md
- docs/authoring-an-adapter.md
- docs/cli-reference.md
- docs/commands.md
- docs/comparison.md
- docs/decisions.md
- docs/getting-started.md
- docs/lifecycle.md
- docs/team-setup.md
- src/specflow/templates/skills/shared/specflow-init/SKILL.md
- tests/test_init_hook_path_prose.py
- tests/test_link_roles_doc.py
---

# W-2 docs: correct all SPIKE-008 docs-code sites (architecture, authoring guides, decisions, commands, comparison, getting-started, cli-reference, team-setup, lifecycle, README, ROADMAP)

## Scope
All rows of SPIKE-008 with fix kind docs (61 sites). architecture.md:353 rewritten once; team-setup.md adopts the D6 wording (require both display-named checks, CI gate row, CODEOWNERS any-of, author not committer); README badge 3.11+; ROADMAP:94 pointer.

## Acceptance criteria
- AC1: Given each SPIKE-008 docs row with severity blocking or warning, when its site is re-read, then the quoted claim is gone or matches the engine.
- AC2: Given `docs/team-setup.md` and the adapter reference, when read, then both say to require 'Pass 1 — programmatic validation' and 'CI gate (RBAC)', that ci-gate must be in `ci.operations`, and that a multi-owner CODEOWNERS line is any-of.
- AC3: Given `uv run pytest tests/test_doc_command_examples.py tests/test_cli_reference_coverage.py tests/test_readme_pin.py`, when run, then all pass.
- AC4: Given README.md line 4, when read, then the Python badge says 3.11+.
