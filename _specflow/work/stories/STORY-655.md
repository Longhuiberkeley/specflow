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
fingerprint: sha256:1ab9654b45c6
modified: '2026-09-11'
---

# Ops RUN reversible pause: schema, doctrine line, tests
