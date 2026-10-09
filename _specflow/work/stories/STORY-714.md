---
id: STORY-714
title: 'Wave P-9: stdin EOF guard, reserved --set keys, title index sync, no-op fingerprint
  refresh, impact-log noise, dedup gate'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-059
  role: implements
- target: REQ-003
  role: implements
created: '2026-10-08'
fingerprint: sha256:75891357e37f
modified: '2026-10-09'
output_files:
- src/specflow/commands/autoresearch.py
- src/specflow/commands/change_impact.py
- src/specflow/commands/create.py
- src/specflow/commands/fingerprint_refresh.py
- src/specflow/commands/update.py
- src/specflow/lib/artifacts.py
- src/specflow/lib/impact.py
- src/specflow/lib/stdin_probe.py
- src/specflow/packs/ops/skills/specflow-ops/SKILL.md
- tests/test_p9_writers_stdin_impact.py
- tests/test_display_colors.py
---

# Wave P-9: stdin EOF guard, reserved --set keys, title index sync, no-op fingerprint refresh, impact-log noise, dedup gate

# Wave P-9

Findings F-001, F-017, F-018, F-015, F-014, F-021, F-020, F-097.
## Acceptance Criteria

- [ ] AC1: Given update invoked with stdin at EOF, when it runs, then no stdin warning is printed and a real piped body still works.
- [ ] AC2: Given update --set id=X, when it runs, then it is refused with a pointer to renumber-drafts/split/merge.
- [ ] AC3: Given update --title, when it runs, then _index.yaml carries the new title.
- [ ] AC4: Given fingerprint-refresh on an unchanged artifact, when it runs, then no event is written and version is unchanged.
- [ ] AC5: Given create in non-interactive mode with a medium-similarity candidate, when it runs, then candidates are printed and the artifact is created with exit 0.
