---
id: STORY-647
title: 'v1.14.6: privacy completion — working-tree polish, denylist gate automation
  (CI+pytest), brief vanished symmetry + locking tests'
type: story
status: implemented
rationale: 'Finish REQ-038: neutralize residual descriptive context (STORY-075 title/h1/body,
  DEC-059 corpus phrasing); automate the DDD-029 denylist gate as a single-source
  script wired into CI and pytest (enumerated path allowlist: REQ-038, DDD-029, domain-research-checklists.md;
  .specflow/ out of scope); fix brief.py vanished-check has_informs asymmetry + stale
  docstring; add locking tests for the v1.14.5 lint/schema changes; hygiene: CHL-348
  close, QT-049 dup-link dedupe, CHANGELOG baseline-count fix.'
suspect: false
links:
- target: REQ-038
  role: implements
created: '2026-08-30'
fingerprint: sha256:1d4bbe3ef7ea
modified: '2026-08-30'
output_files:
- tests/test_v1145_locks.py
- scripts/denylist_gate.py
- tests/test_denylist_gate.py
---

# v1.14.6: privacy completion — working-tree polish, denylist gate automation (CI+pytest), brief vanished symmetry + locking tests
