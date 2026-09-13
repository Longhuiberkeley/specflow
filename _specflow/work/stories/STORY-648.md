---
id: STORY-648
title: "v1.14.6: quant domain checklist thin rewrite \u2014 mapping, not finance"
type: story
status: implemented
rationale: 'Rewrite quant.md per DEC-078: keep the concept-to-artifact map and ~5
  universal open questions (data reality, split integrity, costs, regime robustness,
  multiple-testing awareness); delete subfield menus (Kelly, Bonferroni/PBO, vig,
  postseason) and the personal Algo-Betting framing. Template + .claude mirror byte-identical.'
suspect: false
links:
- target: REQ-038
  role: implements
created: '2026-08-30'
fingerprint: sha256:992c7fb99058
modified: '2026-09-13'
---

# v1.14.6: quant domain checklist thin rewrite — mapping, not finance

## Acceptance Criteria

1. The quant domain checklist teaches concept-to-artifact mapping, not finance methodology.
2. Template and live `.claude` mirror stay byte-identical (pinned by the mirror guard in tests/test_v1143_integration.py).
