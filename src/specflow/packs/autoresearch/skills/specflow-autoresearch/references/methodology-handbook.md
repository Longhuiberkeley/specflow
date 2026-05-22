# ML Methodology Handbook

Canonical best practices for ML/experimental work. Advisory only — not enforced.

## Domain Fit Gate

Each practice lists `applies_to` domains. Only apply practices tagged for your `COMP.domain`. Forcing vision BPs onto a quant COMP wastes time.

| Domain | Tag |
|--------|-----|
| Quantitative trading | `quant` |
| Tabular ML | `tabular_ml` |
| Computer vision | `vision` |
| NLP / text | `nlp` |

---

## BP-01: EDA Before Modeling

**applies_to:** all

Understand your data before touching a model. Distribution shapes, missingness patterns, cardinality, target imbalance, and temporal structure dictate every downstream choice. Skipping EDA means discovering leakage or drift after burning budget.

**Anti-pattern:** Jumping to a neural net on day one without checking if the target has 95% class imbalance.

## BP-02: Strong Baseline First

**applies_to:** all

Implement the simplest reasonable baseline before anything fancy. Buy-and-hold (quant), majority class or global mean (tabular), pretrained model zero-shot (vision/nlp). If your sophisticated approach barely beats trivial, the problem is either too easy or your approach isn't helping.

**Anti-pattern:** Training a transformer for 3 days before checking that logistic regression gets 94% accuracy.

## BP-03: Trust Your CV, Not the Leaderboard

**applies_to:** all

Your cross-validation score is your honest signal. Public leaderboard is a small sample and overfitting it is the canonical failure mode. Optimize CV; use leaderboard only as a sanity check.

**Anti-pattern:** Chasing leaderboard score improvements that fall outside your CV error bars.

## BP-04: Match CV Scheme to Data Structure

**applies_to:** `quant`, `tabular_ml`

Time-series data needs walk-forward or embargoed splits, not k-fold. Group-structured data needs group-aware splits. Random shuffling when there's temporal or group dependency creates bogus validation scores.

**Anti-pattern:** Using StratifiedKFold on stock returns with temporal autocorrelation.

## BP-05: Feature Engineering Over Architecture

**applies_to:** `tabular_ml`, `quant`

On tabular data, handcrafted features with domain knowledge dominate architectural innovations. GBDT with good features beats deep learning with raw features. Spend features budget before model budget.

**Anti-pattern:** Trying 15 neural architectures before encoding basic domain signals (e.g., rolling z-scores, interaction terms).

## BP-06: Model Family by Modality

**applies_to:** all

Default model families exist for a reason:
- **Tabular / quant** → GBDT (XGBoost, LightGBM, CatBoost)
- **Vision / speech** → CNNs / ViTs
- **Text** → Transformers

Deviating is fine but justify it. Don't use a transformer on tabular data because it's trendy.

**Anti-pattern:** Using BERT to encode a 50-column numeric dataset.

## BP-07: Advanced Techniques Late

**applies_to:** all

Ensembling, stacking, pseudo-labeling, and TTA are finishing moves, not opening moves. Apply them only after a single strong model with good features. They amplify signal but also amplify mistakes.

**Anti-pattern:** Building a 5-model ensemble when no individual model beats baseline.

## BP-08: Characterize Noise Before Trusting a Delta

**applies_to:** all

Run your verify command 3-5 times with different seeds. If the standard deviation exceeds your claimed improvement, the delta is noise. This is what `noise_characterization` on COMP is for.

**Anti-pattern:** Declaring victory on a 0.2% improvement when run-to-run variance is 0.5%.

## BP-09: Never Tune on the Test Split

**applies_to:** all

The test set is a one-time honesty check. Any decision informed by test performance (feature selection, hyperparameter choice, model selection) contaminates it. Use CV for all tuning; reserve test for final evaluation only.

**Anti-pattern:** Iteratively adding features that boost the public test score until it stops improving.
