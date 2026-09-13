# Finding Generation — Invariants

Condense a completed LOOP's EXPTs into FIND artifacts. Start from
`specflow autoresearch suggest-finds --loop LOOP-NNN` (add `--write` to create
the draft) — the CLI groups EXPTs by `change_category` and pre-populates
`what_worked` / `what_failed`; edit the draft rather than writing from scratch.
For small loops (<10 EXPTs) authoring directly is fine.

## Create vs update map

| Situation | Action |
|-----------|--------|
| New insight not covered by any existing FIND | Create a new FIND at `status: draft` |
| Existing FIND-NNN gains supporting evidence | Update it: extend `what_worked`/`what_failed`, raise `confidence` if warranted |
| New evidence contradicts or refines a confirmed FIND | `specflow update FIND-NNN --status superseded`, create the corrected FIND |
| New evidence definitively disproves a confirmed FIND | `specflow update FIND-NNN --status falsified`, create a FIND documenting it |

```bash
specflow create --type finding \
  --title "Feature engineering outperforms model tuning" \
  --status draft \
  --set competition=COMP-001 \
  --set source_loop=LOOP-001 \
  --set confidence=medium \
  --set summary="Tenure/usage features drove the largest gains; model changes had minimal impact."
```

Lifecycle: `draft → confirmed` (user gate) · `confirmed → superseded | falsified`.

## Hard invariants

1. **`FIND draft → confirmed` is a human gate.** The agent (and any review subagent) drafts FINDs and presents the supporting EXPT evidence and confidence; only the direct user's explicit confirmation promotes a FIND. EXPT metrics are evidence, not approval.
2. **Honest outcomes on `what_failed`.** Tag each entry `falsified` (clear repeatable negative) / `conditional` (works only under stated conditions) / `sensitive` (hinges on a knob or noise — a robustness statement, not a verdict) / `inconclusive` (inside the noise floor at this budget). A sensitive or inconclusive result points where to look next; don't force a thumbs-down.
3. **Evidence is cited.** `what_worked` / `what_failed` reference specific EXPTs and name the `COMP.theses` entry they support or refute. Read `failure_analysis` and `hypothesis_outcome` from discarded/crashed EXPTs — that pairing is what makes `what_failed` fast and honest.
4. **Confidence is calibrated.** high = consistent across 2+ LOOPs, multiple confirming EXPTs, no contradictions; medium = one LOOP with 3+ kept EXPTs; low = 1–2 kept EXPTs. A `what_worked` selected as best-of-many EXPTs is capped at medium until confirmed on a fresh seed or held-out slice (multiple-comparisons bias).
5. **`deployability` separates paper from production** (`deployable` / `conditional` / `not_deployable`); a deployable FIND with `confidence` ≥ medium is promoted to a core REQ via `/specflow-discover`, linked `derives_from` the FIND (see `protocol-integrations.md`). `safety_assessment` is required in safety-critical domains.
6. **Cross-loop synthesis is triggered, not optional:** 2+ completed LOOPs ⇒ one comparison FIND; 3+ ⇒ a state-of-the-COMP FIND; a low-confidence FIND 2+ LOOPs old ⇒ re-evaluate; 100+ cumulative EXPTs ⇒ a meta-analysis FIND. Cross-loop FINDs omit `source_loop` and read prior FINDs, not raw EXPTs.

## Signals worth surfacing

Auxiliary metrics moving while the primary is flat, or contradicting it (gaming); progression shape (step-function / gradual / oscillation / saturation → different `next_steps`); never-tried theses, category pairs, or parameter regions; `design_quality` trends (mostly 1–2 ⇒ lower all confidence; high-quality disagreement ⇒ document the uncertainty).
