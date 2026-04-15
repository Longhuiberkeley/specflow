---
id: STORY-024
title: Ship /specflow-artifact-review with tiered depth and thinking techniques
type: story
status: implemented
priority: high
tags:
- review
- quality
- M1-clarity
suspect: false
created: '2026-04-14'
checklists_applied:
- checklist: check-STORY-024
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-15'
fingerprint: sha256:b95df92dbbbb
---

# Ship /specflow-artifact-review with tiered depth and thinking techniques

## Description

Ship the renamed `/specflow-artifact-review` skill (was /specflow-verify) with three key capabilities: (1) tiered depth selection (quick / normal / deep), (2) four starter thinking techniques running as subagent fan-out, and (3) a CHL (challenge) artifact type with full lifecycle. Fold `/specflow-detect` (hygiene) into this skill as a silent pre-step.

### Depth tiers

- **quick**: deterministic lint + checklist-run only, zero LLM
- **normal**: lint + checklist + LLM judgment on target artifacts
- **deep**: normal + thinking techniques fan-out via subagents

### Starter thinking techniques (4 of 16 from retrospective §9)

1. Devil's advocate — assume the artifact is wrong
2. Premortem — fast-forward to failure, what caused it
3. Assumption surfacing — enumerate and attack implicit assumptions
4. Red/blue team — attacker vs. defender on security-adjacent artifacts

### Checklist-first workflow

Before selecting which thinking techniques to deploy, the skill reads existing assembled checklists for the target artifacts. This ensures techniques surface findings that go beyond what checklists already enforce, rather than duplicating known coverage. If a technique discovers a recurring best practice not yet codified, it may produce a new checklist item as a CHL artifact.

### CHL artifact type

New schema: `templates/schemas/challenge.yaml`. Fields include `id`, `title`, `type: challenge`, `status` (open/addressed/accepted/stale), `severity` (info/warn/error), `lens` (which thinking technique produced it), `links` (to target artifact). Lifecycle: `open → addressed → accepted → stale`.

### Composition

`artifact-lint` (deterministic) → `checklist-run` → read existing checklists → LLM judgment → optional thinking techniques. Detect (dead-code, similarity) runs silently inside review as hygiene pre-step; CLI `specflow detect` remains for CI.

## Acceptance Criteria

1. `specflow artifact-review --depth quick <artifact-ids>` runs deterministic lint + checklist with zero LLM tokens and returns exit code 0 (clean) or 2 (findings)

2. `specflow artifact-review --depth normal <artifact-ids>` adds LLM judgment and produces CHL artifacts in `_specflow/specs/challenges/` for any findings

3. `specflow artifact-review --depth deep --techniques devil,premortem,assumption,redblue <artifact-ids>` fans out 4 subagents in parallel, each producing CHL artifacts tagged with their technique name

4. CHL artifacts follow the schema in `templates/schemas/challenge.yaml` with status lifecycle open→addressed→accepted→stale

5. Technique selection UX reads existing checklists for target artifacts first, then presents available thinking techniques (not duplicating checklist coverage) with estimated token spend before launching subagents

6. Hygiene detect (dead-code, similarity) runs silently as a pre-step inside review; `specflow detect` CLI remains for CI

7. Exit codes: 0 = clean, 2 = open findings, 3 = tool error

## Out of Scope

- Remaining 12 thinking techniques from retrospective §9 (future progressive delivery)
- `/specflow-project-audit` (STORY-030)
- Change-audit pipeline (STORY-025)

## Dependencies

- STORY-022 (command rename — verify→artifact-review)
- STORY-021 (SKILL.md rewrite — the artifact-review skill prompt must be sound)
