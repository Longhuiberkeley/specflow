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
fingerprint: sha256:c1710dbcd31b
thinking_techniques:
- assumption-surfacing
modified: '2026-09-13'
---

# COMP lifecycle architecture: closure gate, reversible pause, closure accounting

## Structure

The competition lifecycle (REQ-039) has three components: a closure gate on the `competition` schema (active → completed requires every `goals` entry satisfied-with-confirmed-FIND-evidence or explicitly abandoned-with-reason, plus direct-user confirmation — no self-approval, mirroring the FIND gate), a reversible paused state (the `initial_statuses` schema key names the creation roots; paused → active is legal, so pausing no longer strands a competition), and deterministic closure accounting in `specflow autoresearch status` (goals met, confirmed FINDs, open agenda directions).

## Responsibilities

- `artifact-lint` warns on a completed COMP with zero confirmed FINDs, resolving FIND→COMP via both frontmatter `competition` and `belongs_to` links.
- The creation-status gate keeps COMP creation honest: creating directly in a non-root status requires a recorded sanction.
- Closure signals are computed deterministically from the artifact graph — no LLM judgment in the loop.

## Dependencies

The transition-map mechanism is shared with the autoresearch pack schema surface (ARCH-027); the ops-pack RUN pause (ARCH-033) reuses it. Implemented by STORY-650..652.
