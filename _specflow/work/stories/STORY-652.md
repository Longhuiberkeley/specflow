---
id: STORY-652
title: 'Reversible pause: initial_statuses schema key, paused-to-active'
type: story
status: implemented
rationale: "paused\u2192active is impossible today (one-way door; root-status logic\
  \ treats empty-predecessor statuses as creation roots). Add an initial_statuses\
  \ schema key honored by implicit-status resolution and the creation sanction gate;\
  \ set competition.yaml to active:[paused] + initial_statuses:[active]; update schema\
  \ display, pack-author docs (+ byte-identical .claude mirror), and tests including\
  \ the mandatory pin in test_autoresearch_pack.py."
suspect: false
links:
- target: REQ-039
  role: implements
- target: DEC-079
  role: guided_by
created: '2026-09-11'
fingerprint: sha256:f292d79bff01
modified: '2026-09-13'
---

# Reversible pause: initial_statuses schema key, paused-to-active

## Acceptance Criteria

1. The autoresearch competition schema accepts an `initial_statuses` key naming the creation roots.
2. paused → active is a legal COMP transition — paused is no longer a one-way door — while completed → active stays rejected.
3. tests/test_v1145_locks.py and tests/test_artifacts.py pin the map and both directions.
