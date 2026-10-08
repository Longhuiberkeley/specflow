---
id: STORY-718
title: "Wave P-13: tests and CI hygiene \u2014 executor tests, un-skip practice tests,\
  \ handler tests, release consistency, wheel smoke PATH, brownfield fixture"
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-009
  role: implements
- target: REQ-057
  role: implements
created: '2026-10-08'
fingerprint: sha256:3ed2bc027de6
modified: '2026-10-08'
output_files:
- pyproject.toml
- scripts/wheel_smoke.py
- tests/conftest.py
- tests/test_autoresearch_cli.py
- tests/test_autoresearch_pack.py
- tests/test_brownfield_upgrade.py
- tests/test_checklist_dedup.py
- tests/test_detect_hygiene.py
- tests/test_findings_model.py
- tests/test_format_version.py
- tests/test_go_executor.py
- tests/test_handbook.py
- tests/test_pack_healthy_fixtures.py
- tests/test_patterns_cmd.py
- tests/test_phase_status_cmd.py
- tests/test_practices.py
- tests/test_release_consistency.py
---

# Wave P-13: tests and CI hygiene — executor tests, un-skip practice tests, handler tests, release consistency, wheel smoke PATH, brownfield fixture

# Wave P-13

Findings F-056, F-098, F-013, F-055, F-057, F-058 (test), F-059, F-012.
## Acceptance Criteria

- [ ] AC1: Given tests/test_practices.py and test_handbook.py, when run with -rs, then zero skips.
- [ ] AC2: Given auto_commit_wave in a temp git repo, when run, then it commits staged files and returns False when nothing is staged.
- [ ] AC3: Given pyproject, __init__ and CHANGELOG head, when compared by a test, then they agree.
- [ ] AC4: Given a git archive of the previous tag, when read-only commands run against it, then no Traceback and only documented exit codes.
