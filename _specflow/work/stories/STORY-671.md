---
id: STORY-671
title: Brief bound/unbound practice accounting (REQ-045)
type: story
status: implemented
suspect: false
links:
- target: REQ-045
  role: implements
- target: ARCH-036
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:6546fbec875a
thinking_techniques:
- premortem
- dependency-shock
- worst_case_user
- composition
modified: '2026-09-25'
---

# Brief bound/unbound practice accounting (REQ-045)

## Story
Extend specflow brief with bound versus unbound counts for REQ, ARCH, and STORY against in-scope approved BPs, replacing the bare dormancy hint.

## Acceptance Criteria
1. Given artifacts with and without guided_by edges to in-scope BPs, when brief runs, then both counts appear per type.
2. Given no in-scope BPs, when brief runs, then the section is omitted rather than printing zeros.
3. Given artifact-lint, when run after brief changes, then the payload-budget guardrail tests still pass (brief stays within budget).
