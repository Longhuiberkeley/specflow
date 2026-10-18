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
modified: '2026-10-08'
fingerprint: sha256:42ba281c5aa1
thinking_techniques:
- assumption_surfacing
version: 2
---

# Research-aware traceability chain

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-035); earlier text described one generic, recursive role-walk with no research branch, but `trace` dispatches COMP/LOOP/EXPT ids to dedicated one-level renderers.

## Component

`specflow trace <artifact-id>` (`commands/trace.py:run`) uses the link-role taxonomy from ARCH-023 to render research chains, and it does branch on the id prefix: COMP, LOOP and EXPT ids route to dedicated renderers (`_render_comp`, `_render_loop`, `_render_expt`) before the generic engine is reached. Those renderers do one-level lookups with `_find_children(parent_id, id_index, role)` and `_find_parent(child_id, id_index, role)` on hard-coded roles (`operates_on`, `belongs_to`, `condenses`). Every other type, FIND included, goes through the generic `art_lib.trace_chain(artifact_id, id_index, direction="both")` in `lib/artifacts.py` plus `compute_chain_depth(artifact_id, id_index)`.

## Structure

- **COMP trace**: Shows the COMP header, all LOOPs (artifacts linking to it with `operates_on`, each with its `mode`, iteration count and `best_metric`), each LOOP's EXPTs (`belongs_to`), and the FINDs that link to the COMP with `belongs_to`. FINDs that only `condenses` a LOOP appear in the LOOP view, not here, and the frontmatter `competition` field is not consulted.
- **LOOP trace**: Shows the parent COMP (the LOOP's own `operates_on` link), all EXPTs (`belongs_to`), and any FINDs that link to the LOOP with `condenses`.
- **EXPT trace**: Walks up to the parent LOOP (the EXPT's `belongs_to` link) and the grandparent COMP (that LOOP's `operates_on` link).

## Data Flow

User invokes `specflow trace COMP-NNN` → `discover_artifacts` + `build_id_index` → prefix dispatch in `run()` → the matching renderer looks up children and parents by fixed role names (COMP → LOOPs → EXPTs, COMP → FINDs; no recursion beyond those levels) → formatted output with grouped sections. Non-research ids take the generic `trace_chain` path (upstream and downstream trees plus chain depth).

## Responsibility

- Renders the full research hierarchy without requiring users to manually walk links between COMP, LOOP, EXPT, and FIND artifacts.
- FINDs appear in their own section (not nested under LOOPs) in the COMP view because they live at COMP level per ARCH-023, making them visible as top-level knowledge assets.
- Research views are a deliberate fork from the generic engine: the hand-written renderers know the four-tier hierarchy's roles, while spec/work artifacts share the role-based `trace_chain` traversal.
