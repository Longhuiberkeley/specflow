---
id: STORY-060
title: Persist discovery challenge results as decision artifacts
type: story
status: implemented
priority: low
tags:
- discover
- decisions
suspect: false
links:
- target: REQ-027
  role: implements
- target: ARCH-021
  role: guided_by
- target: DDD-021
  role: specified_by
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:37c22118b06c
---

# Persist discovery challenge results as decision artifacts

Update the discover skill to persist thinking technique challenge results as DEC artifacts, so assumptions, risks, and dropped requirements survive across sessions and are available to the plan skill.

## Acceptance Criteria

1. Given a discovery session where the devil's advocate technique surfaces a dropped requirement, when discover Step 5 completes, then a DEC artifact is created with title "Dropped: <summary>" and rationale in the body.
2. Given a discovery session where assumption surfacing identifies an implicit constraint, when discover Step 5 completes, then a DEC artifact is created with title "Assumption: <text>" and the consequence of being wrong.
3. Given the plan skill Step 2, when it loads context, then it reads DEC artifacts created during discovery and incorporates their insights into the architecture discussion.
4. Given a discovery session with no significant challenge results, when Step 5 completes, then no DEC artifacts are created (avoid noise).
