---
id: STORY-673
title: EDA lenses, applicability-aware accounting, agenda re-rank (REQ-046)
type: story
status: implemented
suspect: false
links:
- target: REQ-046
  role: implements
- target: ARCH-037
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:ed7fce11f719
thinking_techniques:
- premortem
- dependency-shock
modified: '2026-09-25'
---

# EDA lenses, applicability-aware accounting, agenda re-rank (REQ-046)

## Story
Replace the dangling EDA checks #1/#4 references with references/eda-lenses.md (leakage, distribution shift diagnosed within the COMP eval data resolving the ML-11 conflict, class imbalance, target noise; vol/regime buckets for quant), make status EDA accounting applicability-aware (not-applicable when the domain has no lenses), and add the post-EDA agenda-revision advisory.

## Acceptance Criteria
1. Given SKILL.md and the loop protocol, when grepped for EDA checks #1/#4, then no dangling reference remains and the lenses file is cited.
2. Given a domain without lenses, when status runs, then EDA reports not-applicable instead of the unconditional advisory.
3. Given eda_completed on a lensed domain, when status runs, then the agenda-revision advisory appears with the exact update command.
4. Given ML-11, when read after the change, then it no longer instructs reading the isolated eval partition.
