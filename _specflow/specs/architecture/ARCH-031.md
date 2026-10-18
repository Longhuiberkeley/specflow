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
fingerprint: sha256:f38db2460a76
thinking_techniques:
- assumption_surfacing
modified: '2026-10-08'
version: 2
---

# COMP lifecycle architecture: closure gate, reversible pause, closure accounting

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-110); earlier text described a schema-enforced COMP closure gate and a "goals met" judgment in `autoresearch status`, neither of which the engine has — the closure gate is a protocol-level human gate.

## Structure

The competition lifecycle (REQ-039) has three components:

- **A protocol-level closure gate.** `competition-setup-protocol.md` (rule 5) makes COMP `active → completed` a human gate: the agent assembles the per-goal `closure_disposition` (each `goals` entry satisfied-with-FIND-citation or abandoned-with-reason), presents it with the Closure-readiness block from `specflow autoresearch status`, and only the direct user's explicit go-ahead completes the COMP; subagents never close COMPs. This mirrors the FIND `draft → confirmed` human gate in `finding-generation-protocol.md`. The engine does not enforce it: `packs/autoresearch/schemas/competition.yaml` carries a plain transition map (`active: [paused]`, `paused: [active]`, `completed: [active]`), so `specflow update COMP-N --status completed` is accepted. The engine backs the gate only with warn-only lint and read-only accounting (below).
- **A reversible paused state.** The schema's `initial_statuses: [active]` key names the creation root (honoured by `entry_statuses()` in `lib/artifacts.py`), and paused → active is legal, so pausing no longer strands a competition.
- **Deterministic closure accounting.** `specflow autoresearch status` prints a Closure-readiness block (`_render_closure_readiness`, `commands/autoresearch.py`) with the recorded goals list, confirmed / total FIND counts, the evaluation window (an advisory when `window_end` has elapsed), open `research_agenda` directions deduped across LOOPs, and a LOOP status census. It states facts only and makes no goal-met or ready-to-close judgment.

## Responsibilities

- `artifact-lint` (`_check_autoresearch_comp_closure`, check `autoresearch-comp-closure`) warns on a completed COMP with zero confirmed FINDs (`autoresearch-comp-closure/no-confirmed-find`) and on a completed COMP with no `closure_disposition` recorded (`autoresearch-comp-closure/no-disposition`). FIND→COMP association resolves through both frontmatter `competition` and `belongs_to` links (`_findings_for_comp`). Never blocking.
- The creation-status gate (STORY-640, `commands/create.py`) keeps COMP creation honest: creating directly in a status that is not an entry status requires a recorded sanction (`--sanctioned "why"`, kept as `sanctioned_justification`).
- Closure signals are computed deterministically from the artifact graph — no LLM judgment in the loop.

## Dependencies

The transition-map mechanism is shared with the autoresearch pack schema surface (ARCH-027); the ops-pack RUN pause (ARCH-033) reuses it. Implemented by STORY-650..652; verified by IT-050.
