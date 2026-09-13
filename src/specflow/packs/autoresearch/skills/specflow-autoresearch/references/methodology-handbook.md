# ML Methodology Handbook — Invariants

Best practices for ML/experimental work, consulted live during Phase 2 ideation —
pull the group matching the change, don't read end-to-end. Tiering: **ML-01/ML-02
mandatory** (enforced by the loop protocol's Phase 0.6 EDA and Phase 0.7 agenda),
**ML-05/ML-07 gated** (diversity gate / agenda ranking), the rest advisory.
Breadth comes from the Phase 0.7 agenda in `domain-research-checklists.md` and
mode behavior in `explore-exploit-protocol.md`; this file is the depth lens.

## Goal: generalization, not the leaderboard

`verify_command` is a proxy for a real-world goal. **Transfer filter:** keep
robust CV matched to data structure, leakage hygiene, adversarial validation,
feature engineering/calibration, diverse ensembles + seed averaging; avoid
leaderboard probing, eval-set leaks, split-tuned post-processing, ensembles too
heavy to run live. If a tactic raises `metric_value` without raising the goal, it
is metric-gaming (premise check), not progress.

## Domain fit gate

Each practice lists `applies_to` domains — only apply practices tagged for your
`COMP.domain`: `quant` · `tabular_ml` · `vision` · `nlp`.

## Foundations (ML-01–09)

- **ML-01: EDA before modeling** [MANDATORY] — applies_to: all. Distribution, missingness, cardinality, imbalance, temporal structure before touching a model.
- **ML-02: Strong baseline first** [MANDATORY] — applies_to: all. Simplest reasonable baseline tested and recorded before anything fancy.
- **ML-03: Trust your CV, not the leaderboard** — applies_to: all. Leaderboard is a sanity check, not the objective.
- **ML-04: Match CV scheme to data structure** — applies_to: `quant`, `tabular_ml`. Time-series ⇒ walk-forward/embargoed; groups ⇒ group-aware.
- **ML-05: Feature engineering over architecture** [GATED] — applies_to: `tabular_ml`, `quant`. Spend features budget before model budget.
- **ML-06: Model family by modality** — applies_to: all. GBDT for tabular/quant; CNN/ViT for vision; transformers for text — deviate with justification.
- **ML-07: Advanced techniques late** [GATED] — applies_to: all. Ensembling/stacking/pseudo-labeling/TTA are finishing moves, after one strong model.
- **ML-08: Characterize noise before trusting a delta** — applies_to: all. If run-to-run stdev exceeds the claimed improvement, the delta is noise.
- **ML-09: Never tune on the test split** — applies_to: all. Test is a one-time honesty check; any decision informed by it contaminates it.

## Validation integrity (ML-10–12)

- **ML-10: Split first, preprocess second** — applies_to: all. Every transform (scaler, imputer, encoder, SMOTE, PCA, selection) fit on the training fold only.
- **ML-11: Adversarial validation** — applies_to: all. Train train-vs-test classifier; AUC ≈ 0.5 ⇒ CV trustworthy, AUC → 1.0 ⇒ shift/leak suspects found.
- **ML-12: Out-of-fold for any meta-step** — applies_to: `tabular_ml`, `quant`. Target encoding and stacking consume OOF predictions, never in-fold.

## Statistical traps (ML-13–16)

- **ML-13: Correct for multiple comparisons** — applies_to: all. Best-of-N is upward-biased; confirm a marginal winner on a fresh seed or held-out slice (LOOP-level counterpart of ML-08).
- **ML-14: Mind dimensionality** — applies_to: `tabular_ml`, `quant`. p ≫ n and multicollinearity distort fits and importances; drive regularization/reduction choices, not just EDA.
- **ML-15: Distribution shift & non-stationarity** — applies_to: `quant`, `tabular_ml`. Pair walk-forward (ML-04) with adversarial validation (ML-11); prefer regime-robust features.
- **ML-16: Simpson's paradox & confounding** — applies_to: all. Check key results per segment, not just globally; a global score can move opposite to its components.

## Optimize the real objective (ML-17–19)

- **ML-17: Optimize the eval metric, then post-process for it** — applies_to: all. Threshold for F1, rank-average for AUC, calibrate for log-loss — chosen on validation (ML-09).
- **ML-18: Calibrate probabilities when decisions depend on them** — applies_to: `quant`, `tabular_ml`. Good ranking ≠ calibrated; check reliability, not only AUC.
- **ML-19: Decompose multi-output targets** — applies_to: all. Record each component (`component_<name>` auxiliary metrics); improving one by trading off another is rarely progress.

## Finishing moves (ML-20–22) — only after ML-07

- **ML-20: Ensemble diverse models** — applies_to: all. Lift scales with uncorrelated errors, not member count.
- **ML-21: Seed averaging / bagging** — applies_to: all. Cheap variance reduction; don't ship a single-seed result inside its own spread.
- **ML-22: Pseudo-labeling / semi-supervised** — applies_to: `tabular_ml`, `vision`, `nlp`. Amplifies existing bias; gate behind leak-free validation and confidence thresholds.

## Bias catalog

| Bias | Tell | Fix |
|------|------|-----|
| Selection | Sample unrepresentative of serve-time population | Define the target population; sample/weight to match |
| Survivorship | Dead/delisted/failed cases missing | Point-in-time data including entities as they were |
| Look-ahead / data-snooping | Metric improbably high; features use future info | Strict temporal cutoffs; features from the past only |
| Confirmation (ideation) | Only testing variants of the liked hypothesis | Explore mode tests the opposite; read `what_failed`; diversity gate + idea-diversity check |
| Label leakage | Feature proxies for or is computed from the target | Audit feature provenance; drop what wouldn't exist at prediction time |
