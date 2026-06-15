---
id: ARCH-025
title: Research-aware traceability chain
type: architecture
status: implemented
priority: medium
rationale: "The trace command must walk the research hierarchy (COMP\u2192LOOP\u2192\
  EXPT, COMP\u2192FIND) using the link roles defined in ARCH-023."
tags:
- autoresearch
- trace
- traceability
suspect: false
links:
- target: REQ-034
  role: derives_from
- target: ARCH-023
  role: refined_by
created: '2026-06-07'
modified: '2026-06-15'
fingerprint: sha256:667cabf7f862
thinking_techniques: [assumption-surfacing]
---

# Research-aware traceability chain

## Component

`specflow trace` uses the link-role taxonomy from ARCH-023 to render research chains. The trace engine in `lib/artifacts.py:trace_chain` performs generic role-based traversal — no special research branch exists in the code.

## Structure

- **COMP trace**: Shows COMP header, all LOOPs (`operates_on`), each LOOP's EXPTs (`belongs_to`), and FINDs (`belongs_to` on COMP + `condenses` on LOOP).
- **LOOP trace**: Shows parent COMP (`operates_on` reverse), all EXPTs (`belongs_to`), and any FINDs (`condenses`).
- **EXPT trace**: Walks up to parent LOOP (`belongs_to` reverse) and grandparent COMP (`operates_on` reverse).

## Data Flow

User invokes `specflow trace COMP-NNN` → frontmatter parsing → link-chain walk using role names → recursive traversal down LOOP → EXPT and across COMP → FIND → formatted output with grouped sections.

## Responsibility

- Renders the full research hierarchy without requiring users to manually walk links between COMP, LOOP, EXPT, and FIND artifacts.
- FINDs appear in their own section (not nested under LOOPs) because they live at COMP level per ARCH-023, making them visible as top-level knowledge assets.
- Role-based traversal means the same trace engine handles research artifacts identically to spec/work artifacts — no fork in the logic.
