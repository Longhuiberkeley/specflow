---
id: STORY-657
title: Rewrite all 15 skill catalog descriptions to narrow one-liners
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:768c9e9248ea
modified: '2026-09-13'
---

# Rewrite all 15 skill catalog descriptions to narrow one-liners

Every SKILL.md frontmatter description becomes a one-line narrow trigger per audit O1: the situation where the skill is REQUIRED. No keyword walls, no NOT-for lists. Includes the 5 skills outside the audit table (ship, adapter, pack-author, autoresearch, adopt) rewritten in the same audited style.

## Acceptance Criteria

1. All 15 shipped SKILL.md frontmatter descriptions are one-line narrow REQUIRED-when triggers.
2. No description carries keyword walls or NOT-for lists.
3. The five skills outside the audit table (ship, adapter, pack-author, autoresearch, adopt) follow the same audited style.
