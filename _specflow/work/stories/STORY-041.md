---
id: STORY-041
title: Add EARS patterns and quality guidance to normative-language reference
type: story
status: approved
priority: high
tags:
- quality
- ears
- discover
suspect: false
links:
- target: REQ-010
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-21'
---

# Add EARS patterns and quality guidance to normative-language reference

Enhance normative-language.md with EARS sentence patterns, ambiguity word list, compound shall detection, and passive voice guidance. Update the /specflow-discover skill to reference this guidance.

## Description

The current normative-language.md covers RFC 2119 keywords and basic anti-patterns but is missing EARS (Easy Approach to Requirements Syntax) patterns, an ambiguity word list, and compound shall/passive voice detection. Adding these to the reference file and the discover skill shifts quality left — requirements are created correctly from the start.

## Acceptance Criteria

1. Given normative-language.md, when reviewed, then all 5 EARS patterns (Ubiquitous, Event-Driven, Unwanted Behaviour, State-Driven, Optional Feature) are documented with examples
2. Given normative-language.md, when reviewed, then an ambiguity word list with at least 20 entries is present
3. Given normative-language.md, when reviewed, then compound shall detection guidance is present (split requirements with multiple "shall")
4. Given normative-language.md, when reviewed, then passive voice warning guidance is present
5. Given the /specflow-discover SKILL.md, when reviewed, then it references the enhanced normative-language guidance for requirements authoring
6. Given the installed skill copy at .claude/skills/specflow-discover/, when diffed with src/specflow/templates/skills/shared/specflow-discover/, then they are identical

## Out of Scope

- Adding lint checks for quality (that is the next story)
- Changing existing REQ artifacts to match EARS patterns

## Dependencies

- None
