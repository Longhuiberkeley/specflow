# Competition Setup Protocol

Walks the user through creating a COMP artifact. Read this when the user invokes `/specflow-autoresearch` without an existing competition, or when they explicitly ask to set up a competition.

## Step 1: Identify the Dataset and Split Method

Ask the user:

- **What dataset are you optimizing against?** (e.g., "BTC/USDT 30m candles", "ImageNet validation split", "Kaggle titanic train.csv")
- **What split method separates training from evaluation?** (e.g., "walk-forward with 80/20 gap", "5-fold cross-validation", "single temporal split")

Record these in COMP's optional fields: `dataset`, `split_method`.

## Step 2: Choose the Verify Command

The verify command is a shell command that:

1. Runs the experiment against the dataset
2. Outputs a **single parseable number** to stdout (the metric)
3. Exits 0 on success

**Mechanical validation checklist:**

| Check | Pass | Fail |
|-------|------|------|
| Outputs a number | `87.3`, `0.95`, `42` | `PASS`, `looks good` |
| Extractable by command | `grep`, `awk`, `jq` can isolate it | Requires human judgment |
| Deterministic | Same code → same number (given fixed seed) | Random, flaky |
| Fast | Under 5 minutes | Over 15 minutes |

**Research-relevant verify templates:**

| Domain | Verify Command | Metric |
|--------|---------------|--------|
| Quant trading | `python scripts/evaluate.py --strategy {strategy} 2>&1 \| grep 'sharpe' \| awk '{print $2}'` | Sharpe ratio |
| ML classification | `python train.py --eval-only 2>&1 \| grep 'accuracy' \| awk '{print $NF}'` | Accuracy % |
| Kaggle competition | `python scripts/score.py --submission {output} \| tail -1` | Competition metric |
| NLP | `python evaluate.py 2>&1 \| grep 'BLEU' \| grep -oP '[\d.]+'` | BLEU score |

The `{strategy}` placeholder is replaced at runtime with the strategy identifier being tested.

## Step 3: Choose Metric Direction

Ask: "Is higher or lower better for your metric?"

- **Higher is better:** Sharpe ratio, F1 score, accuracy, mAP, BLEU
- **Lower is better:** loss, error rate, RMSE, latency (ms)

Record as COMP's `metric_direction` field: `higher_is_better` or `lower_is_better`.

### Does this metric, alone, capture success?

Before moving on, pause on intent. A single metric is sometimes exactly right ("the best chess engine" → win rate) and sometimes a thin proxy for what the user actually wants ("accurate **and** well-calibrated", "a family of strategies across asset classes", "fast enough to deploy"). Ask the user — or reason from the goal — whether the metric is the whole story. If not, capture the rest now rather than discovering it 40 iterations in:

- a different `metric_name` that bakes in generalization (walk-forward Sharpe over single-split Sharpe)
- `auxiliary_metrics` the loop should always log (calibration error alongside accuracy)
- a non-`single_best` `objective_type` (next step)
- `success_criteria` describing deploy-fit the raw metric won't show

This is the difference between a number that climbs and a result that does the job.

## Step 3.5: Choose Objective Type

Ask: "Are you looking for one best result, a family of good results, or a Pareto front?"

| objective_type | When to use | Example |
|---|---|---|
| `single_best` | One metric to rule them all | Best Sharpe ratio, lowest latency |
| `family_of_good` | Need diverse, deployable candidates | 3 uncorrelated quant strategies; ensemble of 5 models |
| `pareto_front` | Multi-objective tradeoff space | Accuracy vs inference speed; return vs drawdown |

Record as COMP's `objective_type` field. Default to `single_best` if the user is unsure.

**Why it matters:** `family_of_good` changes LOOP behavior — the agent prefers uncorrelated keeps over marginal metric gains, and the leaderboard groups by strategy family rather than ranking by raw metric alone.

## Step 4: Dry-Run the Verify Command

**MANDATORY — dry-run before accepting the competition.**

1. Run the verify command on the current codebase
2. Confirm exit code 0
3. Extract the metric and validate it matches `^-?[0-9]+\.?[0-9]*$`
4. If dry-run fails → show error, help user fix the pipeline, re-validate

**Common failures and fixes:**

| Extracted Value | Problem | Fix |
|---|---|---|
| `85.2%` | Trailing `%` | Add `\| tr -d '%'` |
| `342ms` | Trailing unit | Add `\| grep -oE '[0-9]+\.?[0-9]*'` |
| *(empty)* | grep matched nothing | Check grep pattern |
| Two numbers | Pipeline too broad | Add `head -1` or tighten grep |

**Verify-command safety screen:** Before dry-run, scan for `rm -rf /`, fork bombs, `curl ... | sh`, embedded credentials. Refuse and re-prompt if found.

## Step 5 (Optional): Define a Guard Command

A guard command runs after verification to catch regressions. If you want every loop on this competition to check that tests still pass while optimizing the metric, define a guard.

| Field | Values | Purpose |
|-------|--------|---------|
| `guard_command` | Any shell command that exits 0 on pass | Regression check (e.g., `npm test`, `pytest`, `cargo test`) |
| `guard_mode` | `pass_fail` (default) or `metric_valued` | `pass_fail`: exit 0 = pass. `metric_valued`: extract number, compare to threshold |

Example COMP with guard:

COMP-specific fields are written with the generic `--set KEY=VALUE` flag (repeatable; values are parsed as JSON when possible, else kept as strings). Only `--type`, `--title`, and `--status` are first-class flags. **A COMP must be created with `--status active`** (`draft` is not a valid competition status).

```bash
specflow create --type competition \
  --title "Track A: single split" \
  --status active \
  --set verify_command="python scripts/track_a.py --strategy {strategy}" \
  --set metric_name="Sharpe ratio" \
  --set metric_direction=higher_is_better \
  --set guard_command="pytest tests/ -x" \
  --set guard_mode=pass_fail
```

If no guard is defined, the loop skips Phase 5.5 entirely.

## Step 6: Create the COMP Artifact

```bash
specflow create --type competition \
  --title "Track A: single split" \
  --status active \
  --set verify_command="python scripts/track_a.py --strategy {strategy}" \
  --set metric_name="Sharpe ratio" \
  --set metric_direction=higher_is_better
```

Record baseline metric from the dry-run as the initial reference point.

## Step 6.5: Set Goals and Define the "Why"

A COMP is not just a metric — it is a research question. Capture the goals explicitly so the agent knows when to stop and what success looks like:

`goals` is a list of freeform strings — pass it as a JSON array:

```bash
specflow update COMP-001 --set goals='["Find 3 uncorrelated strategies with Sharpe > 2.0", "Walk-forward Sharpe degrades < 15% from in-sample", "Max drawdown < 10% across all candidates"]'
```

Goals are what the loop steers toward: they drive hypothesis framing (Phase 2a), Dynamic Termination (Phase 8), and what the post-check should validate (Step 7). The agent uses them to decide whether to stop early or continue.

Also set `success_criteria` — a sentence explaining why a high metric might still fail. This is the deploy-fit definition the post-check enforces:

```bash
specflow update COMP-001 --set success_criteria="High Sharpe alone is not enough; strategy must be profitable after transaction costs and deployable with <5min setup time."
```

## Step 6.6: Define Boundaries and Constraints

Ask the user explicitly about the rules of engagement for this competition:

> "What are the strict boundaries or constraints for this research? (e.g., Are pre-trained weights allowed? Is external unlabeled data okay? Are there any forbidden libraries or techniques?)"

Record their answers in the COMP's `constraints` field. This prevents the agent from finding "solutions" that violate the user's implicit rules (like downloading a pre-trained model when the goal was to train from scratch, or expanding the dataset beyond allowed limits).

```bash
specflow update COMP-001 --set constraints="Must be trained from scratch with randomized weights. External unlabeled data is allowed for pre-training, but no external labeled data. Do not use the transformers library."
```

## Step 6.7: Define Research Theses (the durable agenda)

Goals say *what success looks like*. Theses say *what we believe about this domain that, if true, would get us there*. They are the broader claims a series of hypotheses test across multiple loops — the durable research agenda above any single experiment.

Ask the user:

> *"Beyond hitting the metric — what are the 2–4 substantive claims about this domain you're trying to validate or refute over the next several loops? These will guide hypothesis generation in every iteration, and FINDs will accumulate evidence for or against them."*

Examples to seed the conversation:

- quant: *"Cross-asset regime signals lift risk-adjusted return"*, *"Mean-reversion dominates on intraday bars for this universe"*
- ML: *"Data augmentation beats architecture changes on this dataset"*, *"Pretraining on unlabeled domain data closes the labeled-data gap"*
- systems: *"Tail latency is bound by GC, not network"*, *"Read-heavy workloads benefit more from caching than indexing"*

Record:

```bash
specflow update COMP-001 --set theses='["Cross-asset regime signals lift Sharpe", "Kalman filters outperform OLS on intraday bars for this universe"]'
```

Theses are *not* hypotheses — they're broader claims that hypotheses test. They evolve: add new ones as loops surface them, refute old ones with evidence, supersede when refined. The agent surfaces them at the start of every LOOP and links FINDs back to them in `what_worked` / `what_failed`.

## Step 7 (Optional): Define Pre-Check and Post-Check Commands

Instead of passively waiting for the user to define checks, **proactively suggest them based on the domain and goals**. Ask the user:
> "Before we start running optimization loops, should we write a pre-check script (e.g., to verify the class distribution of your images, or check if the series are actually cointegrated)? And should we add a post-check to validate the deployability of successful results?"

Instead of a single monolithic verify script, use a **unified runner with phase flags**:

```bash
# The same script handles all three phases
specflow create --type competition \
  --title "Pair-trading with Kalman" \
  --status active \
  --set verify_command="uv run python run_comp002.py {strategy} --phase=verify" \
  --set pre_check_command="uv run python run_comp002.py {strategy} --phase=pre-check" \
  --set post_check_command="uv run python run_comp002.py {strategy} --phase=post-check" \
  --set metric_name="Sharpe ratio" \
  --set metric_direction=higher_is_better
```

**Derive the checks from the goals, not just the metric.** The pre-check guards the inputs (some datasets/algorithms deserve EDA before a single verify runs); the post-check guards deploy-fit — it should test the conditions named in `success_criteria`, so a high-metric result that wouldn't survive deployment gets caught. Not every COMP needs both: pick the ones the goal actually implies.

| Phase | Purpose | Quant Example | ML Example |
|-------|---------|---------------|------------|
| `pre-check` | EDA, data quality, structural validation | Cointegration test, stationarity test | Data leakage scan, class balance check |
| `verify` | Primary metric extraction | Sharpe ratio on backtest | Validation accuracy / loss |
| `post-check` | Deploy-fit: calibration, robustness, OOS, sensitivity | Walk-forward Sharpe, max drawdown, cost after slippage | OOS accuracy, calibration error, fairness metrics |

Separate scripts also work — the protocol only cares that the commands exist and produce measurable output.

**IMPORTANT:** Before creating a LOOP, the agent must confirm that all defined commands (verify, pre-check, post-check) exist and have passed a successful dry-run. No LOOP may be created against a COMP whose pipeline is untested.

## Step 8 (Optional): Characterize Metric Noise

Run the verify command 3x back-to-back on unchanged code. Record the results on the COMP so future LOOPs know the measurement floor:

```bash
# Run 3 times and capture
for i in 1 2 3; do python run_comp002.py baseline --phase=verify; done
# Results: 1.23, 1.31, 1.15

specflow update COMP-001 --set noise_characterization='{"metric": "sharpe", "mean": 1.23, "stdev": 0.08, "min": 1.15, "max": 1.31, "strategy": "multi_run_median"}'
```

This prevents false-positive "keeps" when the improvement is within the noise floor.

## Domain-Specific Auxiliary Metric Recommendations

When `domain` is set on the COMP, the agent and lint system know which auxiliary metrics are expected. Log all that apply:

| Domain | Recommended auxiliary_metrics |
|--------|------------------------------|
| `quant` | max_drawdown, total_trades, win_rate, profit_factor, oos_decay, walk_forward_sharpe, sortino_ratio, calmar_ratio |
| `ml` | val_loss, learning_rate, batch_size, epochs, architecture, num_parameters, inference_ms, train_time_minutes |
| `nlp` | perplexity, token_count, rouge_l, bertscore_f1, inference_tokens_per_sec |
| `systems` | p50_latency_ms, p99_latency_ms, memory_mb, throughput_rps, cpu_percent, error_rate |
| `safety_critical` | false_positive_rate, false_negative_rate, precision, recall, explainability_score, domain_coverage |

These are recommendations, not mandates. The agent should log what it sees fit, but `artifact-lint` warns when a domain-recommended field is completely absent from a kept EXPT.

## Trust Boundary

`verify_command` is executed by the agent with full shell access. Only the project owner should create or edit COMP artifacts. Audit verify commands for safety before the first loop run — the agent trusts them blindly.

## Multi-Competition Pattern

A common pattern is to run two competitions against the same dataset with different evaluation rigor:

- **COMP-001 (Screener):** Fast evaluation (e.g., single in-sample split). Used for rapid exploration loops. Low iteration cost enables bold experimentation.
- **COMP-002 (Validator):** Rigorous evaluation (e.g., walk-forward out-of-sample). Used for validation loops. Confirms that screener findings generalize.

FINDs from COMP-001 inform LOOPs on COMP-002 when the user creates a LOOP with `mode: validate` and reads the screener's confirmed FINDs. The FIND schema's `applies_to` field indicates scope.

## Multi-criteria Competitions

Most real domains have one key metric but several important auxiliary concerns. The schema supports this through three distinct mechanisms — use all three deliberately rather than collapsing everything into a single composite number.

### Primary Metric (for ranking)

The COMP's `metric_name` + `metric_direction` fields define the **one number** the agent optimizes. This is what drives the `kept`/`discarded` decision in Phase 6.

Choose a robustness-adjusted primary when possible:

| Primary | Why it's better than the alternative |
|---------|--------------------------------------|
| `sharpe_walk_forward` | Tests generalization across temporal windows, not just one split |
| `sharpe_bootstrap_lower_5pct` | Bootstrap CI lower bound is harder to overfit than point estimate |
| `accuracy_5fold_mean` | Cross-validated mean is more stable than single-split accuracy |

Point estimates over a single backtest are the most overfittable metrics in finance. Prefer metrics that bake generalization into the measurement itself.

### Guards (binary floors)

Guards are hard constraints that auto-discard experiments violating them. They use the COMP's `guard_command` + `guard_mode` fields. Unlike the primary metric, guards are binary — you either pass or you don't.

**Why lexicographic guards beat composite scalars:** A composite like `0.6 * sharpe - 0.3 * drawdown_penalty` smears the constraint into the objective. The agent will find a basin where one component dominates (e.g., tolerating extreme drawdown to chase Sharpe). Guards stay binary and unforgeable.

**Worked quant example:**

```bash
specflow create --type competition \
  --title "Walk-forward momentum strategy" \
  --status active \
  --set verify_command="python scripts/evaluate.py --strategy {strategy} 2>&1 | grep 'sharpe_wf' | awk '{print \$2}'" \
  --set metric_name="Walk-forward Sharpe" \
  --set metric_direction=higher_is_better \
  --set guard_command="python scripts/guard_check.py --strategy {strategy}" \
  --set guard_mode=metric_valued
```

Where `guard_check.py` checks multiple floors and exits non-zero if any fail:

```python
# guard_check.py — returns max_drawdown value, exits 1 if violation
metrics = load_results()
if metrics["max_drawdown"] > 0.15:
    sys.exit(1)
if metrics["total_trades"] < 100:
    sys.exit(1)
if metrics["oos_decay"] > 0.30:
    sys.exit(1)
print(metrics["max_drawdown"])  # metric_valued mode: prints the number
```

The guard catches the cheats before the EXPT is marked `kept`. The agent cannot optimize around it — it's a hard wall.

### Auxiliary Metrics (for logging)

Use the EXPT's `auxiliary_metrics` field to log any additional measurements without affecting the decision. This is structured data you can query later during `:review`.

```yaml
# In EXPT frontmatter
metric_value: 1.83
auxiliary_metrics:
  max_drawdown: 0.12
  total_trades: 340
  oos_decay: 0.22
  win_rate: 0.54
  runtime_seconds: 12.4
  profit_factor: 1.67
```

The agent populates this during Phase 7 (Log) after the kept/discarded decision. It's post-hoc enrichment — not a decision driver. The leaderboard ranks by primary metric; auxiliary metrics are visible in EXPT details for the review phase.

### Choosing Strictness

These are recommendations with tradeoffs, not mandates. The user decides how strict to be:

| Strictness | When to use | Tradeoff |
|------------|-------------|----------|
| No guards | Early exploration, want maximum iteration throughput | May keep overfitted or risky experiments |
| Single guard | Production strategy, one key risk to bound | Slightly slower loops (guard runs per iteration) |
| Multiple guards | Regulated domain, multiple failure modes to prevent | More discards, fewer keeps, but higher quality |
| Composite metric instead | Only when you truly have a multi-objective problem | Requires careful weighting, agent will game weights |

### Weighted (Composite) Primary Metric

The lexicographic pattern above — one primary metric plus binary guards — is the default because it keeps each concern unforgeable. Reach for a **weighted composite** only when you genuinely have a multi-objective problem (e.g. return vs. drawdown, accuracy vs. latency) and are willing to make the weighting a deliberate, frozen, reviewed choice.

The schema exposes a single `metric_name` / `metric_direction`, so the weighting lives **inside the verify command**: the script combines the components, applies the weights, and prints one number. The COMP records the weight contract in `description`, and every component is logged as an `auxiliary_metric` on each EXPT so the review phase can decompose the score.

Concrete COMP (frontmatter, consistent with `competition.yaml`):

```yaml
id: COMP-003
title: "Risk-adjusted return composite"
type: competition
status: active
created: '2026-08-04'
verify_command: "python scripts/composite_score.py --strategy {strategy}"
metric_name: "Composite score (0.6*sharpe - 0.4*max_dd)"
metric_direction: higher_is_better
description: |
  Weighted composite printed by composite_score.py:
  score = 0.6*sharpe - 0.4*max_drawdown.
  Weights are FROZEN for the lifetime of this COMP; changing them
  is a new COMP, not an in-place edit.
guard_command: "python scripts/floor_check.py --strategy {strategy}"
guard_mode: pass_fail
objective_type: single_best
```

The verify script bakes in the weights and prints exactly one number — the agent never sees the components, only the composite:

```python
# composite_score.py — frozen weights, prints ONE number to stdout
m = load_results()
score = 0.6 * m["sharpe"] - 0.4 * m["max_drawdown"]
print(round(score, 4))
```

Log every component as an `auxiliary_metric` so review can audit the trade-off the agent made:

```bash
specflow autoresearch log --loop LOOP-003 --status kept \
  --metric-value 1.07 --change-category features \
  --summary "added volatility filter" \
  --set 'auxiliary_metrics={"sharpe": 1.9, "max_drawdown": 0.12, "composite": 1.07}'
```

**Rules that keep a composite honest:**

- **Freeze the weights in `description` and treat them as part of the metric.** Re-weighting mid-competition silently re-benchmarks every prior EXPT — that is a new COMP, not an edit (same rule as mutating `verify_command`).
- **Pair the composite with at least one `guard_command` floor** on the most safety-critical component (e.g. max drawdown, latency p99). A composite lets the agent trade a component down to lift the sum; a binary guard sets the unforgeable floor it cannot cross.
- **Log all components, every EXPT.** A climbing composite with a silently degrading component is the failure mode this pattern enables; `auxiliary_metrics` makes it visible at `:review`.
- **If one component dominates the sum**, switch back to lexicographic guards (above), where the floor stays binary and un-gameable.

When in doubt, prefer primary + guards. Use a weighted composite only when you can name the trade-off you want and accept that the agent will press against it.

## Leakage and Gaming

Leakage occurs when evaluation data or evaluation artifacts are accessible to the optimization process. Gaming occurs when the agent finds a way to inflate the metric without genuine improvement. Both produce misleading results.

### Read-only eval data

The verify command should run against data the agent literally cannot open. If the LLM can read the test set, eventually it will fit to it.

| Pattern | How to implement |
|---------|-----------------|
| File permissions | `eval/` directory owned by another user, permissions 400 |
| Separate working directory | Verify command runs in a subprocess with a different cwd |
| Protocol convention | Document `eval/` as off-limits in COMP description; agents respect this by convention |
| Container isolation | Verify command runs inside Docker with read-only eval mount |

Choose based on your threat model. A solo researcher can often trust convention. A shared CI system needs real isolation.

### Verify output should be one number

Don't let the verify command print equity curves, per-window stats, or per-trade details during the loop. That's leakage — the agent will use the rich output to guide the next iteration toward overfitting.

**Pattern:** Save detailed diagnostics to a file the agent doesn't read until the post-loop review phase. The verify command prints only the primary metric to stdout.

```bash
# Good: verify outputs one number
python scripts/evaluate.py --strategy {strategy} --save-dir results/ 2>&1 | grep 'sharpe_wf' | awk '{print $2}'

# Bad: verify prints full equity curve to stdout
python scripts/evaluate.py --strategy {strategy}  # agent sees per-window Sharpe and fits to them
```

The `--save-dir` pattern is the recommended approach: rich output goes to disk (available in review), one number goes to stdout (used by the loop).

### Robustness-adjusted primaries

Point estimates over a single backtest are the most overfittable metrics in finance. Prefer:

| Metric type | Overfit resistance | When to use |
|-------------|-------------------|-------------|
| Walk-forward (rolling OOS) | High | Any temporal data; tests stability across windows |
| Bootstrap CI lower bound | High | When you need a conservative estimate; hard to overfit the 5th percentile |
| K-fold cross-validated mean | Medium | Classification/regression tasks; assumes exchangeable data |
| Purged K-fold | Medium-High | Financial data with serial correlation; prevents leakage from adjacent folds |
| Single-split point estimate | Low | Only for quick prototyping; don't trust results |

The protocol's noise-handling section (Phase 5.1 in `autonomous-loop-protocol.md`) addresses measurement noise — running the same code multiple times and getting different numbers. That's different from generalization — whether the result holds on unseen data. Both problems matter. Noise handling fixes measurement; robustness-adjusted primaries fix generalization.

### Split Validation & Temporal Boundary Checks

Before trusting any result, verify the split itself is sound. These are deterministic checks you run locally — no network, no model training, just file and timestamp comparison against your data directory. Run them once at setup and re-run whenever the dataset changes.

**1. Train/test disjointness.** The evaluation set must share no records with training. Hash both partitions and confirm the intersection is empty:

```bash
# File-level: prints "LEAK: 0" and exits 0 when partitions are disjoint.
python -c "import hashlib,sys; \
  a={hashlib.md5(open(p,'rb').read()).hexdigest() for p in ['data/train.csv']}; \
  b={hashlib.md5(open(p,'rb').read()).hexdigest() for p in ['data/test.csv']}; \
  leak=a&b; print('LEAK:',len(leak)); sys.exit(1 if leak else 0)"
```

For row-level (not file-level) checks, extract a key from each record with `awk`/`jq`, sort, and intersect — the output must be empty:

```bash
awk -F, '{print $1}' data/train.csv | sort > /tmp/train_keys.txt
awk -F, '{print $1}' data/test.csv  | sort > /tmp/test_keys.txt
comm -12 /tmp/train_keys.txt /tmp/test_keys.txt        # must print nothing
```

**2. Temporal boundary integrity.** For time-series splits, no feature computed for a training row may use information dated at or after the split cutoff. Static checks against the source:

| Check | How to verify | Pass |
|-------|---------------|------|
| Feature join respects cutoff | Feature pipeline keys off an `as_of` date that is `< split_boundary` for training rows | No feature column has a max timestamp at/after the boundary |
| No lookahead accessor | `grep -rn "shift(-" src/features/` and any `future`/negative-lag accessor | Zero hits |
| Walk-forward windows don't overlap | For each fold, training-window end `<` test-window start | `comm -12` of per-fold train/test key sets is empty |

**3. Verify command respects the split.** The `verify_command` must read only the held-out evaluation partition. Confirm the path it loads is eval-only, not the full dataset:

```bash
# The data path inside the verify script must point at the eval partition only.
grep -n "data/" scripts/evaluate.py
```

Record the outcome of these checks in the COMP's `constraints` field so a later LOOP inherits the guarantee without re-deriving it:

```bash
specflow update COMP-001 --set constraints="Train/test disjoint: verified (0 overlap). Temporal cutoff: 2024-01-01; no lookahead accessors in src/features/. Verify reads eval partition only."
```

### User decides strictness

Not every competition needs maximum leakage protection. Examples:

- **Quick prototype:** Single split, no guards, convention-only eval isolation. Fast iteration, accept that results are directional.
- **Production strategy:** Walk-forward primary, multi-guard, read-only eval via permissions. Higher quality, fewer iterations per hour.
- **Purged K-fold for finance:** Acceptable for many financial applications — it handles serial correlation while keeping most training data. User decides if the leakage from adjacent folds is tolerable for their regime.

The anti-leakage patterns are a menu of options. Pick what fits your domain and threat model.

## Coexisting with External ML Trackers

SpecFlow EXPT artifacts are the source of truth for the research loop, but they can coexist with dedicated ML tracking tools (MLflow, Weights & Biases, Neptune, MLRun, etc.). Treat them as complementary layers:

| Layer | Tool | What it logs | When to use |
|-------|------|-------------|-------------|
| **Loop state** | SpecFlow EXPT | `metric_value`, `change_category`, `hypothesis`, `status` | Every iteration — lightweight, git-linked |
| **Rich metrics** | ML tracker | Per-epoch loss curves, gradients, activation histograms | During training — too verbose for EXPT frontmatter |
| **Hyperparameters** | Both | EXPT `parameters` + tracker config | Always — EXPT gets the summary, tracker gets the full sweep |

**Integration pattern:**

1. Your verify command can call an ML tracker internally:
   ```bash
   python train.py --track --project my-comp  # logs to wandb
   ```
2. The verify command still extracts exactly one number to stdout for the loop decision.
3. Log the external run ID in EXPT `auxiliary_metrics` so review can cross-reference:
   ```yaml
   auxiliary_metrics:
     wandb_run_id: "abc123"
     mlflow_experiment_id: 42
   ```

**Why both?** The loop needs a deterministic, git-linked, human-readable record (EXPT). The tracker needs high-frequency, high-dimensional telemetry. Don't force the EXPT to carry per-epoch data — that's context bloat. Don't force the tracker to carry hypothesis narrative — that's its weakness. Use each for what it's good at.

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Non-deterministic verify | Metric varies ±5% on same code | Pin seeds, flush caches, use deterministic test ordering |
| Metric diverges randomly | No clear improvement trend across iterations | Verify command depends on mutable state — isolate it |
| No split method documented | Results can't be reproduced | Document dataset, split method, and assets in COMP fields |
| Verify depends on network | Flaky results across runs | Mock external calls or use cached fixtures |
| Composite metric gaming | Agent optimizes one component at expense of others | Switch to primary + guards (lexicographic) |
| Lookahead in verify | In-sample metric improbably high | Use walk-forward or temporal split; check verify doesn't peek ahead |
| Overfitting to test set | Sharpe degrades immediately in production | Read-only eval data; prefer robustness-adjusted primaries |
| Rich verify output | Agent uses per-window details to guide next iteration | Verify prints one number; save rich output to disk for review only |

## COMP Configuration Checklist

Run this before starting the first LOOP. Each item is a single deterministic check — if any fails, fix the COMP before iterating. The whole list costs a few seconds and catches the mistakes that otherwise waste a 50-iteration budget.

**Artifact & schema**

- [ ] COMP created with `--status active` (not `draft`); `specflow artifact-lint COMP-NNN` reports no blocking findings
- [ ] `verify_command`, `metric_name`, and `metric_direction` are all set, and the direction matches what the verify number actually means
- [ ] Baseline metric from the dry-run recorded as the initial reference point

**Verify command**

- [ ] Dry-run exits 0 and prints exactly one parseable number matching `^-?[0-9]+\.?[0-9]*$`
- [ ] Safety screen clean — no `rm -rf /`, fork bombs, `curl ... | sh`, or embedded credentials
- [ ] Output is one number — rich diagnostics go to `--save-dir` (disk), not stdout
- [ ] (Skipped in quick mode ≤ 5) Noise probe: 3 back-to-back runs, stdev ≤ ~5% of mean

**Split integrity (anti-leakage)**

- [ ] Train/test partitions are disjoint — hash/`comm` intersection is empty
- [ ] Temporal boundary holds — no feature uses data at/after the split cutoff (`grep "shift(-"` returns nothing)
- [ ] `verify_command` reads only the evaluation partition, not the full dataset
- [ ] Eval data is read-only to the agent — file permissions, separate cwd, container isolation, or a documented convention

**Multi-criteria (if applicable)**

- [ ] One primary metric drives ranking; secondary concerns are guards (binary floors) or `auxiliary_metrics` (logged, not ranked)
- [ ] If using a weighted composite: weights frozen in `description`, every component logged as an `auxiliary_metric`, and at least one `guard_command` floor on the most safety-critical component

**Goals & boundaries**

- [ ] `goals`, `success_criteria`, and `constraints` capture the "why" and the rules of engagement (allowed data, forbidden techniques)
- [ ] `domain` set when known — triggers the expected `auxiliary_metrics` in lint
- [ ] Pre-check / post-check commands defined where the goal implies them, and each has passed a dry-run

## Post-Setup: Methodology Review

Before starting a LOOP, review the [ML Methodology Handbook](methodology-handbook.md) for practices tagged with your `COMP.domain`. This catches common setup mistakes (wrong CV scheme, missing baselines) before they waste budget.
