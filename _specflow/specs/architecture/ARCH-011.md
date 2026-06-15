---
id: ARCH-011
title: Tier 1 Conversational Routing
type: architecture
status: implemented
suspect: false
links:
- target: REQ-019
  role: derives_from
- target: IT-013
  role: verified_by
created: '2026-04-22'
fingerprint: sha256:f2f3094481f0
thinking_techniques: [assumption-surfacing, devil's-advocate]
version: 1
modified: '2026-06-15'
---

# Tier 1 Conversational Routing

## Component

The skill ecosystem lives in `.claude/skills/` (or the platform-equivalent directory resolved by `lib/platform.py`). Each skill is a directory containing a `SKILL.md` entry point and optional `references/` and `scripts/` subdirectories. The agent loads a skill via the skill tool when a user utterance matches the skill's trigger description.

## Structure

- **Core skills** (10 directories): `specflow-discover`, `specflow-plan`, `specflow-execute`, `specflow-artifact-review`, `specflow-audit`, `specflow-change-impact-review`, `specflow-ship`, `specflow-init`, `specflow-adapter`, `specflow-pack-author`.
- **Pack skills**: installed at runtime by `apply_pack()` from `pack.yaml`'s `adds_skills` field into the platform skills directory.
- **Routing heuristic**: The agent matches user intent to the closest skill trigger phrase. Ambiguous requests default to `specflow-execute` for implementation work.

## Interface

- **SKILL.md**: Markdown file with YAML-like sections defining trigger phrases, workflow steps, and references to scripts.
- **References directory**: Domain knowledge documents the skill injects into context (protocols, checklists, escalation rules).
- **Scripts directory**: Deterministic shell/Python scripts the skill invokes for zero-token validation (e.g., `artifact-lint`, `project-audit`).

## Responsibility

- Skills provide the conversational interface layer — users invoke `/specflow-*` commands, not raw CLI.
- Each skill encodes a complete workflow (discover → plan → execute → ship) or a specialized subtask (audit, review, adapter config).
- Pack skills extend the routing surface without modifying core skills, preserving isolation between subsystems (e.g., autoresearch vs. engineering).
