---
id: STORY-710
title: "Wave P-4: standards and ReqIF correctness \u2014 double-escape, malformed\
  \ YAML, dead-end hints, silent exits"
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-011
  role: implements
- target: REQ-016
  role: implements
created: '2026-10-08'
fingerprint: sha256:b356b7cfa730
modified: '2026-10-08'
output_files:
- .claude/skills/specflow-discover/SKILL.md
- src/specflow/commands/rebuild_index.py
- src/specflow/commands/standards_gaps.py
- src/specflow/lib/reqif.py
- src/specflow/lib/standards.py
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- tests/test_rebuild_index_type.py
- tests/test_reqif_roundtrip.py
- tests/test_standards.py
---

# Wave P-4: standards and ReqIF correctness — double-escape, malformed YAML, dead-end hints, silent exits

# Wave P-4

Findings F-069, F-070, F-110, F-113, F-116.
## Acceptance Criteria

- [ ] AC1: Given an artifact whose title contains <, & and ", when export then import then export, then the second export is byte-identical to the first.
- [ ] AC2: Given a malformed standards YAML, when standards gaps runs, then the error names the file and parse problem, not 'not found'.
- [ ] AC3: Given no standards installed, when standards gaps runs, then it exits 0 with a neutral message and discover does not print a misleading init --preset hint.
- [ ] AC4: Given bare specflow standards or rebuild-index --type unknown, when run, then a usage or unknown-type message is printed and the exit code is non-zero.
