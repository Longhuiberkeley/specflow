---
id: STORY-719
title: 'Ledger housekeeping: renumber draft-slug IDs, approve draft tests with evidence,
  close superseded AUDs, retire dead checklist dirs'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-021
  role: implements
- target: REQ-060
  role: implements
created: '2026-10-08'
fingerprint: sha256:799cacbdb00c
modified: '2026-10-08'
---

# Ledger housekeeping: renumber draft-slug IDs, approve draft tests with evidence, close superseded AUDs, retire dead checklist dirs

# Ledger housekeeping

Findings F-066, F-068, F-101, F-128, F-136 (owner-approved batch operations on this repo's ledger).
## Acceptance Criteria

- [ ] AC1: Given 37 draft-slug IDs on main, when renumber-drafts runs, then every reference and the findings baseline are updated and lint passes.
- [ ] AC2: Given 47 draft UT/IT/QT with passing verify evidence, when reviewed, then they are approved via the CLI.
- [ ] AC3: Given 126 open auto-generated AUDs, when batch-closed, then brief no longer counts them as open work.
- [ ] AC4: Given the dead readiness checklist dir and tracked checklist-log files, when removed/untracked, then no loader or test references them.
