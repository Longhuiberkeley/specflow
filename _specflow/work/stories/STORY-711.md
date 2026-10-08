---
id: STORY-711
title: 'Wave P-5: one practice-binding predicate for brief and lint; thinking_techniques
  catalog sweep'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-045
  role: implements
- target: REQ-060
  role: implements
created: '2026-10-08'
fingerprint: sha256:e9de361b4930
modified: '2026-10-08'
output_files:
- .claude/skills/specflow-references/references/adversarial-lenses.md
- src/specflow/commands/artifact_lint.py
- src/specflow/lib/artifacts.py
- src/specflow/lib/practices.py
- src/specflow/templates/skills/shared/specflow-references/references/adversarial-lenses.md
- tests/test_bp_application.py
- tests/test_practice_binding_parity.py
- tests/test_thinking_techniques_normalization.py
---

# Wave P-5: one practice-binding predicate for brief and lint; thinking_techniques catalog sweep

# Wave P-5

Findings F-040, F-146 (approval), F-135 steps 1, 3, 4.
## Acceptance Criteria

- [ ] AC1: Given this repo, when brief and artifact-lint --type bp-application run, then both report the same unbound count.
- [ ] AC2: Given an artifact with bracket-split or hyphenated lens names, when the sweep runs via update --set, then every value is a catalog name and lint reports zero non-catalog values.
- [ ] AC3: Given update --thinking-techniques with an unknown name, when it runs, then the documented behaviour (warn and save) matches adversarial-lenses.md.
