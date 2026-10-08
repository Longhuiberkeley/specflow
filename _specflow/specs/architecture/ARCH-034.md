---
id: ARCH-034
title: Autoresearch evidence/priority model and reassessment semantics
type: architecture
status: approved
rationale: Coverage structural gap for REQ-043 (shipped behavior documented retrospectively).
suspect: false
links:
- target: REQ-043
  role: derives_from
created: '2026-09-21'
fingerprint: sha256:8c18da8a2938
modified: '2026-10-08'
thinking_techniques:
- assumption_surfacing
---

## Rationale
Coverage structural gap for REQ-043 (retrospective architecture record; the behavior shipped with the STORY-665 implementation). The change has three structural pieces: the CLI reassessment signal, the schema-level evidence/priority fields, and the skill/protocol surfaces that consume them. The reassessment predicate is bounded to the recent window so progress must be recent, anchored, and novel — counts and outcome labels are accounting, not evidence.

## Components

- **Evidence axis (EXPT).** `hypothesis_outcome` carries the evidence about the tested formulation: `supported` / `not_supported` (scoped falsification) / `inconclusive` / `invalid` (invalid instrument). Value set is documented on `experiment.yaml`; `artifact-lint` requires `failure_analysis` alongside `invalid`.
- **Progress record (EXPT).** Optional `research_progress` (`{evidence_ref, finding, next_decision}`, all non-empty) is the structured claim the reassessment reads. `evidence_ref` anchors narrowly to the current EXPT: the ID exactly or with an explicit `#fragment` (a longer ID is a different experiment); the recorded `commit` exactly or as a ≥7-character hex abbreviation (`commit:` alone never matches); or a repo-relative output path the record logs outside the progress note itself and that exists. The finding/ref must not repeat earlier records; existence, anchor, and novelty are checked, never truth. One validated producer: `autoresearch log --research-progress '<json>'`.
- **Priority axis (LOOP `research_agenda[]`).** `priority` (`pursue` / `deprioritize` / `blocked` / `revisit`) and `progress` (new evidence + next decision) are decisions, separate from evidence. Open-direction rendering excludes `deprioritize`/`blocked`; `revisit` stays open. No priority is derived from a failure count.
- **Reassessment signal (`specflow autoresearch status`).** Deterministic accounting reads the consecutive same-category tail and the consecutive non-kept tail over a bounded recent window (the last three affected experiments). It warns (exit 3) only when that window produced no meaningful progress: either an anchored, distinct `research_progress` note or a keep with a new best primary `metric_value` per `COMP.metric_direction` (a finite, correctly signed `delta` only when no comparable metric exists; non-finite numbers never count). Outcome labels alone, repeated claims/refs, malformed or absent records, and keeps outside the window count for nothing. Presence of the `research_agenda` is checked; its direction count is not a gate, and a prioritized direction without `progress` is an advisory (exit stays 0).
- **Review boundary.** One investigator drives the loop and writes the deterministic log; independent review is an optional boundary pass (platform delegation or the same sequential walk), never a required stage.

## Data Flow

Agenda reasoning (Phase 0.7, before the baseline dry-run) → EXPT hypothesis and outcome → `autoresearch log` (optional `research_progress`) → LOOP counters → `status` recent-window reassessment signal → direction `priority`/`progress` → next LOOP's `knowledge_input` and the condensation briefs.

## Dependencies

- `src/specflow/commands/autoresearch.py` (reassessment window/progress predicates, strict evidence anchoring, open-direction view, printed protocol, `--research-progress` producer)
- `src/specflow/commands/artifact_lint.py` (outcome vocabulary, `invalid` failure-analysis pairing, malformed `research_progress` shape advisory)
- autoresearch pack schemas (`loop.yaml`, `experiment.yaml`) and skill references
- Arch-034 depends on no external service; the signal is deterministic and zero-token.

## Tradeoffs

- The evidence proxy stays deliberately coarse (an anchored, novel progress note or a measured new best) so it remains deterministic and cheap; richer judgments stay in the protocol prose where the agent can explain them. It asserts existence, anchor, and novelty — never truth.
- Legacy/unannotated EXPTs are read conservatively (warn when a ≥3 tail shows no measurable keep), which is the intended cost of removing label-based optimism.
- Keeping `status: exhausted` as a possible lifecycle state but requiring recorded progress preserves legacy artifacts while removing count-driven kills.
