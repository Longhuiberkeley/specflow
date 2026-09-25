---
id: STORY-642
title: 'v1.15.0: unify chain-depth with the typed edge matrix'
type: story
status: deprecated
tags:
- v1.15.0-backlog
suspect: false
links:
- target: REQ-003
  role: implements
created: '2026-08-27'
fingerprint: sha256:e229e745199b
modified: '2026-09-26'
deprecation_reason: 'v1.15.0-era scope parked at v1.16.0 release per owner decision
  2026-09-26: superseded by later work or explicitly deferred (see title); re-derive
  via a new REQ if the need returns'
---

# v1.15.0: unify chain-depth with the typed edge matrix

Deferred from v1.14.3 (riskier refactor). `compute_chain_depth` uses `_CHAIN_DEPTH_ROLES` + reverse links (artifacts.py:913-954) while trace traversal and audit/RTM use separate semantic paths — numbers can disagree. Unify on one shared type-aware edge engine. v1.14.3's role-target matrix (STORY-639) is the declared cousin.

## Acceptance Criteria

1. `compute_chain_depth`, trace traversal, and audit/RTM report the same chain depth for the same artifact pair via one shared type-aware edge engine.
2. A regression test pins agreement across the three call sites on a fixture project.
