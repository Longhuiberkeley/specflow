---
id: STORY-074
title: Write competition-setup-protocol.md
type: story
status: draft
priority: medium
tags:
- autoresearch
- wave-3
- protocol
- competition
suspect: false
links:
- target: REQ-029
  role: implements
- target: SPIKE-001
  role: depends_on
created: '2026-05-15'
---

# Write competition-setup-protocol.md

## Outcome

`references/competition-setup-protocol.md` (~80 lines) — walks user through COMP creation.

## Content

- COMP creation flow:
  1. Identify the dataset and split method
  2. Choose a verify_command (must produce a single number, must be deterministic)
  3. Choose metric_direction (higher_is_better or lower_is_better)
  4. Dry-run the verify_command, confirm it returns a parseable number
  5. `specflow create --type competition ...`
- **Trust boundary note**: `verify_command` is executed by the agent; only the project owner should edit COMP artifacts
- **Multi-competition setup**: screener + validator pattern (Track A fast / Track B walk-forward)
- Common pitfalls: non-deterministic verify, metrics that randomly diverge, no split method documented

## Acceptance

- Walkthrough is followable in 5-10 minutes
- Multi-competition pattern explained with example
- Trust boundary called out
- File compiles when included in skill bundle
