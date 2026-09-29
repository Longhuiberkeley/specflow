---
id: STORY-689
title: 'Core lifecycle skills: ship reorder, execute output_files, review scope, lens
  keys, BP path, context rule'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- skills
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:a7c27e413cf0
modified: '2026-09-30'
output_files:
- src/specflow/templates/skills/shared/specflow-ship/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/references/verification-contracts.md
- src/specflow/templates/skills/shared/specflow-artifact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-change-impact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-references/references/adversarial-lenses.md
- src/specflow/templates/skills/shared/specflow-references/references/bp-authoring.md
- src/specflow/templates/skills/shared/specflow-references/references/approval-presentation.md
- src/specflow/templates/skills/shared/specflow-init/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/references/thinking-techniques.md
- src/specflow/templates/skills/shared/specflow-plan/SKILL.md
- src/specflow/templates/skills/shared/specflow-plan/references/link-roles.md
- src/specflow/templates/skills/shared/specflow-plan/references/thinking-techniques.md
- src/specflow/templates/skills/shared/specflow-start/SKILL.md
- src/specflow/templates/skills/shared/specflow-doc/SKILL.md
- src/specflow/templates/skills/shared/specflow-doc/references/citation-syntax.md
- src/specflow/templates/agent-context.md
- src/specflow/packs/autoresearch/pack.yaml
- .claude/skills
- tests/test_core_skill_text.py
---

# Core lifecycle skills: ship reorder, execute output_files, review scope, lens keys, BP path, context rule

## Acceptance Criteria
1. Ship runs verify, document-changes, lens pass and the gate before baseline create, then phase-set complete and a handoff; the skill is router-style under 50 lines.
2. Execute records output_files on the STORY after implemented; artifact-review calls the composite command, stops only on blockers naming the artifact, and uses trace.
3. change-impact-review and adversarial-lenses use the catalog underscore lens keys; the dollar-spend example is replaced by a subagent count.
4. init, discover and plan use practices seed and practices validate instead of the deprecated handbook alias; bp-authoring.md matches the five-section body, draft-plus-provenance creation and spec-side guided_by; discover and plan tell the agent to link in-scope approved BPs via guided_by and link-roles.md has the row.
5. agent-context.md narrows the never-hand-edit rule to state, schemas and indexes, drops the bare cascade-status clause, and the autoresearch snippet says exit 3 proceeds; the init skill's truncated sections, domain labels, CI default and pack-author route are fixed.
6. Every change is mirrored byte-identically to .claude/skills.
