# Error Analysis Protocol — Train/OOF Only

Run a result-analysis pass after a meaningful evaluation and before Phase 2
ideation. Analyze the current best using saved training-fold and out-of-fold
(OOF) predictions, labels, residuals, and strategy diagnostics. The outputs are
evidence for hypotheses and agenda revisions; they do not change the COMP
metric or prove generalization by themselves.

**The isolated final eval/test partition is NEVER read for error analysis.** Do
not load its rows or labels, slice its predictions, inspect its residuals, or
choose changes from its outcomes. Use train/OOF diagnostics and COMP-approved
development validation folds only. If the saved data does not identify its
split provenance, treat it as unavailable until verified.

## Prediction and residual review

For classification, compare OOF prediction with truth. Slice confusion counts,
precision/recall, calibration, and errors by class, meaningful segment, time,
group, and relevant feature buckets. For regression, inspect signed and absolute
residuals, tail errors, and residual patterns against time, groups, and predicted
value. Respect the COMP split: fit all diagnostic transforms on the training
fold and keep entities, time, and duplicate groups on their intended side.

Inspect the worst-k OOF errors with their prediction, truth, residual or
confidence, and available non-sensitive input context. Ask whether they share a
data-quality issue, subgroup, target ambiguity, or systematic model weakness.
Record representative IDs/paths and the observed pattern, not a cherry-picked
score. Do not silently exclude hard rows or turn this review into eval-set
tuning.

## Strategy and P&L attribution

For quant or other strategy COMPs, attribute train/OOF P&L and risk to trades,
positions, exposure, entry/exit decisions, transaction costs, and drawdown
contributors. Tag outcomes with the COMP-relevant volatility, trend, liquidity,
and market-regime buckets. Compare net and gross contributions where available;
separate a broad improvement from a gain concentrated in one regime. Use only
the train/OOF or COMP-approved validation-window diagnostics, never the isolated
final eval partition.

## Feed Phase 2

Persist a concise diagnostic artifact or logged path and summarize:

1. the slice and split provenance;
2. the repeatable error or attribution pattern;
3. what observation would falsify the explanation;
4. the next formulation and expected metric effect.

If analysis itself is the iteration, log an EXPT with
`status: no_op`, `change_category: analysis`, and a complete `research_progress`
whose `evidence_ref` anchors to that EXPT (or to its recorded commit/output path).
The distinct finding and `next_decision` preserve the result for later ideation;
an analysis-only EXPT is not a metric attempt and is excluded from evidence-free
streak windows.
