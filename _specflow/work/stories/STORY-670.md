---
id: STORY-670
title: bp-application evidence check with tailoring and migration stamp (REQ-045)
type: story
status: implemented
suspect: false
links:
- target: REQ-045
  role: implements
- target: ARCH-036
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:225cba543bec
thinking_techniques:
- premortem
- dependency_shock
- worst_case_user
- composition
modified: '2026-10-08'
---

# bp-application evidence check with tailoring and migration stamp (REQ-045)

## Story
Implement the single evidence-based bp-application lint check modeled on compliance-evidence: graph facts only (link presence, field values, coverage arithmetic, test-result status), warning-first with opt-in lint.bp_evidence_strict, skipping BPs lacking provenance (migration stamp) and artifacts unmodified since BP approval (backfill grace). Tailoring records validate the cited DEC exists and is approved.

## Acceptance Criteria
1. Given a REQ citing an in-scope BP via guided_by, when artifact-lint runs, then the check verifies evidence and stays warning-first by default, blocking only under lint.bp_evidence_strict.
2. Given an unstamped legacy BP, when the check runs, then it is skipped entirely (no escalation exposure, DEC-089).
3. Given a dropped mandatory practice, when the tailoring record cites a draft DEC, then the check warns; with an approved DEC it passes.
4. Given body-text criteria in a Verification section, when the check runs, then they render as advisory inspection items, never compiled predicates.
