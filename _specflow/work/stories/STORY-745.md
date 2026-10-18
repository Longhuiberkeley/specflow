---
id: STORY-745
title: 'W-1 agent-safety prose: fix every blocking/warning skill and checklist site
  from SPIKE-008 in both skill trees, add the D1 approval carve-out, pin changed sentences'
type: story
status: verified
tags:
- consistency
- v1.17.7
suspect: false
links:
- target: REQ-070
  role: implements
- target: SPIKE-008
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:8847036d0d97
modified: '2026-10-18'
output_files:
- .claude/skills/specflow-adapter/SKILL.md
- .claude/skills/specflow-adapter/references/adapter-framework.md
- .claude/skills/specflow-adapter/references/team-setup.md
- .claude/skills/specflow-artifact-review/SKILL.md
- .claude/skills/specflow-artifact-review/references/challenge-engine.md
- .claude/skills/specflow-artifact-review/references/checklist-assembly.md
- .claude/skills/specflow-artifact-review/references/severity-levels.md
- .claude/skills/specflow-audit/SKILL.md
- .claude/skills/specflow-change-impact-review/SKILL.md
- .claude/skills/specflow-discover/SKILL.md
- .claude/skills/specflow-discover/references/conflict-check.md
- .claude/skills/specflow-discover/references/framing.md
- .claude/skills/specflow-doc/SKILL.md
- .claude/skills/specflow-doc/references/citation-syntax.md
- .claude/skills/specflow-doc/references/staleness-rules.md
- .claude/skills/specflow-execute/SKILL.md
- .claude/skills/specflow-execute/references/verification-contracts.md
- .claude/skills/specflow-execute/references/wave-computation.md
- .claude/skills/specflow-init/SKILL.md
- .claude/skills/specflow-pack-author/SKILL.md
- .claude/skills/specflow-plan/SKILL.md
- .claude/skills/specflow-plan/references/link-roles.md
- .claude/skills/specflow-plan/references/story-writing.md
- .claude/skills/specflow-references/references/adversarial-lenses.md
- .claude/skills/specflow-references/references/approval-presentation.md
- .claude/skills/specflow-references/references/bp-authoring.md
- .claude/skills/specflow-ship/SKILL.md
- .claude/skills/specflow-start/SKILL.md
- AGENTS.md
- src/specflow/templates/agent-context.md
- src/specflow/templates/checklists/in-process/requirement-writing.yaml
- src/specflow/templates/checklists/in-process/story-writing.yaml
- src/specflow/templates/checklists/phase-gates/executing-to-verifying.yaml
- src/specflow/templates/checklists/phase-gates/planning-to-executing.yaml
- src/specflow/templates/checklists/phase-gates/specifying-to-planning.yaml
- src/specflow/templates/checklists/phase-gates/verifying-to-complete.yaml
- src/specflow/templates/skills/shared/specflow-adapter/SKILL.md
- src/specflow/templates/skills/shared/specflow-adapter/references/adapter-framework.md
- src/specflow/templates/skills/shared/specflow-adapter/references/team-setup.md
- src/specflow/templates/skills/shared/specflow-artifact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-artifact-review/references/challenge-engine.md
- src/specflow/templates/skills/shared/specflow-artifact-review/references/checklist-assembly.md
- src/specflow/templates/skills/shared/specflow-artifact-review/references/severity-levels.md
- src/specflow/templates/skills/shared/specflow-audit/SKILL.md
- src/specflow/templates/skills/shared/specflow-change-impact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/references/conflict-check.md
- src/specflow/templates/skills/shared/specflow-discover/references/framing.md
- src/specflow/templates/skills/shared/specflow-doc/SKILL.md
- src/specflow/templates/skills/shared/specflow-doc/references/citation-syntax.md
- src/specflow/templates/skills/shared/specflow-doc/references/staleness-rules.md
- src/specflow/templates/skills/shared/specflow-execute/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/references/verification-contracts.md
- src/specflow/templates/skills/shared/specflow-execute/references/wave-computation.md
- src/specflow/templates/skills/shared/specflow-init/SKILL.md
- src/specflow/templates/skills/shared/specflow-pack-author/SKILL.md
- src/specflow/templates/skills/shared/specflow-plan/SKILL.md
- src/specflow/templates/skills/shared/specflow-plan/references/link-roles.md
- src/specflow/templates/skills/shared/specflow-plan/references/story-writing.md
- src/specflow/templates/skills/shared/specflow-references/references/adversarial-lenses.md
- src/specflow/templates/skills/shared/specflow-references/references/approval-presentation.md
- src/specflow/templates/skills/shared/specflow-references/references/bp-authoring.md
- src/specflow/templates/skills/shared/specflow-ship/SKILL.md
- src/specflow/templates/skills/shared/specflow-start/SKILL.md
- tests/test_core_skill_text.py
---

# W-1 agent-safety prose: fix every blocking/warning skill and checklist site from SPIKE-008 in both skill trees, add the D1 approval carve-out, pin changed sentences

## Scope
Every blocking/warning row of SPIKE-008 whose site is under `.claude/skills` or `src/specflow/templates/checklists` (mirror to `src/specflow/templates/skills/shared`). Adds the D1 carve-out once in `specflow-references/references/approval-presentation.md` with a pointer from the discover/plan/execute/audit/artifact-review/change-impact-review gates; the D5 severity-mapping table in severity-levels.md; D6 wording in the adapter team-setup reference.

## Acceptance criteria
- AC1: Given each SPIKE-008 Round 1/2 row with fix kind prose or checklist and severity blocking or warning, when its source site is re-read, then the quoted claim is gone or now matches the engine side cited in the row.
- AC2: Given `diff -rq .claude/skills src/specflow/templates/skills/shared`, when it runs, then it prints nothing.
- AC3: Given `tests/test_core_skill_text.py`, when the suite runs, then every changed normative sentence is pinned with a `# SPIKE-008` comment and passes; `tests/test_reference_lint.py` budgets hold (adapter SKILL.md ≤ its ceiling).
- AC4: Given approval-presentation.md, when read, then one sentence states that only the direct user in the current session can delegate approvals and never for a release or risk-tier 2 action, and each of the six gates points at it.
