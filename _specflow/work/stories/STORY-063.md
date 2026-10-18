---
id: STORY-063
title: Improve discover-to-plan handoff with explicit approval instructions
type: story
status: implemented
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
modified: '2026-05-05'
fingerprint: sha256:58977522b2fb
version: 1
---

# Improve discover-to-plan handoff with explicit approval instructions

Update the discover skill exit message to explicitly list which REQs need approval and provide the command, closing the unowned gap between discover and plan.

## Acceptance Criteria

1. Given a full-path discovery session that creates REQ-030, REQ-031, REQ-032 in draft status, when the session ends, then the exit message lists all draft REQ IDs and provides the `specflow update <ID> --status approved` command.
2. Given a lean-path discovery session that auto-approves REQs, when the session ends, then the exit message confirms REQs are already approved and recommends `/specflow-plan` directly.

> Amended 2026-10-18 (SPIKE-008 R1-139): discover never auto-approves. The lean path leaves its REQ and STORY in draft and points to `specflow approve --type REQ` and `specflow approve --type STORY`, then /specflow-execute; the full path points to `specflow approve --type REQ`, then /specflow-plan (specflow-discover SKILL.md).

3. Given the exit message, when a user reads it, then it is clear what action to take next and what command to run.
