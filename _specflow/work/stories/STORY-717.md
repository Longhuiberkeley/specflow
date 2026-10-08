---
id: STORY-717
title: "Wave P-12: core skill text parity \u2014 link direction, vocabulary tables,\
  \ statuses, discover/start/ship flows, delegation guidance"
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-061
  role: implements
created: '2026-10-08'
fingerprint: sha256:f3d29816052f
modified: '2026-10-08'
output_files:
- .claude/skills/specflow-discover/SKILL.md
- .claude/skills/specflow-execute/SKILL.md
- .claude/skills/specflow-execute/references/status-lifecycle.md
- .claude/skills/specflow-plan/references/link-roles.md
- .claude/skills/specflow-ship/SKILL.md
- .claude/skills/specflow-start/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/references/status-lifecycle.md
- src/specflow/templates/skills/shared/specflow-plan/references/link-roles.md
- src/specflow/templates/skills/shared/specflow-ship/SKILL.md
- src/specflow/templates/skills/shared/specflow-start/SKILL.md
- tests/test_core_skill_text.py
- tests/test_link_roles_doc.py
---

# Wave P-12: core skill text parity — link direction, vocabulary tables, statuses, discover/start/ship flows, delegation guidance

# Wave P-12

Findings F-009, F-039, F-046, F-010, F-042, F-047, F-043, F-071, F-041, F-091, F-030, F-063 (delegation), F-062 (ship), F-066 (ship line), F-070 (discover line), F-011 (ship/audit lines).
## Acceptance Criteria

- [ ] AC1: Given the plan skill, when read, then it links ARCH to REQ via update <REQ> --add-link <ARCH>:refined_by.
- [ ] AC2: Given every shipped schema role, when checked against link-roles.md, then each appears, pinned by a test.
- [ ] AC3: Given the live and template skill trees, when diffed, then they are byte-identical.
- [ ] AC4: Given a DEF in open, when update --status fixing, then it succeeds.
