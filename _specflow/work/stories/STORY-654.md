---
id: STORY-654
title: Thin pack domain-research checklists per DEC-080
type: story
status: implemented
rationale: Rewrite references/domain-research-checklists.md to concept-to-artifact
  mapping plus universal open questions (DEC-080 extension of DEC-078), preserving
  the five domain keys used by protocol call sites; update SKILL.md references; denylist
  gate must stay green.
suspect: false
links:
- target: REQ-040
  role: implements
- target: DEC-080
  role: guided_by
created: '2026-09-11'
fingerprint: sha256:f48818149cd9
modified: '2026-09-13'
---

# Thin pack domain-research checklists per DEC-079

## Acceptance Criteria

1. domain-research-checklists.md keeps the five domain keys (quant, tabular_ml, vision, nlp, generic) while teaching concept-to-artifact mapping plus universal open questions only.
2. Protocol call sites that resolve domain keys still work (tests/test_autoresearch_pack.py).
