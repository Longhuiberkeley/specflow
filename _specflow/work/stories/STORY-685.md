---
id: STORY-685
title: Platform install never deletes the instruction file or pack blocks
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- install
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:6af69f20c44a
modified: '2026-09-30'
output_files:
- src/specflow/templates/platforms.yaml
- src/specflow/lib/platform.py
- src/specflow/commands/init.py
- src/specflow/commands/refresh.py
- src/specflow/lib/scaffold.py
- tests/test_platform_install_safety.py
---

# Platform install never deletes the instruction file or pack blocks

## Acceptance Criteria
1. kiro and trae legacy_dirs no longer name the parent of their instruction_file.
2. Legacy cleanup refuses to remove any ancestor of the instruction file and removes only specflow-owned entries.
3. init installs skills before injecting context, matching refresh.
4. A parametrized test over every platforms.yaml entry runs init with a preset then refresh and asserts both sentinel blocks and a user-authored sibling file survive.
