---
id: STORY-664
title: Autoresearch invariant sheets; skill-standards becomes DEC/ARCH
type: story
status: verified
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:3289341fad9e
modified: '2026-09-13'
---

# Autoresearch invariant sheets; skill-standards becomes DEC/ARCH

Per SPIKE-002 STORY-9 section, gated on the CLI-backstops story. skill-standards migration per DEC-082.

## Acceptance Criteria

1. autonomous-loop-protocol.md and competition-setup-protocol.md collapse to invariant sheets (budget, one LOOP/COMP, one atomic EXPT, commit-before-verify, no `git add -A`, persist condensation_brief, stop on goals-met/budget; stdout-is-one-number, dry-run-before-first-LOOP, frozen exam fields, eval-data off-limits, human gate on COMP completed).
2. finding-generation-protocol.md keeps the create-vs-update/supersede/falsify map with the FIND draft→confirmed gate on the user.
3. docs/skill-standards.md becomes derived rendering; the normative standards live in DEC-083 + ARCH-030.
4. tests/test_autoresearch_pack.py pins the invariant sheets.
