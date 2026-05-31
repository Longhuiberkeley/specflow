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

Concrete approaches that improved the metric. Each entry references specific EXPTs. **Where possible, name the `COMP.theses` entry the evidence supports** — this is how theses accumulate evidence over loops.

Example:
```
- Single-asset specialization on ADA (EXPT-005, EXPT-012) — supports thesis: "basket narrowing improves Sharpe on this universe"
- Kalman filter with Q=0.001 (EXPT-003, EXPT-021) — supports thesis: "Kalman filters outperform OLS on intraday bars"
- Feature engineering: cross-asset momentum (EXPT-008, EXPT-015) — supports thesis: "cross-asset regime signals lift Sharpe"
- Threshold optimization: 0.03 entry threshold (EXPT-023) — no thesis link (parameter-level finding)
```

### what_failed

Approaches that didn't pan out, each tagged with its honest outcome (falsified / conditional / sensitive / inconclusive) and EXPT references. **Where the evidence refutes or refines a `COMP.theses` entry, name it.** Future loops use this to decide what to avoid versus what to revisit differently, and to retire theses that no longer earn their keep.

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

## Auxiliary Metric Synthesis

Auxiliary metrics are logged on every EXPT but are rarely analyzed systematically. This section ensures they don't get buried.

### When to Synthesize Auxiliary Metrics

Auxiliary metrics matter when:

1. **Primary is flat but auxiliary moves.** This is the canonical buried signal. A LOOP could produce 50 EXPTs where Sharpe (primary) is flat but max drawdown steadily decreases. The primary-only view says "no progress"; the auxiliary view says "the strategy is getting safer."

2. **Auxiliary trend contradicts primary.** If the primary metric improves but an auxiliary metric degrades (e.g., accuracy up but calibration down), the improvement may be gaming the metric. Flag this in `what_failed` as a `conditional` finding.

3. **Auxiliary metrics converge to a stable regime.** Even without primary improvement, convergence (e.g., trade count stabilizing, runtime decreasing, memory usage plateauing) indicates the system is finding a stable operating point — useful for production readiness.

### Analysis Method

For each auxiliary metric tracked across >=5 EXPTs:

1. **Correlation with primary:** Spearman rank correlation. Co-moving metrics are redundant (consider dropping). Orthogonal metrics provide independent signal.
2. **Trend detection:** Simple linear regression on the auxiliary metric vs iteration number. Significant slope (p<0.05) → trend worth surfacing.
3. **Breakpoint detection:** Did the auxiliary metric shift at a specific EXPT? That EXPT may have had side effects invisible to the primary metric.

**Tag findings from auxiliary metrics with source: `auxiliary_metric`** so the next LOOP knows this insight came from secondary analysis, not primary verification.

### Mandatory Cross-Loop Synthesis Triggers

Certain conditions REQUIRE a cross-loop synthesis FIND regardless of whether the agent thinks one is needed:

| Trigger | Action |
|---------|--------|
| 2+ completed LOOPs on the same COMP | Create at least one synthesis FIND comparing the two LOOPs (what changed, what stayed the same) |
| 3+ completed LOOPs on the same COMP | Create a "state of the COMP" FIND summarizing cumulative knowledge, remaining unknowns, and recommended next direction |
| A FIND with `confidence: low` is now 2+ LOOPs old | Re-evaluate: has new evidence raised or lowered confidence? Update the FIND or supersede it. Low-confidence findings that are old are stale — they represent uncertainty that may have been resolved without being captured. |
| A `what_worked` finding from >3 LOOPs ago has never been reproduced | Flag as `confidence: low` with note: "Not reproduced since LOOP-NNN." The finding may be specific to a stale code snapshot. |
| Cumulative EXPT count across all LOOPs exceeds 100 | Create a meta-analysis FIND: which change_categories delivered ROI, which are saturated, what's the overall trajectory |

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

## Cross-EXPT Pattern Detection

Before authoring FINDs for this LOOP, scan for patterns that single-axis (per-category) grouping misses. These are meta-signals worth surfacing as separate FINDs or enriching existing ones.

### 1. Cross-Category Interaction Detection

Some categories amplify or cancel each other. Check:

- **Synergistic pairs:** Did EXPTs in category A perform better when preceded by a kept EXPT in category B? (e.g., model architecture changes only helped AFTER feature engineering was done)
- **Antagonistic pairs:** Did one category's success undo another's? (e.g., regularization improvements erased gains from a previous feature engineering EXPT)
- **Sequencing effects:** Did the ORDER of changes matter? (e.g., "normalization first, then architecture" worked but "architecture first" didn't)
- **Cross-category patterns:**
  - File-level: Which files appeared in kept EXPTs across multiple categories? (likely core leverage points)
  - Complexity: Did complexity increase with improvement, or did simpler changes win?
  - Temporal: Did improvement cluster in early iterations (low-hanging fruit) or was it steady?
  - Budget-efficiency: Which categories delivered the most improvement per iteration?

### 2. Progression Shape Analysis

Look at the metric trajectory across iterations within this LOOP:

- **Step-function:** Metric jumped and stayed flat → a single high-leverage change was found early
- **Gradual improvement:** Metric trended up steadily → cumulative small wins
- **Oscillation:** Metric went up and down → high noise floor, or competing changes undoing each other
- **Saturation:** Metric improved then plateaued → diminishing returns on the current approach

The progression shape informs `next_steps`: step-function → search for the next lever. Gradual → keep going in same direction. Oscillation → increase noise handling. Saturation → switch approach or mode.

### 3. Negative-Space Analysis

What was NEVER tried? This is as important as what worked:

- **Untried theses:** Which `COMP.theses` entries were never tested this LOOP? Why?
- **Untried category pairs:** Are there combinations of `change_category` values that were never co-tested?
- **Unexplored parameter regions:** Did all parameter sweeps stay in the same region? Is there a completely different part of the parameter space worth probing?
- **Budget allocation vs return:** Did the LOOP spend 80% of iterations on a category that produced 10% of improvement?

### 4. Design Quality Trends

Aggregate `design_quality` scores (from Phase 6.6) across the LOOP:
- If most EXPTs score 1-2 (Flawed/Invalid), the LOOP's knowledge is unreliable — lower confidence on all FINDs
- If high-quality EXPTs (3-4) consistently point one way, increase confidence
- If high-quality EXPTs disagree, that's a GENUINE uncertainty — document it, don't force consensus

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
