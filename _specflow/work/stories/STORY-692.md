---
id: STORY-692
title: 'Ops pack: breached nag clears, MONITOR template lints clean, pause and retire
  guidance'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- ops
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:0a41e40bcc30
modified: '2026-09-30'
output_files:
- src/specflow/packs/ops/README.md
- src/specflow/packs/ops/schemas/run.yaml
- src/specflow/packs/ops/skills/specflow-ops/SKILL.md
- src/specflow/commands/brief.py
- tests/test_ops_pack.py
---

# Ops pack: breached nag clears, MONITOR template lints clean, pause and retire guidance

## Acceptance Criteria
1. brief counts a MONITOR as breached only while its status is flagged or its health is breached and it is not resolved or credited; the outcome-feedback note uses the same rule.
2. The Flow B MONITOR create sets the required summary field and lints clean.
3. The skill documents pause, retire (retired_at) and deployed-awaiting-live, and RUN allows retired from deployed; derives_from is reserved for corrections.
4. A golden-path test drives RUN, MONITOR, breach and resolve through the CLI and asserts brief --next is silent afterwards; the pack gains a short README.
