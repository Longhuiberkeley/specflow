---
id: STORY-642
title: 'v1.15.0: unify chain-depth with the typed edge matrix'
type: story
status: draft
tags:
- v1.15.0-backlog
suspect: false
links:
- target: REQ-003
  role: implements
created: '2026-08-27'
fingerprint: sha256:f273b7f17a02
---

# v1.15.0: unify chain-depth with the typed edge matrix

Deferred from v1.14.3 (riskier refactor). `compute_chain_depth` uses `_CHAIN_DEPTH_ROLES` + reverse links (artifacts.py:913-954) while trace traversal and audit/RTM use separate semantic paths — numbers can disagree. Unify on one shared type-aware edge engine. v1.14.3's role-target matrix (STORY-639) is the declared cousin.
