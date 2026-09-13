---
id: ARCH-032
title: 'Autoresearch methodology context architecture: thin checklists, rolling evaluation'
type: architecture
status: approved
rationale: Architecture record for REQ-040 (coverage structural gap; shipped behavior
  documented retrospectively).
suspect: false
links:
- target: REQ-040
  role: derives_from
created: '2026-09-13'
fingerprint: sha256:f74c31c49988
thinking_techniques:
- assumption-surfacing
modified: '2026-09-13'
---

# Autoresearch methodology context architecture: thin checklists, rolling evaluation

## Structure

REQ-040 keeps domain methodology out of shipped context and puts mechanics in on-demand references: `domain-research-checklists.md` is a thin concept-to-artifact mapping (five domain keys — quant, tabular_ml, vision, nlp, generic — plus universal open questions) rather than a subfield methodology menu (DEC-078/080 doctrine), and `references/rolling-evaluation.md` carries the operator-ratified rolling-evaluation recipe (fixed train/val/test split vs rolling windows, when each applies).

## Responsibilities

- DEC-079 records the COMP churn rule: frozen competitions, successor chains, window advance.
- `window_end` is a registered COMP schema field, so rolling windows are expressible without freeform fields.
- Protocol call sites that resolve domain keys keep working — the rewrite preserves the five keys they select on.

## Dependencies

Implementing stories: STORY-653 (recipe, churn rule, window_end) and STORY-654 (thin checklists). The rolling-evaluation reference is consulted on demand by the autoresearch skill router.
