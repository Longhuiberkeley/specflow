---
id: STORY-070
title: Author specflow-autoresearch SKILL.md with subcommands and setup gate
type: story
status: implemented
priority: high
tags:
- autoresearch
- wave-3
- skill
suspect: false
links:
- target: REQ-028
  role: implements
- target: REQ-031
  role: implements
- target: SPIKE-001
  role: depends_on
created: '2026-05-15'
fingerprint: sha256:cf3d98d175c8
---

# Author specflow-autoresearch SKILL.md with subcommands and setup gate

## Outcome

`src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md` exists, ready for distribution.

## Content (~300 lines)

- **Frontmatter**: name, description
- **Activation triggers**: invokes when user says 'run research loop', 'explore competition', 'set up competition', 'run experiments overnight', etc.
- **Subcommands**:
  - `/specflow-autoresearch` — run an autonomous LOOP on a COMP
  - `/specflow-autoresearch:plan` — plan a LOOP (mode, budget, knowledge_input)
  - `/specflow-autoresearch:review` — review FINDs and EXPTs for a COMP
  - `/specflow-autoresearch:leaderboard` — show best EXPTs across LOOPs
- **Setup gate**: requires COMP exists, verify_command dry-runs, LOOP in draft, user confirmation
- **Loop execution**: references the 8-phase protocol
- **Anti-patterns**: from autoresearch's `core-principles.md` (merged in)

## Acceptance Criteria

1. File renders correctly via the existing skill display in Claude Code / Cursor / etc.
2. Each subcommand has a one-paragraph description and an example invocation
3. Setup gate steps explicit and numbered
4. Anti-patterns section includes all 7 Karpathy principles from autoresearch fork
