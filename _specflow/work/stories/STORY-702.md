---
id: STORY-702
title: Drop the stale config version key; refresh bumps the CI workflow pin
type: story
status: verified
tags:
- v1.17.1
- config
- ci
suspect: false
links:
- target: REQ-057
  role: implements
created: '2026-09-30'
fingerprint: sha256:ba9d5a07011f
modified: '2026-09-30'
output_files:
- src/specflow/lib/config.py
- src/specflow/commands/init.py
- src/specflow/commands/refresh.py
- src/specflow/lib/adapters/github_actions.py
- tests/test_format_version.py
- tests/test_ci_pin_refresh.py
---

# Drop the stale config version key; refresh bumps the CI workflow pin

## Acceptance Criteria

1. init no longer writes version into .specflow/config.yaml, merge_config removes a legacy version key, refresh strips a legacy top-level version line (dry-run reports it), and the dead version-delta path is removed without breaking init output.
2. When .github/workflows/specflow.yml pins git+https://github.com/Longhuiberkeley/specflow@vX.Y.Z older than the running version, refresh rewrites every such pin to the running version and reports old to new with a count; it never downgrades, leaves branch and SHA pins untouched and reports them, and dry-run writes nothing.
