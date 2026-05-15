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

For categories that failed, ask:
- What approaches were definitively falsified?
- Is there a common thread? (e.g., "all mean-reversion approaches failed regardless of parameters")

### 4. Author the FIND

```bash
specflow create --type finding \
  --title "Basket specialization outperforms broad baskets" \
  --competition COMP-001 \
  --source-loop LOOP-001 \
  --confidence medium \
  --status draft \
  --summary "Specializing on single assets (ADA, ETH) consistently outperforms multi-asset baskets. Broad basket approaches produce noisy signals."
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

Falsified approaches with references. Future loops should avoid these.

Example:
```
- Trailing stops: all variants degraded performance (EXPT-004, EXPT-009, EXPT-014)
- Mean-reversion on daily timeframe (EXPT-007, EXPT-011)
- XGBoost with default parameters on this dataset (EXPT-001)
- Ensemble methods: marginal improvement with 3x complexity cost (EXPT-016, EXPT-018)
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

## Supersession Pattern

When new evidence contradicts or refines an existing FIND:

```bash
# Mark the old finding as superseded
specflow update FIND-001 --status superseded

# Create a refined finding
specflow create --type finding \
  --title "Threshold sensitivity is knife-edge at 0.03, not robust" \
  --competition COMP-001 \
  --source-loop LOOP-003 \
  --confidence medium \
  --status draft \
  --summary "LOOP-001 found threshold=0.03 optimal, but LOOP-003 shows ±0.005 variation degrades performance by 40%. The optimum is real but fragile."
```

## Cross-Loop Synthesis

A FIND can synthesize patterns across multiple LOOPs without a single `source_loop`. This is done by reading prior FINDs (not raw EXPTs) to stay within context limits.

```bash
specflow create --type finding \
  --title "Feature engineering consistently outperforms model tuning" \
  --competition COMP-001 \
  --confidence high \
  --status draft \
  --summary "Across 4 loops and 120 experiments, adding new features produces larger metric improvements than model architecture changes. Feature-driven improvements average +0.5 per iteration vs +0.15 for model tuning."
```

Leave `source_loop` absent. The `experiment_count` and `best_metric` fields should aggregate across all referenced loops.

## Lifecycle Transitions

```
draft → confirmed    (user reviews and approves after one or more supporting LOOPs)
confirmed → superseded  (new LOOP provides refined or contradictory evidence)
confirmed → falsified   (new LOOP definitively disproves the finding)
```

The agent creates FINDs at `draft` status. The user confirms them during `/specflow-autoresearch:review`.
