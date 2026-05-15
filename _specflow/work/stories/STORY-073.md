---
id: STORY-073
title: Write finding-generation-protocol.md
type: story
status: draft
priority: medium
tags:
- autoresearch
- wave-3
- protocol
- findings
suspect: false
links:
- target: REQ-030
  role: implements
created: '2026-05-15'
---

# Write finding-generation-protocol.md

## Outcome

`references/finding-generation-protocol.md` (~100 lines) — playbook for agents authoring FIND artifacts after a LOOP completes.

## Content

- **When to create a new FIND vs update an existing one**
- **How to aggregate EXPTs into a FIND**: read EXPTs filtered by `loop: LOOP-NNN`, group by `change_category`, identify which categories drove improvement
- **What goes in each field**:
  - `what_worked` — concrete approaches that improved metric
  - `what_failed` — falsified approaches (with EXPT references)
  - `next_steps` — suggested directions for the next LOOP
  - `confidence` — high (consistent across loops), medium (one loop), low (preliminary)
- **When to supersede a FIND**: new evidence contradicts or refines it
- **Cross-loop synthesis pattern**: a FIND with no `source_loop` summarizing patterns across multiple LOOPs by reading prior FINDs (not raw EXPTs)

## Acceptance

- Playbook covers all 4 lifecycle transitions (draft → confirmed → superseded/falsified)
- Example invocations for `specflow create --type finding` and `specflow update FIND-NNN --status superseded`
- Confidence assignment criteria are unambiguous
