---
id: ARCH-037
title: 'Autoresearch steering: frontier ledger, EDA lenses, error analysis, knowledge
  flow'
type: architecture
status: implemented
suspect: false
links:
- target: REQ-046
  role: derives_from
- target: DEC-088
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:bbc529903821
modified: '2026-09-25'
thinking_techniques:
- '[premortem'
- dependency-shock]
---

# Autoresearch steering: frontier ledger, EDA lenses, error analysis, knowledge flow

## Responsibility
Turn the autoresearch pack into a complete, self-measuring researcher: the zero-token frontier ledger (width and depth with stagnation states and an advisory move menu), applicability-aware EDA lenses replacing the dangling checks, error/results analysis as a first-class phase, analysis-only iterations exempt from streak windows, machine-seeded LOOP inheritance, the adjacent-field practice lens, and ranked top-three status output.

## Public interface
- commands/autoresearch.py: frontier (--comp, --json) rendering ledger + states + move menu + revisit candidates; plan --inherit LOOP-NNN; status ranking cap
- pack references: eda-lenses.md, error-analysis-protocol.md, landscape-resurvey.md (adjacent-field framing)
- EXPT change_category gains analysis; no_op runs exempt from every evidence-free streak window when anchored

## Dependencies
Reads EXPT/LOOP frontmatter that autoresearch log already mandates; optional EXPT lineage field; practices list --scope consumed as prose guidance only (no hard dependency on the spine).

## Data flow
EXPT/LOOP frontmatter -> frontier computation (lineage depth noise-adjusted via noise probe sigma, family width, agenda coverage) -> advisory rendering -> model decides; LOOP completion -> condensation brief -> plan --inherit seeds the next agenda.
