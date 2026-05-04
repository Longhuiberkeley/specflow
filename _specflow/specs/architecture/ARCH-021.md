---
id: ARCH-021
title: Skill Continuity Layer
type: architecture
status: implemented
suspect: false
links:
- target: REQ-027
  role: derives_from
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:c11a474075c1
---

# Skill Continuity Layer

Ensures discovery-phase context survives into the planning phase by persisting challenge results, modeling inter-REQ dependencies, passing domain classification to plan, and improving the discover-to-plan handoff.

## Package Structure

```
.claude/skills/specflow-discover/SKILL.md  — Updated: persist challenges, REQ deps, handoff message
.claude/skills/specflow-plan/SKILL.md      — Updated: read domain config, consume DEC artifacts
```

## Component Responsibilities

1. **Challenge Result Persister**: During discover Step 5, when thinking techniques surface assumptions, risks, or dropped requirements, creates DEC artifacts with rationale. These persist across sessions and are available to the plan skill.

2. **Inter-REQ Dependency Prompter**: During discover Step 4, explicitly asks the user whether any requirements depend on others being satisfied first. Records dependencies as `derives_from` links between REQ artifacts.

3. **Domain Context Pass-Through**: Plan skill Step 2 reads `.specflow/config.yaml` domain and tags, uses them to inform decomposition approach and scope architecture discussion.

4. **Handoff Message Improver**: Discover skill exit message explicitly lists REQ IDs that need approval, provides the `specflow update` command, and recommends running `/specflow-plan` after approval.

## Interfaces

- Skill instruction updates only (no new CLI commands)
- DEC artifacts created via existing `specflow create --type decision`
- REQ-to-REQ links via existing `derives_from` link role
- Domain config read via existing `specflow status` or config.yaml parsing

## Dependencies

- Existing DEC artifact type
- Existing `derives_from` link role between REQs (already allowed in schema)
- Existing domain/tags in config.yaml

## Data Flow

1. Discover Step 5: challenges produce DEC artifacts
2. Discover Step 4: inter-REQ deps captured as links
3. Discover Step 7: exit message lists draft REQs needing approval
4. Plan Step 2: reads domain config, loads DEC artifacts from discover
