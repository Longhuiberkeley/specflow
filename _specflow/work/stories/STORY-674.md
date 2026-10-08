---
id: STORY-674
title: Error-analysis protocol and analysis iterations (REQ-046)
type: story
status: implemented
suspect: false
links:
- target: REQ-046
  role: implements
- target: ARCH-037
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:989b4509f92b
thinking_techniques:
- premortem
- dependency_shock
modified: '2026-10-08'
---

# Error-analysis protocol and analysis iterations (REQ-046)

## Story
Add references/error-analysis-protocol.md making results analysis a first-class phase (OOF prediction-vs-truth slicing, residual inspection, worst-k review; P&L attribution and regime tags for strategies; train/OOF only, eval partition never read), register the analysis change_category, and teach the loop protocol that analysis-only iterations are anchored no_op EXPTs with research_progress.

## Acceptance Criteria
1. Given saved train/OOF diagnostics for the current best, when Phase 2 ideates, then the protocol references the error-analysis phase and its outputs feed hypotheses.
2. Given an analysis-only iteration, when logged via autoresearch log, then change_category analysis with anchored research_progress is accepted and rendered.
3. Given the protocol files, when grepped for eval-partition reads in analysis, then the isolation rule is stated explicitly.
