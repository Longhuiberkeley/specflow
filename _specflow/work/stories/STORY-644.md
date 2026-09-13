---
id: STORY-644
title: 'v1.15.0: ops pack methodology handbook'
type: story
status: draft
tags:
- v1.15.0-backlog
suspect: false
links:
- target: REQ-001
  role: implements
created: '2026-08-27'
fingerprint: sha256:d473e694a46a
modified: '2026-09-13'
---

# v1.15.0: ops pack methodology handbook

Autoresearch has a methodology handbook (BP-01..ML-22 wired into loop protocol); ops has only schemas + skill (packs/ops/pack.yaml:8-22). Create the ops equivalent: deploy/observe/rollback/runbook BPs with domain-keyed applicability, consulted live by the ops skill.

## Acceptance Criteria

1. The ops pack ships a methodology handbook with deploy/observe/rollback/runbook BPs keyed by domain.
2. The ops skill consults the handbook live, the way the autoresearch skill consults its methodology handbook.
