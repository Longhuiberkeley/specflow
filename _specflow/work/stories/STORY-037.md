---
id: STORY-037
title: Add trace command and chain-report lint check
type: story
status: verified
priority: high
tags:
- traceability
- cli
- reporting
suspect: false
links:
- target: REQ-007
  role: implements
- target: DDD-001
  role: specified_by
- target: UT-001
  role: verified_by
- target: IT-006
  role: verified_by
- target: QT-009
  role: verified_by
created: '2026-04-20'
modified: '2026-04-22'
fingerprint: sha256:ddc227e4eb50
---

# Add trace command and chain-report lint check

## Description

Implement two CLI capabilities: (1) `specflow trace <ID>` that displays the full traceability chain for an artifact as an indented tree, and (2) `specflow artifact-lint --type chain-report` that produces a survey of chain depth distribution across all approved artifacts. Both treat depth as informational data, not errors.

## Acceptance Criteria

1. Given REQ-001 with upstream links to ISO-26262 and downstream links from ARCH-001 and QT-001, when running `specflow trace REQ-001`, then upstream links display with role `complies_with`/`derives_from` and downstream links display with roles `derives_from`/`implements`/`verified_by` in an indented tree format

2. Given a project with approved REQ, ARCH, and DDD artifacts, when running `specflow artifact-lint --type chain-report`, then the output shows a chain depth distribution summary with informational language and the command exits with code 0 (never causes exit code 1)

3. Given the `cli.py` argument parser, when inspecting registered subcommands, then both `trace` and `chain-report` are listed as valid commands/checks

4. Given the `lib/artifacts.py` module, when `trace_chain("REQ-001", id_index)` is called with a multi-hop upstream chain, then the BFS traversal follows derives_from/complies_with links beyond one hop

## Out of Scope

- Graph visualization or DOT output
- Exporting trace chains to files
- Transitive suspect flag propagation

## Dependencies

- REQ-007 must be approved
- `lib/artifacts.py` Link and Artifact dataclasses must exist
