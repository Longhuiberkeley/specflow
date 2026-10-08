---
id: STORY-715
title: "Wave P-10: brief and status honesty \u2014 routing, DEF/DEC/unexecuted notes,\
  \ stale skills, buckets, adopt wording, coverage line"
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-060
  role: implements
created: '2026-10-08'
fingerprint: sha256:35d5773b833e
modified: '2026-10-08'
output_files:
- src/specflow/commands/adopt.py
- src/specflow/commands/brief.py
- src/specflow/commands/status.py
- tests/test_adoption_mechanics.py
- tests/test_brief.py
- tests/test_brief_routing.py
- tests/test_status_coverage.py
---

# Wave P-10: brief and status honesty — routing, DEF/DEC/unexecuted notes, stale skills, buckets, adopt wording, coverage line

# Wave P-10

Findings F-002, F-007, F-038, F-031, F-035, F-066 (brief line), F-068, F-074 (nag), F-022, F-080, F-101, F-040 call-site.
## Acceptance Criteria

- [ ] AC1: Given all non-terminal STORYs implemented or verified, when brief --next runs, then it routes to review/ship, never execute.
- [ ] AC2: Given open DEFs and draft DECs exist, when brief --next runs, then a note lists them with the exact approval command.
- [ ] AC3: Given a quiet, healthy project, when brief runs, then no new note lines appear.
- [ ] AC4: Given installed skills differ from templates, when brief runs, then one Health line names them and points at specflow refresh.
