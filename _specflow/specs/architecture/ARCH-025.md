---
id: ARCH-025
title: Research-aware traceability chain
type: architecture
status: implemented
priority: medium
rationale: The trace command must walk the research hierarchy (COMP→LOOP→EXPT,
  COMP→FIND) using the link roles defined in ARCH-023.
tags:
- autoresearch
- trace
- traceability
suspect: false
links:
- target: REQ-034
  role: derives_from
- target: ARCH-023
  role: refines
created: '2026-06-07'
---

# Research-aware traceability chain

## Design

`specflow trace` uses the link-role taxonomy from ARCH-023 to render research chains:

- **COMP trace**: Shows COMP header, all LOOPs (`operates_on`), each LOOP's EXPTs (`belongs_to`), and FINDs (`belongs_to` on COMP + `condenses` on LOOP).
- **LOOP trace**: Shows parent COMP (`operates_on` reverse), all EXPTs (`belongs_to`), and any FINDs (`condenses`).
- **EXPT trace**: Walks up to parent LOOP (`belongs_to` reverse) and grandparent COMP (`operates_on` reverse).

## Key decisions

- **Role-based traversal**: No special research branch in trace code — it follows the same `derives_from`/`belongs_to`/`operates_on` roles used by all artifacts.
- **Separate FIND section**: FINDs appear in their own section (not nested under LOOPs) because they live at COMP level per ARCH-023.
