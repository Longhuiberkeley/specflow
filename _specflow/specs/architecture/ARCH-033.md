---
id: ARCH-033
title: 'Ops RUN lifecycle architecture: reversible pause'
type: architecture
status: approved
rationale: Architecture record for REQ-041 (coverage structural gap; shipped behavior
  documented retrospectively).
suspect: false
links:
- target: REQ-041
  role: derives_from
created: '2026-09-13'
fingerprint: sha256:cd8de45116b1
thinking_techniques:
- assumption-surfacing
modified: '2026-09-13'
---

# Ops RUN lifecycle architecture: reversible pause

## Structure

The ops pack `run.yaml` transition map grants `live: [deployed, paused]` so paused → live is a legal RUN transition (REQ-041): deployed remains the sole creation root, live already carries a predecessor, and retired stays terminal. No `initial_statuses` key is required — the ops case is strictly simpler than the autoresearch COMP fix it mirrors.

## Responsibilities

- The schema change grants legality, not authority: every transition into live stays user-gated per the ops skill doctrine, including resuming a paused RUN.
- The ops skill's RUN status line reflects reversibility without weakening the frozen-at-deploy doctrine.

## Dependencies

The transition-map mechanism and its test pattern shipped with STORY-652 (ARCH-031). Implemented by STORY-655; pinned by tests/test_ops_pack.py.
