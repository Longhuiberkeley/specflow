---
id: STORY-676
title: Evaluator fingerprint and drift routing (REQ-047)
type: story
status: implemented
suspect: false
links:
- target: REQ-047
  role: implements
- target: ARCH-038
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:bb9678cd9e21
thinking_techniques:
- premortem
- dependency-shock
modified: '2026-09-25'
---

# Evaluator fingerprint and drift routing (REQ-047)

## Story
Record COMP.evaluator_fingerprint (verify command plus evaluation-script hashes) at setup and add the fingerprint-drift lint check: flag once per COMP, route to the documented successor-COMP path, never per-EXPT, never retroactive.

## Acceptance Criteria
1. Given COMP creation, when setup completes, then the fingerprint is recorded and changes when an evaluation script hash changes.
2. Given an EXPT logged under a changed fingerprint, when artifact-lint runs, then exactly one finding with the successor-COMP routing appears.
3. Given historical EXPTs predating fingerprints, when lint runs, then nothing retroactive fires.
