---
id: STORY-058
title: Create DDD selection decision tree reference document
type: story
status: implemented
priority: low
tags:
- plan
- reference
- docs
suspect: false
links:
- target: REQ-026
  role: implements
- target: ARCH-020
  role: guided_by
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:cffa9d8763d0
---

# Create DDD selection decision tree reference document

Author a DDD selection reference document with a decision checklist that guides the plan skill in determining which ARCH components need detailed design artifacts.

## Acceptance Criteria

1. Given the reference document at `.claude/skills/specflow-plan/references/ddd-selection.md`, when a user reads it, then it contains a 6-question decision checklist covering state machines, data transformations, external protocols, complex calculations, concurrent access, and error recovery.
2. Given a question where all answers are NO, when the checklist is applied, then the guidance states the ARCH's interface-level description is sufficient without a DDD.
3. Given a question where any answer is YES, when the checklist is applied, then the guidance states a DDD artifact is recommended.
4. Given the plan skill Step 4 instruction, when it references the DDD selection guide, then the SKILL.md explicitly mentions reading `references/ddd-selection.md` before creating DDD artifacts.
