---
id: STORY-716
title: 'Wave P-11: findings policy classes for pre-implementation rows; lint known/new
  rendering; rtm, verify, project-audit de-noise'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-053
  role: implements
- target: REQ-060
  role: implements
created: '2026-10-08'
fingerprint: sha256:94fc020cd31c
modified: '2026-10-08'
output_files:
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/project_audit.py
- src/specflow/commands/rtm.py
- src/specflow/commands/verify.py
- src/specflow/core/findings.py
- src/specflow/core/policy.py
- src/specflow/lib/artifacts.py
- tests/test_artifact_lint_rendering.py
- tests/test_artifacts.py
- tests/test_coverage_semantics.py
- tests/test_policy_classes.py
- tests/test_project_audit.py
- tests/test_rtm.py
- tests/test_verify.py
---

# Wave P-11: findings policy classes for pre-implementation rows; lint known/new rendering; rtm, verify, project-audit de-noise

# Wave P-11

Findings F-006 (policy table + amending DEC), F-005 rendering, F-034, F-073, F-033, F-026 early-return, F-085 dead local.
## Acceptance Criteria

- [ ] AC1: Given a fresh init at discovering with draft STORYs and no tests, when artifact-lint runs with the empty baseline, then the result is PASS.
- [ ] AC2: Given a STORY moved to implemented without tests, when artifact-lint runs, then coverage/no-test escalates.
- [ ] AC3: Given a baseline with known findings, when artifact-lint runs, then each check prints N known and M new and lists only new lines unless --verbose.
- [ ] AC4: Given rtm --gaps, when run, then terminal-status REQs are hidden with a footer count.
