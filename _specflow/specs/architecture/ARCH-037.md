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
fingerprint: sha256:b5af9edafb5c
modified: '2026-10-08'
thinking_techniques:
- premortem
- dependency_shock
version: 1
---

# Autoresearch steering: frontier ledger, EDA lenses, error analysis, knowledge flow

## Responsibility
Turn the autoresearch pack into a complete, self-measuring researcher: the zero-token frontier ledger (width and depth with stagnation states and an advisory move menu), applicability-aware EDA lenses replacing the dangling checks, error/results analysis as a first-class phase, analysis-only iterations exempt from streak windows, machine-seeded LOOP inheritance, the adjacent-field practice lens, and ranked top-three status output.

## Public interface
- commands/autoresearch.py: frontier (--comp, --json) rendering ledger + states + move menu + revisit candidates; plan --inherit LOOP-NNN; status ranking cap
- pack references: eda-lenses.md, error-analysis-protocol.md, landscape-resurvey.md (adjacent-field framing)
- EXPT change_category gains analysis; no_op runs exempt from every evidence-free streak window when anchored

## Dependencies
Reads EXPT/LOOP frontmatter that autoresearch log already mandates; optional EXPT lineage field; `specflow list --type best-practice` consumed as prose guidance only (no hard dependency on the spine).

> Amended 2026-10-18 (SPIKE-008 R1-042): corrected in place. The earlier text named `practices list --scope`, which does not exist (`practices` has only seed, validate and migrate, cli.py:508).

## Data flow
EXPT/LOOP frontmatter -> frontier computation (lineage depth noise-adjusted via noise probe sigma, family width, agenda coverage) -> advisory rendering -> model decides; LOOP completion -> condensation brief -> plan --inherit seeds the next agenda.
