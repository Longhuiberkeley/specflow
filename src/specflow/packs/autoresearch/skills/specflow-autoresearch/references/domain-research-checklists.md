# Domain Research Checklists

First-principles research directions organized by domain. Loaded during Phase 0.7 (First-Principles Decomposition) to force the agent to think broadly before narrowing.

**Purpose:** These checklists prevent the agent from defaulting to the easiest code-to-generate changes (parameter tweaks) by providing a structured menu of *fundamentally different* research directions. The agent must articulate which areas it has and has not explored, and justify focusing on any single area.

## How to Use

During Phase 0.7, the agent:

1. Loads the checklist matching `COMP.domain`
2. Walks each section, assessing relevance to the current COMP
3. Records a `research_agenda` on the LOOP artifact — a ranked list of research directions with expected impact
4. During Phase 2c, checks the agenda to ensure coverage, not repetition

## Quant / Algorithmic Trading

### Data Quality & Integrity
- [ ] Stationarity: Are price/return series stationary? (ADF, KPSS tests)
- [ ] Survivorship bias: Does data include delisted/failed assets?
- [ ] Look-ahead bias: Does any feature use future information not available at decision time?
- [ ] Data alignment: Are timestamps aligned across assets? Timezone consistency?
- [ ] Missing data patterns: Is missingness informative (halts, delistings)?
- [ ] Corporate actions: Splits, dividends adjusted correctly?

### Signal & Feature Engineering
- [ ] Feature decay profile: How quickly does predictive power degrade? (t+1 vs t+5 vs t+20)
- [ ] Cross-asset signals: Do related assets carry predictive information?
- [ ] Regime detection: Are there distinct market regimes? Can they be identified?
- [ ] Microstructure features: Spread, depth, order flow imbalance
- [ ] Temporal features: Time-of-day, day-of-week, month effects
- [ ] Fundamental features: Earnings, sentiment, macro indicators
- [ ] Alternative data: What non-price information is available and legal to use?

### Modeling Paradigm
- [ ] Is the current model family appropriate? (GBDT vs neural vs Kalman vs rule-based)
- [ ] Would a regime-switching model capture structure a single model misses?
- [ ] Would an ensemble of fundamentally different approaches outperform a single approach?
- [ ] Is the target variable correctly defined? (returns vs excess returns vs risk-adjusted returns)
- [ ] Would predicting a different target (direction, volatility, regime) be more fruitful?

### Risk & Portfolio Construction
- [ ] Position sizing: Is the current method optimal? (Kelly, risk parity, volatility targeting)
- [ ] Drawdown control: Is there a mechanism to reduce exposure during adverse periods?
- [ ] Correlation structure: Are "uncorrelated" strategies actually uncorrelated out-of-sample?
- [ ] Transaction costs: Are they modeled realistically? (slippage, market impact, borrow costs)
- [ ] Capacity: Does the strategy still work at larger scale?

### Validation & Robustness
- [ ] Walk-forward validation: Does performance hold on unseen temporal windows?
- [ ] Parameter sensitivity: Do small parameter changes flip the result?
- [ ] Out-of-sample decay: How quickly does alpha decay after the training period?
- [ ] Regime robustness: Does the strategy work across different market conditions?
- [ ] Minimum trade count: Are results based on enough trades to be statistically significant?

### Post-Modeling
- [ ] Active learning: Can the model identify and flag bad labels/noisy data for removal?
- [ ] Online learning: Should the model adapt to new data incrementally?
- [ ] Execution: Can the signals actually be implemented given latency and infrastructure constraints?

### Common Traps
- [ ] **Data snooping from multiple hypothesis testing:** Testing 50 strategies on the same data → at least one will look good by luck. Confirm top results on a fresh seed or held-out slice (ML-13).
- [ ] **Regime-dependent backtesting:** A strategy that works in a low-vol regime may blow up in high-vol. Walk-forward across regime boundaries, not just calendar time.
- [ ] **Ignoring transaction costs in early stages:** "Promising" strategies that trade frequently may be net-negative after slippage and fees. Model costs from the start.
- [ ] **Overfitting to recent data:** The last 6 months of data is the most "interesting" but also the smallest sample. Don't overweight it.

---

## Tabular ML

### Data Quality
- [ ] Target distribution: Class balance, skew, outliers, range
- [ ] Missingness: MCAR vs MAR vs MNAR? Is missingness informative?
- [ ] Cardinality: Constant columns, near-duplicate features, high-cardinality categoricals
- [ ] Train/test distribution shift: Adversarial validation AUC
- [ ] Feature provenance: Is any feature a proxy for the target?
- [ ] Temporal leakage: If time-series, is split temporal (not random)?

### Feature Engineering
- [ ] Domain-specific encodings: Target encoding (OOF!), interaction terms, polynomial features
- [ ] Aggregation features: Rolling statistics, group-level aggregations
- [ ] Feature selection: Are all features contributing? Remove noise features
- [ ] Dimensionality: p >> n? Need regularization or reduction?
- [ ] Feature importance stability: Do different methods agree on top features?

### Modeling Paradigm
- [ ] Baseline established? (majority class, global mean, simple linear model)
- [ ] Model family match: GBDT for tabular, not transformers (unless justified)
- [ ] Would a completely different paradigm work? (linear vs tree vs distance-based vs neural)
- [ ] Stacking/ensemble: Would combining different model families help?
- [ ] Semi-supervised: Is there unlabeled data that could help?

### Validation & Robustness
- [ ] CV scheme matches data structure (temporal, grouped, stratified)
- [ ] Out-of-fold predictions for any meta-step (target encoding, stacking, model selection)
- [ ] Calibration: Are probabilities reliable for decision-making?
- [ ] Multiple comparison correction: Best of N is upward-biased
- [ ] Feature stability: Do top features change across folds?

### Post-Modeling
- [ ] Threshold optimization: Is 0.5 the right decision boundary?
- [ ] Error analysis: Where does the model fail? Per-segment analysis
- [ ] Fairness/bias: Does performance vary across protected groups?
- [ ] Deployment: Feature pipeline reproducible in production?

### Common Traps
- [ ] **Target leakage through temporal features:** Features that encode future information (e.g., "days since last purchase" computed on the full dataset instead of train-only). Audit every feature's computation window.
- [ ] **CV score inflation from non-temporal splits:** Random splits on time-series data give inflated scores. Always use temporal splits if the data has a time dimension (ML-04).
- [ ] **High-cardinality overfitting:** Target encoding without OOF (ML-12) or high-cardinality categoricals with few samples per category. Check cardinality vs sample count.
- [ ] **Winner's curse in model selection:** Best of N cross-validated models is upward-biased. Confirm the winning model on a truly held-out set (ML-13).

---

## Computer Vision

### Data Quality
- [ ] Image dimensions: Consistent across dataset?
- [ ] Corrupt files: Any unreadable images?
- [ ] Label quality: Random sample manual verification
- [ ] Class distribution: Balanced? Severely imbalanced?
- [ ] Annotation consistency: Inter-annotator agreement if applicable

### Data Pipeline
- [ ] Augmentation strategy: Which augmentations are appropriate for this domain?
- [ ] Preprocessing: Normalization, resizing strategy (crop vs pad vs stretch)
- [ ] Train/val/test split: Stratified? Grouped by patient/scene/session?
- [ ] Data loading: Efficient pipeline (no GPU starvation)

### Modeling Paradigm
- [ ] Pretrained baseline: Does a pretrained model zero-shot already work well?
- [ ] Architecture choice: CNN vs ViT vs hybrid — justified for this data size and task?
- [ ] Transfer learning: Which layers to freeze/unfreeze? Learning rate schedule?
- [ ] Resolution: Is current input resolution optimal? Higher might help, lower might be sufficient
- [ ] Multi-scale: Would features at multiple resolutions help?

### Training Recipe
- [ ] Loss function: Is it aligned with the evaluation metric?
- [ ] Learning rate schedule: Warmup, decay, cosine vs step
- [ ] Regularization: Dropout, weight decay, label smoothing, stochastic depth
- [ ] Batch size: Appropriate for the model and data?
- [ ] Mixed precision: Can training be sped up without quality loss?

### Post-Modeling
- [ ] Test-time augmentation: Would augmenting at inference improve results?
- [ ] Pseudo-labeling: Would semi-supervised learning on unlabeled data help?
- [ ] Ensemble: Would combining different architectures help?
- [ ] Active learning: Can the model identify images most valuable to label?
- [ ] Error analysis: Which classes/scenes/conditions does the model fail on?

### Common Traps
- [ ] **Shortcut learning:** The model learns spurious correlations (e.g., "boats always appear on water" → classify any water image as boat). Check saliency maps — is the model looking at the right thing?
- [ ] **Augmentation leakage:** Augmentations applied before the train/val split create near-duplicate images across splits. Always split first, augment after.
- [ ] **Resolution mismatch:** Training at 224px but the discriminative detail is at 512px. Or vice versa — training at high res when low res suffices and is 4x faster.
- [ ] **Pretrained model domain mismatch:** ImageNet features may not transfer to medical/satellite/microscopy images. Validate the pretrained baseline before building on it.

---

## NLP / Text

### Data Quality
- [ ] Language detection: Is the dataset monolingual? Expected?
- [ ] Text length distribution: Are there outliers that would break tokenization?
- [ ] Encoding consistency: UTF-8 throughout? No mojibake?
- [ ] Label quality: Subjective labels — inter-annotator agreement?
- [ ] Duplicates: Near-duplicate texts with different labels?

### Preprocessing & Tokenization
- [ ] Tokenization strategy: BPE, WordPiece, SentencePiece — appropriate for the language/domain?
- [ ] Vocabulary: Is subword coverage sufficient? OOV rate?
- [ ] Normalization: Lowercasing, punctuation, special characters — consistent?
- [ ] Sequence length: What's the max length? How much is truncated?

### Modeling Paradigm
- [ ] Baseline: TF-IDF + linear model before reaching for transformers
- [ ] Pretrained model: Which checkpoint is closest to this domain?
- [ ] Fine-tuning strategy: Full vs adapter vs LoRA vs prompt tuning
- [ ] Architecture: Encoder-only vs encoder-decoder vs decoder-only — right for the task?
- [ ] Multilingual: Does the model handle all languages in the data?

### Training Recipe
- [ ] Learning rate: Lower for fine-tuning pretrained models
- [ ] Batch size: Gradient accumulation if limited GPU memory
- [ ] Sequence length: Impact on memory and quality
- [ ] Regularization: Dropout, weight decay for pretrained layers
- [ ] Data augmentation: Back-translation, synonym replacement, contextual augmentation

### Post-Modeling
- [ ] Calibration: Are confidence scores reliable?
- [ ] Error analysis: Which text types/lengths/languages fail?
- [ ] Fairness: Performance across demographic groups or languages
- [ ] Inference cost: Can the model be distilled or quantized for deployment?
- [ ] Prompt engineering: If using generative models, is the prompt optimized?

### Common Traps
- [ ] **Label leakage through text overlap:** Near-duplicate texts in train and test with different labels, or test set text appearing verbatim in training data. Deduplicate before splitting.
- [ ] **Tokenizer/domain mismatch:** A general-purpose tokenizer (BPE trained on web text) may split domain terms poorly (medical codes, chemical formulas). Check OOV rate and token quality on domain text.
- [ ] **Sequence length truncation silently dropping signal:** If 20% of texts exceed max_length and get truncated, the model never sees their full content. Measure truncation rate and its impact on the label distribution of truncated vs non-truncated samples.
- [ ] **Prompt sensitivity in generative models:** Small prompt changes causing large output variance. Test multiple prompt phrasings and measure variance before trusting a result.

---

## Generic (fallback for unlisted domains)

When `COMP.domain` does not match any of the above, use this generic checklist:

### Understand the Problem
- [ ] What does the metric actually measure? Is it a faithful proxy for the goal?
- [ ] What assumptions does the current approach make? Which, if wrong, would change everything?
- [ ] What would a domain expert try first? What would they never try?

### Data & Inputs
- [ ] Data quality: Missing values, outliers, distribution shape
- [ ] Feature relevance: Are all inputs actually useful? Is anything missing?
- [ ] Data sufficiency: Is there enough data for the approach being used?

### Approach Diversity
- [ ] Simplest possible approach: What's the dumbest thing that could work?
- [ ] Alternative paradigms: Name 3 fundamentally different approaches
- [ ] Anti-approach: What would be the WORST approach? Why? Does the current approach share any of its flaws?

### Validation
- [ ] Is the evaluation method trustworthy?
- [ ] Could the metric improve without the goal being served?
- [ ] What would it take to falsify the current best result?

### Post-Modeling
- [ ] Error analysis: Where and why does the current approach fail?
- [ ] What information would make the biggest difference if available?
- [ ] Is the current ceiling the approach or the data?
