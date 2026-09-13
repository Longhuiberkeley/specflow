---
id: STORY-651
title: Closure-readiness accounting in autoresearch status
type: story
status: implemented
rationale: "specflow autoresearch status exits before printing when no running/draft\
  \ LOOP exists \u2014 unusable exactly at closure time. Restructure _run_status to\
  \ render a COMP-level closure-readiness block (confirmed FIND count, open research_agenda\
  \ directions, goals echo) independent of LOOP resolution; update cli-reference doc."
suspect: false
links:
- target: REQ-039
  role: implements
created: '2026-09-11'
fingerprint: sha256:b9a8cc5b419b
modified: '2026-09-13'
---

# Closure-readiness accounting in autoresearch status

## Acceptance Criteria

1. `specflow autoresearch status` reports closure-readiness signals (goals met, confirmed FINDs, open agenda directions) deterministically.
2. A repo with no active LOOP reports closure-readiness + Phase 0 checks only, exiting 0 when clean (tests/test_autoresearch_cli.py).
