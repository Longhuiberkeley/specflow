# EDA Lenses — Applicable, Evaluation-Isolated

Use this reference during Phase 0.6 before modeling. These are diagnostic lenses,
not quality gates; record what was examined and any agenda change in
`LOOP.eda_summary` and `LOOP.research_agenda`. The status command reports
not-applicable for a domain without a registered lens.

## Evaluation boundary

Diagnose leakage and distribution shift within the COMP's permitted evaluation
context: its training folds compared with validation folds, walk-forward windows,
and train/OOF diagnostics produced by `verify_command`. These are the evaluation
data views used to estimate generalization. Never open, query, plot, or otherwise
read an isolated final eval/test partition to select features, explain a result,
or revise the agenda. If the COMP exposes only a locked final partition, use
training/OOF diagnostics and the one-number verify result; do not inspect the
partition itself.

## Core lenses

- **Leakage and split integrity** — Inspect feature provenance, target-derived
  fields, point-in-time availability, duplicates, group overlap, and transforms
  fitted across fold boundaries. Use the COMP-approved split and training-fold
  fit scope. Check whether train/validation separability suggests a split or
  leakage problem using only permitted fold data.
- **Distribution shift** — Compare train and validation-fold feature summaries
  (missingness, ranges, categorical support, and time/group composition). For
  adversarial validation, train a classifier to distinguish training rows from
  COMP-approved validation rows; interpret high separability as a shift/leakage
  lead to investigate, not as proof. Never use the isolated final eval partition.
- **Class imbalance** — Report label counts and proportions by training fold,
  validation fold, and meaningful group/time slices. Check that the metric and
  split preserve the minority cases relevant to the COMP objective. Do not
  rebalance or resample across a fold boundary.
- **Target noise** — Inspect train/OOF prediction-versus-truth residuals, label
  disagreement, ambiguous classes, and target concentration. Record the affected
  slice and uncertainty; do not relabel against an isolated eval set.

## Domain lenses

- **`tabular_ml`** — Apply leakage, fold shift, class-imbalance, and target-noise
  lenses; include group/time structure and target proxies.
- **`vision`** — Apply leakage and fold-shift lenses to near-duplicates, source
  sites, acquisition conditions, and preprocessing; inspect class counts and
  train/OOF error slices for annotation noise.
- **`nlp`** — Apply leakage and fold-shift lenses to duplicates, templates,
  language, length, source, and temporal structure; inspect class balance and
  train/OOF disagreement for label noise.
- **`quant`** — Apply point-in-time and survivorship leakage checks, walk-forward
  distribution comparisons, and volatility/regime buckets. Summarize metric
  behavior by volatility, trend, liquidity, and other COMP-relevant regimes
  using only permitted training/validation windows.

## Quick tier

For a LOOP with budget ≤ 5, prioritize split/leakage integrity and the one or two
domain lenses most likely to invalidate the baseline. State the reduced coverage
in `eda_summary`; do not replace these lenses with a numbered checklist.
