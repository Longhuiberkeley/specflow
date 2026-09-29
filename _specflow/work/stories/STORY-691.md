---
id: STORY-691
title: 'Adoption pack: backfill commands run as documented'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- adoption
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:9c678011c2b7
modified: '2026-09-30'
output_files:
- src/specflow/packs/adoption/README.md
- src/specflow/packs/adoption/pack.yaml
- src/specflow/packs/adoption/skills/specflow-adopt/SKILL.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/as-built-baseline-protocol.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/backfill-extraction-checklist.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/conflict-resolution-protocol.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/incremental-adoption-protocol.md
- src/specflow/commands/detect.py
- tests/test_adopt_backfill_smoke.py
---

# Adoption pack: backfill commands run as documented

## Acceptance Criteria
1. Every documented backfill create carries --sanctioned with the as-built justification and succeeds through the creation-status gate.
2. Needs-decision tagging preserves the backfilled tag and the skill finds those artifacts with specflow list --tags.
3. retro-link is documented as project-wide and final-pass only; per-boundary passes use update --output-files; the detect orphan-code tip no longer recommends --adopt inside an adoption run.
4. Legacy D-20 references become DEC-057; a CLI smoke test runs the documented ARCH backfill in a temporary project with zero lint warnings.
