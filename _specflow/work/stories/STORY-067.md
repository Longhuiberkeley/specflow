---
id: STORY-067
title: Extend specflow trace to render research chain
type: story
status: implemented
priority: medium
tags:
- autoresearch
- wave-1
- trace
suspect: false
links:
- target: REQ-034
  role: implements
created: '2026-05-15'
modified: '2026-06-15'
fingerprint: sha256:b09436eed97b
---

# Extend specflow trace to render research chain

## Outcome

`specflow trace <id>` renders a research-aware hierarchy when the artifact is COMP/LOOP/EXPT/FIND.

## Scope

- `src/specflow/commands/trace.py:18-29` — add custom renderer for research artifacts
- Possibly a new helper in `src/specflow/lib/artifacts.py` to walk COMP → LOOPs → EXPTs efficiently
- Realistic size estimate: ~80 lines (not 30 — the existing `_print_tree` is flat upstream/downstream)

## Acceptance Criteria

1. `specflow trace COMP-NNN` shows: COMP header, list of LOOPs nested under COMP, each LOOP with mode/iter/best/status, EXPT summary counts per LOOP, separate FINDINGs section with FIND IDs and statuses
2. `specflow trace LOOP-NNN` shows parent COMP + all EXPTs in that LOOP
3. `specflow trace EXPT-NNN` shows parent LOOP + COMP
4. Non-research artifacts continue to use the existing flat upstream/downstream renderer
