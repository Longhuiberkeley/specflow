---
id: STORY-669
title: guided_by link role for REQ, ARCH, and STORY (REQ-045)
type: story
status: implemented
suspect: false
links:
- target: REQ-045
  role: implements
- target: ARCH-036
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:2a725a5f700b
thinking_techniques:
- premortem
- dependency-shock
- worst_case_user
- composition
modified: '2026-09-25'
---

# guided_by link role for REQ, ARCH, and STORY (REQ-045)

## Story
Add guided_by to requirement.yaml allowed_link_roles and add requirement/guided_by, architecture/guided_by, story/guided_by rows to role_targets.py so practice guidance binds every lifecycle artifact type; render the edges in trace and decide plus document the chain-depth treatment (depth-neutral or one hop) with a unit test.

## Acceptance Criteria
1. Given REQ, ARCH, and STORY fixtures, when linked guided_by to a BP, then schema validation passes, role_targets resolves, and trace renders the edge.
2. Given the chain-depth decision recorded in the STORY notes, when trace depth is computed, then behavior matches the decision and the unit test pins it.
3. Given a link to a nonexistent BP, when lint runs, then the dangling edge is flagged by the existing links check.

## Implementation Notes
Chain-depth decision: guided_by remains a rendered guidance edge but is depth-neutral. It records context rather than an implementation or verification hop, so it does not increase V-model chain depth. The behavior is pinned in test_guided_by_does_not_inflate_chain_depth.
