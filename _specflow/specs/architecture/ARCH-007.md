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
fingerprint: sha256:683906d8a098
version: 2
---

# Traceability Chain Engine

The traceability chain engine walks the artifact link graph bidirectionally and computes chain depth statistics. It is exposed via `specflow trace` and the `--type chain-report` lint check.

## Components

### Chain Walking (`lib/artifacts.py`)

The core algorithm is a bidirectional BFS over the artifact link graph:

- **Upstream walk**: BFS following `derives_from` and `complies_with` links from the seed artifact. Uses a `visited` set to prevent cycles.
- **Downstream walk**: Scans all artifacts in the `id_index` to find those whose links point back to the seed (reverse-link resolution). O(N) over all artifacts, acceptable for filesystem-native corpora.
- **Chain depth** (`compute_chain_depth`): Recursive DFS following reverse links to find the longest path to a leaf.

### CLI Command (`commands/trace.py`)

`specflow trace <ID>` renders the chain as an indented tree showing each linked artifact's ID, type, title, and status. Supports direction filtering (`--direction upstream|downstream|both`).

### Chain Report (`commands/artifact_lint.py`)

The `--type chain-report` check produces a depth distribution survey across all approved spec artifacts:

1. Filters to spec types (built-in + pack-added via `TYPE_TO_PREFIX` dynamic scan).
2. Filters to `approved`, `implemented`, or `verified` status.
3. Calls `compute_chain_depth()` for each qualifying spec.
4. Builds a depth distribution histogram.
5. Identifies partial chains (depth > 1 but no verification test in path).
6. Always returns 0 blocking / 0 warnings — purely informational.

### Evidence Integration (`lib/evidence.py`)

The compliance evidence report consumes `trace_chain()` to generate the traceability matrix section.

## Architectural Decisions

- **Informational-only design**: Short chains are not errors because the right depth depends on the user's standard. This aligns with the Bring-Your-Own-Standard philosophy.
- **Pack extensibility**: Spec types are dynamically extended by scanning `TYPE_TO_PREFIX` for non-standard prefixes, so pack-added types (HAZ, RISK, etc.) are automatically included.
- **BFS for upstream, reverse scan for downstream**: Upstream follows explicit forward links; downstream has no forward pointers, so it scans all artifacts.

## Interfaces

| Interface | Direction | Purpose |
|-----------|-----------|---------|
| `trace_chain(root, seed_id, direction)` | Inbound | Called by `trace.py` and `evidence.py` |
| `compute_chain_depth(root, seed_id)` | Inbound | Called by `artifact_lint.py` chain-report |
| `id_index` | Internal | Dict mapping artifact ID to Artifact object |
