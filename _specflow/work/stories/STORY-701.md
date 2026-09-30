---
id: STORY-701
title: Retire the Gemini CLI host and gemini-toml export
type: story
status: verified
tags:
- v1.17.1
- platforms
suspect: false
links:
- target: REQ-005
  role: implements
- target: DEC-094
  role: guided_by
created: '2026-09-30'
fingerprint: sha256:6a21151d2774
modified: '2026-09-30'
output_files:
- src/specflow/templates/platforms.yaml
- src/specflow/lib/skill_export.py
- src/specflow/cli.py
- src/specflow/templates/skills/shared/specflow-init/SKILL.md
- tests/test_skill_export.py
- tests/test_dual_host_skills.py
---

# Retire the Gemini CLI host and gemini-toml export

## Acceptance Criteria

1. platforms.yaml no longer registers gemini and skill export no longer offers gemini-toml.
2. init --platform gemini and refresh --platform gemini exit 1 with the list of available platforms; a project with only .gemini/ gets the no-platform path without a traceback.
3. Shipped skills, docs and ROADMAP no longer present Gemini as a supported host; tests that asserted Gemini behaviour are removed or inverted.
