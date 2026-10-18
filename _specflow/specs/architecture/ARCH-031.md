---
id: ARCH-031
title: 'COMP lifecycle architecture: closure gate, reversible pause, closure accounting'
type: architecture
status: approved
rationale: Architecture record for REQ-039 (coverage structural gap; shipped behavior
  documented retrospectively).
suspect: false
links:
- target: REQ-039
  role: derives_from
created: '2026-09-13'
fingerprint: sha256:3a264155235a
thinking_techniques:
- assumption_surfacing
modified: '2026-10-08'
version: 1
---

# COMP lifecycle architecture: closure gate, reversible pause, closure accounting

## Structure

The competition lifecycle (REQ-039) has three components: a closure gate on the `competition` schema (active → completed requires every `goals` entry satisfied-with-confirmed-FIND-evidence or explicitly abandoned-with-reason, plus direct-user confirmation — no self-approval, mirroring the FIND gate), a reversible paused state (the `initial_statuses` schema key names the creation roots; paused → active is legal, so pausing no longer strands a competition), and deterministic closure accounting in `specflow autoresearch status` (goals met, confirmed FINDs, open agenda directions).

> Amended 2026-10-18 (SPIKE-008 R1-110): the `competition` schema carries no closure gate; its transition map allows active → completed (packs/autoresearch/schemas/competition.yaml:51). The closure gate is a protocol-level human gate (references/competition-setup-protocol.md), backed by warn-only lint (`_check_autoresearch_comp_closure`) and the read-only closure accounting in `specflow autoresearch status`. `specflow update COMP-N --status completed` is not refused by the engine.

## Responsibilities

- `artifact-lint` warns on a completed COMP with zero confirmed FINDs, resolving FIND→COMP via both frontmatter `competition` and `belongs_to` links.
- The creation-status gate keeps COMP creation honest: creating directly in a non-root status requires a recorded sanction.
- Closure signals are computed deterministically from the artifact graph — no LLM judgment in the loop.

## Dependencies

The transition-map mechanism is shared with the autoresearch pack schema surface (ARCH-027); the ops-pack RUN pause (ARCH-033) reuses it. Implemented by STORY-650..652.
