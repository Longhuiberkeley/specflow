---
id: STORY-675
title: 'Knowledge flow: plan --inherit, condensation requirement, top-3 status, adjacent-field
  lens (REQ-046)'
type: story
status: implemented
suspect: false
links:
- target: REQ-046
  role: implements
- target: ARCH-037
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:22d9c0ca75fd
thinking_techniques:
- premortem
- dependency_shock
modified: '2026-10-08'
---

# Knowledge flow: plan --inherit, condensation requirement, top-3 status, adjacent-field lens (REQ-046)

## Story
Ship the knowledge-flow pieces: autoresearch plan --inherit LOOP-NNN machine-seeding the next agenda from unexplored_directions, open entries, and the latest condensation brief; review requires a condensation brief at LOOP completion (replacing the iteration-count existence check); status output ranks and caps to the top three actionable signals; landscape-resurvey.md gains the adjacent-field practice lens (Kaggle, quant, experiment design) consulted via practices list --scope framing.

## Acceptance Criteria
1. Given a completed LOOP, when plan --inherit runs, then the seeded agenda cites unexplored_directions, open entries, and the brief with rationales.
2. Given LOOP completion without a condensation brief, when review runs, then it is required before completion.
3. Given more than three advisory signals, when status runs, then only the top three render with a pointer to the full ledger.
4. Given a landscape re-survey, when the agent consults guidance, then the adjacent-field lens is referenced with the practices framing.
