---
id: STORY-672
title: Autoresearch frontier ledger and move menu (REQ-046)
type: story
status: implemented
suspect: false
links:
- target: REQ-046
  role: implements
- target: ARCH-037
  role: guided_by
- target: DDD-031
  role: specified_by
created: '2026-09-25'
fingerprint: sha256:35326d62fe8c
thinking_techniques:
- premortem
- dependency-shock
modified: '2026-09-25'
---

# Autoresearch frontier ledger and move menu (REQ-046)

## Story
Implement specflow autoresearch frontier per DDD-031: per-lineage depth (noise-adjusted), per-COMP width, stagnation states, advisory move menu, revisit candidates, --json full ledger; add the optional EXPT lineage field; exempt anchored analysis no_op runs from every streak window.

## Acceptance Criteria
1. Given a fixture COMP with deep and wide EXPT histories, when frontier runs, then the ledger, states, and move menu render zero-token and --json emits the full structure.
2. Given EXPTs missing lineage, when frontier runs, then they count as singleton chains with no error.
3. Given an anchored no_op analysis EXPT, when streak windows are computed, then it is excluded (extends the STORY-665 window logic).
4. Given the module source, when audited, then no rotation rule keyed on counts exists (property test).
