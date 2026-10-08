---
id: STORY-709
title: "Wave P-3: refresh/init/scaffold hygiene \u2014 pack standards sync, backups,\
  \ sentinel safety, optional schemas, codex/junie, legacy dirs"
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-022
  role: implements
- target: REQ-057
  role: implements
created: '2026-10-08'
fingerprint: sha256:e9de626b87bc
modified: '2026-10-08'
output_files:
- src/specflow/commands/init.py
- src/specflow/commands/refresh.py
- src/specflow/lib/config.py
- src/specflow/lib/platform.py
- src/specflow/lib/scaffold.py
- src/specflow/templates/platforms.yaml
- tests/test_init_local_packs.py
- tests/test_platform_install_safety.py
- tests/test_refresh_lints.py
- tests/test_scaffold_refresh_hygiene.py
- tests/test_v12_features.py
---

# Wave P-3: refresh/init/scaffold hygiene — pack standards sync, backups, sentinel safety, optional schemas, codex/junie, legacy dirs

# Wave P-3

Findings F-103, F-109, F-114, F-123, F-125, F-127, F-130, F-117 (baseline backup), F-072, F-083.
## Acceptance Criteria

- [ ] AC1: Given a pack whose standards/ file changed, when refresh --packs --force runs, then the standards file is synced and the overwritten copy is backed up.
- [ ] AC2: Given init --force on a project with a findings baseline, when it completes, then the baseline is backed up and kept.
- [ ] AC3: Given an AGENTS.md with an END sentinel before START, when refresh runs, then the file is repaired idempotently and never grows.
- [ ] AC4: Given codex and junie both selected, when refresh runs, then the shared .agents/skills tree is installed once with no false warning.
- [ ] AC5: Given one drifted skill, when refresh runs, then the summary says 1 installed, not the total.
