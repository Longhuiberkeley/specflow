---
id: STORY-667
title: Practices seed split and handbook deprecation (REQ-044)
type: story
status: implemented
suspect: false
links:
- target: REQ-044
  role: implements
- target: ARCH-035
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:6a90ee08ec8c
thinking_techniques:
- premortem
- dependency_shock
- worst_case_user
- composition
modified: '2026-10-08'
---

# Practices seed split and handbook deprecation (REQ-044)

## Story
Split the bundled practices out of lib/handbook.py into lib/practices_seed.py with stable SEED-<domain>-NN ids and applicability predicates; keep handbook generate as a deprecated alias that delegates to the same data. No behavior change for existing generated BPs beyond id stability.

## Acceptance Criteria
1. Given lib/practices_seed.py, when practices seed lists entries, then ids are stable across runs and each entry carries an applicability predicate.
2. Given specflow handbook generate --create, when run, then it still produces equivalent BP bodies via the alias and prints a deprecation note.
3. Given the six dogfood BPs, when compared to regenerated output, then content is equivalent (ids may differ).
