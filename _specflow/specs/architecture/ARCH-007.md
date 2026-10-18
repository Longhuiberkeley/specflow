---
id: ARCH-007
title: Traceability Chain Engine
type: architecture
status: implemented
priority: high
rationale: The traceability chain engine provides chain walking, depth computation,
  and informational reporting for compliance coverage visibility
tags:
- traceability
- reporting
- cli
suspect: false
links:
- target: REQ-007
  role: derives_from
- target: REQ-003
  role: derives_from
created: '2026-04-22'
fingerprint: sha256:597a8fad40a5
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 5
modified: '2026-10-08'
---

# Traceability Chain Engine

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-029); earlier text described a `trace --direction` flag, `(root, seed_id)` signatures, a role-only upstream walk and no research renderers.

The traceability chain engine walks the artifact link graph bidirectionally and computes chain depth statistics. It is exposed via `specflow trace` and the `--type chain-report` lint check.

## Components

### Chain Walking (`lib/artifacts.py`)

The core algorithm is a bidirectional walk over the artifact link graph:

- **Upstream walk** (`trace_chain`): BFS from the seed artifact over every link that `is_upstream_edge(source_type, role, target_type)` classifies as upstream. Direction is type-aware: `derives_from`/`complies_with` are always upstream; `implements`/`guided_by`/`specified_by` are upstream from work-ish sources; `verified_by` is upstream only from a test; `refined_by` is resolved by abstraction level; research parent roles are upstream. Uses a `visited` set to prevent cycles.
- **Downstream walk** (`trace_chain`): Scans all artifacts in the `id_index` to find those whose links point back to the seed (reverse-link resolution), then adds the seed's own outgoing edges that `is_downstream_owned_edge` classifies as naming its downstream (`verified_by → UT/IT/QT` from a spec/story, canonical `REQ refined_by → ARCH`). O(N) over all artifacts, acceptable for filesystem-native corpora.
- **Chain depth** (`compute_chain_depth`): Recursive DFS that follows child-held edges in the structural roles of `_CHAIN_DEPTH_ROLES` (derives_from, complies_with, refined_by, implements, specified_by, verified_by, executes, belongs_to, operates_on, condenses) plus parent-held `refined_by` along the canonical REQ→ARCH and ARCH→DDD pairs. It returns the longest path as a list of IDs.

### CLI Command (`commands/trace.py`)

`specflow trace <ID>` takes only the artifact ID. For COMP, LOOP and EXPT artifacts it dispatches first to the dedicated research renderers `_render_comp`, `_render_loop` and `_render_expt`. Every other artifact goes through `trace_chain(artifact_id, id_index, direction="both")`. The output shows upstream and downstream nodes (ID, type, title, status) as indented trees, followed by the chain depth and path from `compute_chain_depth`. The CLI has no direction filter.

### Chain Report (`commands/artifact_lint.py`)

The `--type chain-report` check (`_check_chain_report`) produces a depth distribution survey across all approved spec artifacts:

1. Filters to spec types (REQ/ARCH/DDD plus optional `--with-types` types such as HAZ, RISK, CTRL and pack-added types, found by a `TYPE_TO_PREFIX` scan of `TYPE_TO_DIR`).
2. Filters to `approved`, `implemented`, or `verified` status.
3. Calls `compute_chain_depth()` for each qualifying spec.
4. Builds a depth distribution histogram.
5. Identifies partial chains (depth > 1 but no verification test in path).
6. Always returns 0 blocking / 0 warnings — purely informational.

### Evidence Integration (`lib/evidence.py`)

The compliance evidence report calls `trace_chain(req.id, id_index, direction="downstream")` for each requirement to build the traceability matrix section.

## Architectural Decisions

- **Informational-only design**: Short chains are not errors because the right depth depends on the user's standard. This aligns with the Bring-Your-Own-Standard philosophy.
- **Pack extensibility**: Spec types are dynamically extended by scanning `TYPE_TO_PREFIX` for non-standard prefixes, so optional core types (HAZ, RISK, CTRL via `init --with-types`) and pack-added types are automatically included.
- **BFS for upstream, reverse scan for downstream**: Upstream follows explicit forward links; downstream mostly has no forward pointers, so it scans all artifacts (plus the few downstream-owned edges on the seed).

## Interfaces

| Interface | Direction | Purpose |
|-----------|-----------|---------|
| `trace_chain(artifact_id, id_index, direction='both') -> dict` | Inbound | Called by `trace.py` (`both`) and `evidence.py` (`downstream`); returns `upstream` and `downstream` node lists |
| `compute_chain_depth(artifact_id, id_index) -> list[str]` | Inbound | Called by `artifact_lint.py` chain-report and `trace.py` |
| `id_index` | Internal | Dict mapping artifact ID to Artifact object (`build_id_index`) |
