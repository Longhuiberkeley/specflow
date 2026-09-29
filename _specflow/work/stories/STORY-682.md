---
id: STORY-682
title: 'Checklist runner: script-less automated items error, severity honoured, parse
  failures warn'
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
- checklists
suspect: false
links:
- target: REQ-056
  role: implements
- target: REQ-053
  role: implements
created: '2026-09-30'
fingerprint: sha256:ccc1bb2647c5
modified: '2026-09-30'
output_files:
- src/specflow/lib/checklists.py
- src/specflow/commands/checklist_run.py
- tests/test_checklists.py
- tests/test_checklist_run_integration.py
---

# Checklist runner: script-less automated items error, severity honoured, parse failures warn

## Acceptance Criteria
1. An automated item with no script yields an error result instead of a silent pass.
2. checklist-run treats a failed warning-severity item as a warning, not a blocker.
3. The persisted blocking_failures count matches the items that actually blocked.
4. A checklist file that fails YAML parsing prints the path and reason to stderr and is reported in the run summary.
