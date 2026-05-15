---
id: ARCH-023
title: Four-tier research artifact hierarchy
type: architecture
status: draft
priority: high
rationale: Without explicit hierarchy and link roles, queries like 'all EXPTs for
  this COMP' or 'what FINDs feed the next LOOP' become unanswerable. The four tiers
  cleanly separate scope, session, attempt, and condensed knowledge.
tags:
- autoresearch
- architecture
- hierarchy
suspect: false
links:
- target: REQ-028
  role: derives_from
- target: REQ-029
  role: derives_from
- target: REQ-030
  role: derives_from
- target: REQ-031
  role: derives_from
created: '2026-05-15'
---

# Four-tier research artifact hierarchy

Research artifacts form a four-tier hierarchy:

```
COMP-NNN (scope: dataset + metric + verify_command)
  ├── LOOP-NNN (session: mode + budget + knowledge_input)
  │     ├── EXPT-NNN (attempt: terminal status + metric_value)
  │     ├── EXPT-NNN
  │     └── ...
  └── FIND-NNN (condensed knowledge, lives at COMP level)
```

## Link roles

| From | To | Role | Direction |
|---|---|---|---|
| LOOP | COMP | operates_on | LOOP points to COMP |
| EXPT | LOOP | belongs_to | EXPT points to LOOP |
| FIND | COMP | belongs_to (via required `competition` field) | FIND points to COMP |
| FIND | LOOP | condenses (via optional `source_loop`) | FIND points to LOOP |
| LOOP | FIND | informs (via `knowledge_input`) | LOOP points to prior FINDs |
| FIND | FIND | supersedes | FIND replaces an older FIND |
| FIND | COMP | validated_by | cross-competition validation |

## Why FINDs live at COMP level (not LOOP)

A FIND is the unit of *transferable* knowledge — a new LOOP starts by reading all confirmed FINDs for its COMP. If FINDs lived per-LOOP, the agent would have to walk all prior LOOPs each time. Competition-level FINDs collapse that walk into a single query.

## Why EXPT is write-once

An EXPT records one attempt with its final outcome. There is no "re-running" an EXPT (that would be a new EXPT). All four allowed_status values have empty prior-state lists — see DEC for rationale.
