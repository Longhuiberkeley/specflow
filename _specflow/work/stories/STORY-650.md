---
id: STORY-650
title: 'COMP closure gate: criteria, human gate, lint warn'
type: story
status: implemented
rationale: "COMP completion has no protocol text, criteria, or human gate \u2014 the\
  \ root cause of premature closure. Add closure protocol to the pack skill (every\
  \ goal satisfied-with-FIND-evidence or abandoned-with-reason; direct-user confirmation),\
  \ plus a deterministic artifact-lint warn for completed COMPs with zero confirmed\
  \ FINDs."
suspect: false
links:
- target: REQ-039
  role: implements
created: '2026-09-11'
fingerprint: sha256:b34690da3adb
modified: '2026-09-13'
---

# COMP closure gate: criteria, human gate, lint warn

## Acceptance Criteria

1. COMP completion requires every `goals` entry satisfied-with-confirmed-FIND-evidence or explicitly abandoned-with-reason, plus direct-user confirmation (no self-approval).
2. `artifact-lint` warns on a completed COMP with zero confirmed FINDs, resolving FIND→COMP via both frontmatter competition and belongs_to links (tests/test_artifact_lint.py).
3. COMP creation/closure transitions serialize via the creation-status gate and locks (tests/test_v1145_locks.py).
