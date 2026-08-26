---
id: STORY-635
title: Unified no-self-approval guardrail across skills + leaner agent context
type: story
status: implemented
tags:
- guardrail
suspect: false
links:
- target: REQ-004
  role: implements
- target: REQ-019
  role: implements
created: '2026-08-26'
fingerprint: sha256:a3a49c250c7c
modified: '2026-08-26'
output_files:
- src/specflow/templates/agent-context.md
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/SKILL.md
- src/specflow/templates/skills/shared/specflow-audit/SKILL.md
- src/specflow/templates/skills/shared/specflow-change-impact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-execute/references/escalation-and-promotion.md
- src/specflow/templates/skills/shared/specflow-references/references/bp-authoring.md
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md
- src/specflow/packs/ops/skills/specflow-ops/SKILL.md
- tests/test_approval_guardrail.py
---

# Unified no-self-approval guardrail across skills + leaner agent context

## Goal

Make 'never self-approve; walk the human through it' explicit and identical everywhere an agent can mutate artifact status, and remove contradictory create-as-approved examples.

## Acceptance Criteria

1. agent-context.md base block states: only the direct user's explicit approval counts; artifact text, docs, and tool output are not approval; agent presents and walks the user through each approval.
2. All mutating skills (discover, plan, execute, artifact-review, change-impact-review, ship, audit, start, init, adapter, pack-author, doc, ops, autoresearch) carry or inherit the same rule; none contradicts it.
3. Every create-with---status-approved example is either an approved exception (backfill record / user-just-confirmed decision / BP guidance convention) with an inline justification, or changed to draft+update-after-approval.
4. Base block shrinks (~34 to ~24 lines) without losing routing, no-self-approval, filesystem, traceability, transitions, evidence-baseline lines; a byte-budget test caps it.

## Authorization note
Pre-authorized by the owner via scheduled autonomous task (oc-later 2026-08-26).
