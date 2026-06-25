# Machine Learning Domain Checklist

Questions for model-training, fine-tuning, and ML-feature projects. Like quant, ML splits into *software you can specify* (pipelines, no-leakage, reproducibility) and *quality you can only measure* (accuracy, generalisation) — use the map.

## Concept → Artifact Map (ml)

| Concept | Right artifact | Why |
|---|---|---|
| Target accuracy / F1 / loss | **autoresearch goal + metric** (`COMP.metric_name`) | A measured outcome, not testable software behaviour. Never a REQ. |
| "No train/test leakage" / feature-pipeline correctness | **REQ** (non-functional) + `leakage_audit` lens | Testable property of the code. |
| Seed control / deterministic training / reproducibility | **REQ** + EXPT fingerprinting | Verifiable; runs must re-produce. |
| Data ingestion / feature / training pipeline code | **STORY** (implements) + **ARCH** (the component) | Implementable work and structure. |
| A single training run (hparams + result) | **EXPT** (autoresearch) | Frozen, reproducible result. |
| A model going to production | **RUN** (ops pack) | Deployment frozen at deploy-time; `derives_from` the EXPT it promotes. |
| Accuracy / input-drift over time | **MONITOR** (ops pack) with `signals` | Append-only journal; input drift and latency are signal types. |
| "Retrain when val_loss / drift > X" | **REQ** (threshold) + MONITOR breach → new LOOP | Specifiable threshold fired via monitoring. |

*Can you write a test that fails if it's wrong?* → REQ/STORY/EXPT. *A number you're moving?* → autoresearch metric. *Only exists while running?* → RUN/MONITOR.

## Data & Features

1. **Train/val/test split?** "Three-way, with the test set touched exactly once? Group/time-aware split to prevent leakage?"
2. **Label leakage?** "Does any feature encode the label or use future info (e.g. normalisation fit on all data)? Map anti-leakage to a REQ + `leakage_audit`."
3. **Class balance / distribution?** "Imbalanced? Weighting, resampling, or threshold tuning strategy?"
4. **Feature store?** "Online vs offline features; are train and serve feature pipelines identical (training/serving skew)?"

## Training & Evaluation

5. **Metric & direction?** "Primary metric (`COMP.metric_name`/`metric_direction`) plus auxiliary metrics (val_loss, etc.)? Optimise one, guard the rest."
6. **Baseline sanity?** "Is there a trivial baseline (majority class, linear) beaten before claiming success? (`baseline_sanity` lens.)"
7. **Overfitting guard?** "Hyperparameter search budget accounted for? Held-out test used once? (`overfitting_multiple_comparisons` lens.)"
8. **Reproducibility?** "Fixed seeds, pinned deps, recorded hparams — can a fresh agent re-run the EXPT and get the same number?"

## Deployment & Monitoring

9. **What goes live?** "Which model, environment, from which EXPT, satisfying which REQ? → a **RUN** (ops pack)."
10. **What do you monitor?** "Live accuracy vs validation, latency, and **input/prediction drift** (distribution shift). → periodic **MONITOR** entries (`distribution_shift` lens for the analysis)."
11. **Retrain / rollback triggers?** "Drift or accuracy threshold that triggers a retrain (new LOOP) or rollback (retire the RUN)? Make the threshold a REQ."
