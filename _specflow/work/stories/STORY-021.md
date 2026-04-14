---
id: STORY-021
title: Audit and rewrite the four existing SKILL.md prompts
type: story
status: draft
priority: high
tags:
  - quality
  - skills
  - M1-clarity
suspect: false
created: '2026-04-14'
---

# Audit and rewrite the four existing SKILL.md prompts

## Description

The reasoning layer in SpecFlow's four core skills (specflow-discover, specflow-plan, specflow-execute, specflow-verify) has never been reviewed holistically. These prompts are load-bearing: every user interaction flows through them. Audit each SKILL.md for coherence, completeness, and alignment with the retrospective's lifecycle design (retrospective §4). Rewrite where needed to match the featured skill interface specs.

## Acceptance Criteria

1. Each of the four SKILL.md files is reviewed against the interface spec in retrospective §4 and any gaps (missing reads/writes, incorrect exit behavior, incomplete compositional description) are documented and fixed

2. The specflow-verify skill is assessed for rename to specflow-artifact-review (coordinate with STORY-022, but the prompt content rewrite is independent)

3. No SKILL.md exceeds 500 lines per docs/skill-standards.md

4. Each skill correctly references only CLI commands that exist (no phantom commands), and references deterministic scripts in scripts/ where applicable

## Out of Scope

- Renaming the verify skill directory (that's STORY-022)
- Writing new skills (artifact-review depth/lenses is STORY-024)
- Thin-skill wrappers for Tier 2/3 commands (STORY-022)

## Dependencies

- None (this is the load-bearing first item)
