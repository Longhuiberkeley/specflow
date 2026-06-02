# ML Methodology Handbook

Best practices for ML/experimental work. BP-01 is mandatory (enforced by Phase 0.6 of autonomous-loop-protocol). BP-02 through BP-22 are advisory but strongly recommended.

These are grouped: **BP-01–09** (foundations), **BP-10–12** (validation integrity), **BP-13–16** (statistical traps), **BP-17–19** (optimize the real objective), **BP-20–22** (finishing moves), plus a **Bias Catalog**. Phase 2 ideation should pull the groups relevant to the current hypothesis — they are meant to be consulted live, not read once.

## Goal: Generalization, Not the Leaderboard

A COMP's `verify_command` is a *proxy* for a real-world goal (live trading P&L, production accuracy). Many widely-shared "how to win Kaggle" tactics optimize a **frozen public leaderboard** and actively hurt a deployed system. Apply this filter before importing any competition technique:

| Transfers to deployed research (keep) | Leaderboard-gaming (avoid here) |
|---|---|
| Robust CV matched to data structure (BP-04) | Probing / overfitting a public leaderboard |
| Leakage hygiene (BP-10, BP-12) | Exploiting unintended data leaks in the eval set |
| Adversarial validation (BP-11) | Post-processing tuned to one specific test split |
| Feature engineering, calibration (BP-05, BP-18) | Ensembles too heavy/slow to run live |
| Ensembling diverse models, seed averaging (BP-20, BP-21) | Any move that raises the metric but not the goal |

**Rule:** if a tactic would raise `metric_value` without raising the underlying goal, it is metric-gaming (premise-check 2d), not progress. Importing leaderboard tricks blindly *increases* the overfitting this pack exists to prevent.

## Domain Fit Gate

Each practice lists `applies_to` domains. Only apply practices tagged for your `COMP.domain`. Forcing vision BPs onto a quant COMP wastes time.

| Domain | Tag |
|--------|-----|
| Quantitative trading | `quant` |
| Tabular ML | `tabular_ml` |
| Computer vision | `vision` |
| NLP / text | `nlp` |

---

## BP-01: EDA Before Modeling [MANDATORY]

**applies_to:** all
**enforcement:** Mandatory. Enforced by Phase 0.6 of `autonomous-loop-protocol.md`. A COMP that skips EDA runs blind — the LOOP is stopped before the first iteration.

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

---

# Validation Integrity (BP-10–12)

The single largest source of results that look great offline and collapse live. If validation is wrong, every downstream BP is wasted.

## BP-10: Split First, Preprocess Second

**applies_to:** all

Fit *every* transform — scaler, imputer, target encoder, resampling (SMOTE), outlier removal, feature selection, PCA — on the training fold only, then apply to validation/test. Anything fit on the full dataset leaks information about the eval rows into training. This is the most common silent leak and it inflates offline metrics invisibly. Wrap preprocessing in a fold-aware pipeline so the eval split stays untouched.

**Anti-pattern:** `StandardScaler().fit(X)` or `SMOTE().fit_resample(X, y)` before splitting.

## BP-11: Adversarial Validation

**applies_to:** all

Train a binary classifier to distinguish train rows from test/holdout rows (label train=0, test=1). If its AUC ≈ 0.5, the two sets are exchangeable and your CV is trustworthy. If AUC → 1.0, train and test differ systematically — your CV score is lying, and the features the classifier relies on are your distribution-shift (or leakage) suspects. In quant, run it as backtest-vs-recent-live to catch regime drift before deploying.

**Anti-pattern:** Trusting a glowing CV score when the test period is a different market regime than training.

## BP-12: Out-of-Fold for Any Meta-Step

**applies_to:** `tabular_ml`, `quant`

Target encoding, stacking inputs, and model selection must consume **out-of-fold (OOF)** predictions, never in-fold ones. Encoding a category with target statistics computed on the same rows you train on leaks the label; stacking on in-fold predictions does the same one level up. Generate OOF predictions and use those as the meta-features.

**Anti-pattern:** Target-encoding a high-cardinality column on the whole training set, then training on it.

---

# Statistical Traps (BP-13–16)

## BP-13: Correct for Multiple Comparisons

**applies_to:** all

The best of N tried things is upward-biased by roughly (noise spread × the order statistic of N) — try enough variants and one will look good by luck alone. Before declaring a LOOP's top EXPT a real win, **confirm it on a fresh seed or a held-out slice**. The more hypotheses you tested, the harder you discount a marginal winner. This is the LOOP-level counterpart to BP-08's per-EXPT noise check.

**Anti-pattern:** Declaring the top of 50 EXPTs a win on a delta smaller than the run-to-run spread, with no confirmation run.

## BP-14: Mind Dimensionality — Not Just at EDA

**applies_to:** `tabular_ml`, `quant`

p ≫ n (more features than samples) and multicollinearity cause spurious fits, distances that stop being meaningful, and feature-importance rankings you can't trust. This is a **modeling** concern, not a one-time EDA snapshot: it should drive regularization strength, whether to reduce dimensionality, the choice of tree vs linear models, and how much weight to put on importance plots. Adding features always helps the training fit and eventually hurts generalization.

**Anti-pattern:** Engineering 2,000 features on 800 samples and reading the top-20 importances as truth.

## BP-15: Distribution Shift & Non-Stationarity

**applies_to:** `quant`, `tabular_ml`

Covariate shift (inputs drift) and concept drift (the input→target relationship drifts) break the assumption that train resembles serve. Quant data is rarely stationary. Pair walk-forward validation (BP-04) with adversarial validation (BP-11) to detect it, and prefer features/models robust across regimes over ones tuned to one window.

**Anti-pattern:** Training on a low-volatility regime and deploying into a high-volatility one without re-checking.

## BP-16: Simpson's Paradox & Confounding

**applies_to:** all

An effect measured in aggregate can reverse within subgroups, and a confounder can manufacture or hide a relationship. Always check key results **per segment** (per asset, per time bucket, per class), not just globally. This is the statistical root of the multi-output discipline (BP-19): a global score can move the opposite direction of its components.

**Anti-pattern:** Concluding a feature helps because aggregate accuracy rose, when it helped one class and hurt three.

---

# Optimize the Real Objective (BP-17–19)

## BP-17: Optimize the Actual Eval Metric, Then Post-Process for It

**applies_to:** all

Training loss is usually not the scoring metric. Optimize a surrogate that tracks the metric, then post-process for the metric itself: tune the decision threshold for F1, rank-average for AUC, calibrate for log-loss, round/clip for bounded targets. Choose all such post-processing on validation, never on test (BP-09).

**Anti-pattern:** Reporting accuracy at a 0.5 threshold when the metric is F1 and the optimal threshold is 0.2.

## BP-18: Calibrate Probabilities When Decisions Depend on Them

**applies_to:** `quant`, `tabular_ml`

A model can rank well (good AUC) yet output badly miscalibrated probabilities. Any expected-value decision — position sizing, Kelly fraction, thresholded actions — needs calibrated probabilities (Platt/isotonic fit on held-out folds), not just good ranking. Check a reliability curve, not only AUC.

**Anti-pattern:** Sizing positions by a model's raw softmax outputs that systematically overstate confidence.

## BP-19: Decompose Multi-Output Targets

**applies_to:** all

When the target is a vector `[x, y, z]` (or the metric is an aggregate over components), a single scalar score can hide a component that is regressing while another carries the average. **Record each component as its own number** (see `auxiliary_metrics` convention `component_<name>` in the loop protocol), inspect every component each iteration, and watch their correlation — improving one by trading off another is rarely real progress.

**Anti-pattern:** Optimizing a mean-of-three-targets score while the third target quietly gets worse every iteration.

---

# Finishing Moves (BP-20–22)

Apply these **only after** a single strong model with good features (BP-07). They amplify signal — and mistakes.

## BP-20: Ensemble Diverse Models; Diversity Beats Individual Strength

**applies_to:** all

Averaging, hill-climbing, or stacking helps in proportion to how **uncorrelated** the members' errors are, not how many members there are. Two decorrelated mediocre models often beat five near-identical strong ones. Seek diversity across model families, feature sets, and seeds; add members greedily, keeping only those that improve OOF/validation.

**Anti-pattern:** Averaging five LightGBM runs with the same features and expecting an ensemble lift.

## BP-21: Seed Averaging / Bagging

**applies_to:** all

Retrain the same pipeline under several random seeds and average the predictions — a cheap, reliable variance reduction. The "extra training" Grandmaster move: once a configuration is chosen, refit on 100% of available data with multiple seeds for the final model.

**Anti-pattern:** Shipping a single-seed model whose result sits inside its own seed-to-seed spread.

## BP-22: Pseudo-Labeling / Semi-Supervised

**applies_to:** `tabular_ml`, `vision`, `nlp`

When abundant unlabeled data exists, use a strong model to label it and fold high-confidence predictions back into training. Powerful, but it amplifies the model's existing bias and can entrench errors — gate it behind strong, leak-free validation and confidence thresholds.

**Anti-pattern:** Pseudo-labeling with a weak model and training on its confident-but-wrong guesses.

---

# Bias Catalog

Quick reference — the *tell* (how it shows up) and the *fix*. These are cross-cutting; look-ahead/data-snooping overlaps with leakage (BP-10/12) and the premise check (Phase 2d).

| Bias | Tell | Fix |
|------|------|-----|
| **Selection bias** | Sample isn't representative of where the model will run (e.g. only liquid assets, only complete rows). | Define the target population first; sample/weight to match it. |
| **Survivorship bias** | Dead/delisted/failed cases are missing from the data. | Use point-in-time data that includes entities as they existed then. |
| **Look-ahead / data-snooping** | Metric improbably high; a feature uses information not available at decision time. | Strict temporal cutoffs; build features from the past only (ties to BP-10/12). |
| **Confirmation bias (in ideation)** | Only testing variants of the hypothesis you already like; ignoring `what_failed`. | In `explore` mode deliberately test the opposite; read prior FIND `what_failed`. |
| **Label leakage** | A feature is a proxy for, or computed from, the target. | Audit each feature's provenance; drop anything that wouldn't exist at prediction time. |
