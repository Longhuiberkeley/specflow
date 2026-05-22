# Finding Generation Protocol

Playbook for authoring and updating FIND artifacts after a LOOP completes. Read this when the agent finishes a LOOP and needs to condense experiment results into structured knowledge.

## When to Create vs Update

| Situation | Action |
|-----------|--------|
| New insight not covered by any existing FIND | Create a new FIND with `status: draft` |
| Existing FIND-NNN has new supporting evidence from this LOOP | Update FIND-NNN: add to `what_worked` or `what_failed`, raise `confidence` if warranted |
| New evidence contradicts or refines an existing confirmed FIND | Set FIND-NNN to `status: superseded`, create a new FIND with the corrected understanding |
| A confirmed FIND is actively falsified by new evidence | Set FIND-NNN to `status: falsified`, create a new FIND documenting what happened |

## Aggregation Process

After a LOOP completes, follow these steps:

### 1. Read All EXPTs in the LOOP

```bash
specflow trace LOOP-NNN
```

This shows all EXPTs with their metrics, change categories, and statuses. Alternatively, read individual EXPT artifacts filtered by `loop: LOOP-NNN`.

### 2. Group EXPTs by change_category

Count outcomes per category:

| change_category | Kept | Discarded | Crashed | Best Delta |
|-----------------|------|-----------|---------|------------|
| features | 4 | 6 | 0 | +0.8 |
| params | 2 | 3 | 1 | +0.2 |
| model | 1 | 4 | 0 | +0.4 |
| exit | 0 | 5 | 0 | 0.0 |

Categories with high kept rates drove improvement. Categories with all discards are dead ends.

### 3. Identify Key Insights

For each category that drove improvement, ask:
- What specific changes produced the best metrics?
- What was the progression? (e.g., "started with XGBoost, switched to Kalman, improved further with Q tuning")
- Are there patterns across iterations? (e.g., "smaller time windows consistently beat larger ones")

For categories that did not pan out, ask: what is the *honest* outcome? Falsifying an approach cleanly is often hard, and "it didn't work" is usually too strong. Classify each into one of:

- **falsified** — a clear, repeatable negative across parameters and seeds ("all mean-reversion variants lost money regardless of threshold")
- **conditional** — works only under stated conditions ("profitable on ETH but not ADA"; "needs >2 years of history")
- **sensitive** — the result hinges on a knob or on noise, so it can't be trusted as-is. Prefer *"sensitive to parameter/noise — 0.020 vs 0.021 flips the outcome; may or may not be useful downstream"* over *"the algorithm doesn't work."* This is a robustness statement, not a verdict.
- **inconclusive** — couldn't separate signal from the noise floor within the budget; genuinely unknown

Recording the right one of these is more useful to the next LOOP than forcing a thumbs-down. A sensitive or inconclusive result is a pointer to *where to look next*, not a dead end.

**Read `failure_analysis` and `hypothesis_outcome` from discarded and crashed EXPTs.** `failure_analysis` is the raw root-cause sentence the agent logged during Phase 7; `hypothesis_outcome` (supported / not_supported / inconclusive) says whether the Phase 2a hypothesis held. Together they make `what_failed` authoring faster and more honest. If an EXPT lacks `failure_analysis`, infer the root cause from `summary` and `parameters`.

### 4. Author the FIND

FIND-specific fields use the generic `--set KEY=VALUE` flag; only `--type`, `--title`, and `--status` are first-class.

```bash
specflow create --type finding \
  --title "Basket specialization outperforms broad baskets" \
  --status draft \
  --set competition=COMP-001 \
  --set source_loop=LOOP-001 \
  --set confidence=medium \
  --set summary="Specializing on single assets (ADA, ETH) consistently outperforms multi-asset baskets. Broad basket approaches produce noisy signals."
```

## Field Guidance

### what_worked

Concrete approaches that improved the metric. Each entry references specific EXPTs.

Example:
```
- Single-asset specialization on ADA (EXPT-005, EXPT-012)
- Kalman filter with Q=0.001 (EXPT-003, EXPT-021)
- Feature engineering: cross-asset momentum (EXPT-008, EXPT-015)
- Threshold optimization: 0.03 entry threshold (EXPT-023)
```

### what_failed

Approaches that didn't pan out, each tagged with its honest outcome (falsified / conditional / sensitive / inconclusive) and EXPT references. Future loops use this to decide what to avoid versus what to revisit differently.

Example:
```
- Trailing stops [falsified]: all variants degraded performance (EXPT-004, EXPT-009, EXPT-014)
- Threshold=0.03 entry [sensitive]: optimal at 0.030 but 0.020↔0.021 flips P&L sign — fragile, not deployable as-is (EXPT-023, EXPT-031)
- Mean-reversion on daily timeframe [conditional]: works on ETH, fails on ADA (EXPT-007, EXPT-011)
- LSTM depth sweep [inconclusive]: gains within the noise floor at this budget (EXPT-016, EXPT-018)
```

### next_steps

Suggested directions for the next LOOP. These inform the user's mode selection.

Example:
```
- Explore: try LSTM or Transformer architectures (not yet attempted)
- Exploit: tune Kalman parameters further — Q and R grids around current best
- Validate: re-run top 3 strategies on COMP-002 (walk-forward split)
```

### confidence

| Level | Criteria |
|-------|----------|
| **high** | Consistent across 2+ LOOPs. Multiple EXPTs in different change_categories confirm the finding. No contradictory evidence. |
| **medium** | Supported by one LOOP with 3+ kept EXPTs. Pattern is clear but not yet validated on a different split. |
| **low** | Based on 1-2 kept EXPTs. Preliminary — needs confirmation before relying on it for direction. |

### deployability

Not all "what worked" findings are deployable. A high-Sharpe strategy with 1,000 micro-trades per day may be "what worked" but `not_deployable` due to transaction costs. Use this field to separate "works on paper" from "works in production."

| Level | When to use |
|-------|-------------|
| **deployable** | Meets all COMP goals; post-checks pass; ready for live or production use |
| **conditional** | Promising but needs additional guard (e.g., "deployable only with <0.1% slippage") |
| **not_deployable** | Metric looks good but post-checks fail; too fragile; not cost-effective |

### safety_assessment

For `safety_critical` domains (medical, automotive, aerospace). A finding is not "confirmed" unless its safety impact is understood.

| Level | When to use |
|-------|-------------|
| **pass** | No safety regressions; meets all domain-specific thresholds |
| **conditional** | Safe under stated assumptions (e.g., "safe if training data includes demographic X") |
| **fail** | Safety regression detected; do not deploy |
| **not_applicable** | Domain is not safety-critical; field can be omitted |

## Supersession Pattern

When new evidence contradicts or refines an existing FIND:

```bash
# Mark the old finding as superseded
specflow update FIND-001 --status superseded

# Create a refined finding
specflow create --type finding \
  --title "Threshold sensitivity is knife-edge at 0.03, not robust" \
  --status draft \
  --set competition=COMP-001 \
  --set source_loop=LOOP-003 \
  --set confidence=medium \
  --set summary="LOOP-001 found threshold=0.03 optimal, but LOOP-003 shows ±0.005 variation degrades performance by 40%. The optimum is real but fragile."
```

## Cross-Loop Synthesis

A FIND can synthesize patterns across multiple LOOPs without a single `source_loop`. This is done by reading prior FINDs (not raw EXPTs) to stay within context limits.

```bash
specflow create --type finding \
  --title "Feature engineering consistently outperforms model tuning" \
  --status draft \
  --set competition=COMP-001 \
  --set confidence=high \
  --set summary="Across 4 loops and 120 experiments, adding new features produces larger metric improvements than model architecture changes. Feature-driven improvements average +0.5 per iteration vs +0.15 for model tuning."
```

Leave `source_loop` absent. The `experiment_count` and `best_metric` fields should aggregate across all referenced loops.

## Lifecycle Transitions

```
draft → confirmed    (user reviews and approves after one or more supporting LOOPs)
confirmed → superseded  (new LOOP provides refined or contradictory evidence)
confirmed → falsified   (new LOOP definitively disproves the finding)
```

The agent creates FINDs at `draft` status. The user confirms them during `/specflow-autoresearch:review`.
