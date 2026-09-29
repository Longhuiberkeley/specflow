---
id: STORY-681
title: init and refresh resolve project-local packs before bundled packs
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
- packs
suspect: false
links:
- target: REQ-055
  role: implements
created: '2026-09-30'
fingerprint: sha256:d3de08686577
modified: '2026-09-30'
output_files:
- src/specflow/lib/scaffold.py
- src/specflow/commands/init.py
- src/specflow/commands/refresh.py
- tests/test_init_local_packs.py
- src/specflow/templates/skills/shared/specflow-pack-author/SKILL.md
checklists_applied:
- checklist: check-STORY-681
  timestamp: '2026-09-29T19:11:52Z'
---

# init and refresh resolve project-local packs before bundled packs

## Acceptance Criteria

1. specflow init --preset <name> finds .specflow/packs/<name>/ before the bundled directory.
2. On an already-initialised project, specflow init --preset <name> (merge mode) installs and registers a local pack, and specflow refresh --packs syncs later edits to an active local pack. refresh --packs does not install packs that are not active (opt-in stays explicit).
3. The pack-author skill exit message and install section name only the working commands (no hand-copy into .specflow/).
4. A test installs a temporary local pack through both paths, including the pack-first flow where .specflow/ holds only packs/ (the project ends up with state.yaml).
