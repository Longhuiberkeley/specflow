---
id: STORY-UPDATESK-86fb
title: Update SKILL.md to thin CLI wrapper and add pack context injection
type: story
status: draft
suspect: false
links:
- target: REQ-AUTORESE-d684
  role: implements
created: '2026-05-16'
fingerprint: sha256:a557ed85a54a
---

# Update SKILL.md to thin CLI wrapper and add pack context injection

## Acceptance Criteria

1. SKILL.md body delegates to CLI subcommands instead of inline protocol steps
2. Pack context (COMP metadata, LOOP state) is injected into the agent prompt before execution
3. Skill remains under 500 lines after refactor
