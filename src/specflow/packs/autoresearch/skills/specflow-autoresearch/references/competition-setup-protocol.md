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

## Step 7 (Optional): Define Pre-Check and Post-Check Commands

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

### User decides strictness

Not every competition needs maximum leakage protection. Examples:

- **Quick prototype:** Single split, no guards, convention-only eval isolation. Fast iteration, accept that results are directional.
- **Production strategy:** Walk-forward primary, multi-guard, read-only eval via permissions. Higher quality, fewer iterations per hour.
- **Purged K-fold for finance:** Acceptable for many financial applications — it handles serial correlation while keeping most training data. User decides if the leakage from adjacent folds is tolerable for their regime.

The anti-leakage patterns are a menu of options. Pick what fits your domain and threat model.

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
