---
id: STORY-655
title: 'Ops RUN reversible pause: schema, doctrine line, tests'
type: story
status: implemented
rationale: "Make RUN pause reversible: run.yaml live: [deployed, paused] (no initial_statuses\
  \ needed \u2014 deployed is sole root); update the ops SKILL.md RUN status line\
  \ to show live \u21C4 paused with resume explicitly user-gated; update/add pins\
  \ in tests/test_ops_pack.py plus a map lock; bump ops pack version 0.1.0 \u2192\
  \ 0.2.0."
suspect: false
links:
- target: REQ-041
  role: implements
- target: DEC-081
  role: guided_by
created: '2026-09-11'
fingerprint: sha256:386c45e8cf2f
modified: '2026-09-13'
---

# Ops RUN reversible pause: schema, doctrine line, tests

## Acceptance Criteria

1. paused → live is legal in run.yaml (`live: [deployed, paused]`); deployed stays the sole creation root; retired stays terminal.
2. The ops skill's RUN status line documents resumability without weakening the frozen-at-deploy doctrine.
3. tests/test_ops_pack.py pins the schema map.
