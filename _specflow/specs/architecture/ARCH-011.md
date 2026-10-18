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
fingerprint: sha256:cd4f5ec8d692
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 3
modified: '2026-10-08'
---

# Tier 1 Conversational Routing

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-105); earlier text described 10 core skills and a default route to specflow-execute.

## Component

Skills are installed into the host's skills directory resolved by `lib/platform.py` (`get_skills_install_dir()`; `.claude/skills/` for Claude Code, one of the 13 platforms registered in `src/specflow/templates/platforms.yaml`). The shipped source is `src/specflow/templates/skills/shared/`, which `init` and `refresh` copy; in this repo the live `.claude/skills/` tree mirrors it byte for byte. Each skill is a directory containing a `SKILL.md` entry point and optional `references/` and `scripts/` subdirectories. The agent loads a skill when a user utterance matches the `description` in the skill's SKILL.md frontmatter.

## Structure

- **Core skills** (13 directories): the 12 skills named by `get_skill_names()` in `lib/platform.py` — `specflow-init`, `specflow-discover`, `specflow-plan`, `specflow-execute`, `specflow-artifact-review`, `specflow-change-impact-review`, `specflow-audit`, `specflow-ship`, `specflow-pack-author`, `specflow-adapter`, `specflow-doc`, `specflow-start` — plus `specflow-references`, a support directory of shared reference files (no SKILL.md).
- **Pack skills**: installed by `apply_pack()` (`lib/scaffold.py`) from `pack.yaml`'s `adds_skills` field into the platform skills install directory, without overwriting an existing skill.
- **Routing heuristic**: The agent matches user intent to the closest skill description. When the next step is unclear, `specflow-start` routes: it sends a project without `.specflow/` to `/specflow-init`, otherwise runs `specflow brief --next` and names the next skill.

## Interface

- **SKILL.md**: Markdown file with YAML frontmatter (`name`, and `description`, which is the trigger) followed by the workflow steps and pointers to references and scripts.
- **References directory**: Domain knowledge documents the skill injects into context (protocols, checklists, escalation rules).
- **Scripts directory**: Deterministic shell scripts that wrap CLI calls; the only one shipped is `specflow-pack-author/scripts/validate-pack.sh`, which delegates to `specflow pack-validate`. Other zero-token checks are CLI commands the skills call directly (e.g., `specflow artifact-lint`, `specflow project-audit`).

## Responsibility

- Skills provide the conversational interface layer — users invoke `/specflow-*` commands, not raw CLI.
- Each skill encodes a complete workflow (discover → plan → execute → ship) or a specialized subtask (audit, review, adapter config).
- Pack skills extend the routing surface without modifying core skills, preserving isolation between subsystems (e.g., autoresearch vs. engineering).
