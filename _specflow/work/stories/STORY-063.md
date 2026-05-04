---
id: STORY-063
title: Improve discover-to-plan handoff with explicit approval instructions
type: story
status: draft
priority: low
tags:
- discover
- plan
- handoff
suspect: false
links:
- target: REQ-027
  role: implements
- target: ARCH-021
  role: guided_by
- target: DDD-021
  role: specified_by
created: '2026-05-04'
---

# Improve discover-to-plan handoff with explicit approval instructions

Update the discover skill exit message to explicitly list which REQs need approval and provide the command, closing the unowned gap between discover and plan.

## Acceptance Criteria

1. Given a full-path discovery session that creates REQ-030, REQ-031, REQ-032 in draft status, when the session ends, then the exit message lists all draft REQ IDs and provides the `specflow update <ID> --status approved` command.
2. Given a lean-path discovery session that auto-approves REQs, when the session ends, then the exit message confirms REQs are already approved and recommends `/specflow-plan` directly.
3. Given the exit message, when a user reads it, then it is clear what action to take next and what command to run.
