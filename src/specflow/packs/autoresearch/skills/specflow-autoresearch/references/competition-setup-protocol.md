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

```bash
specflow create --type competition \
  --title "Track A: single split" \
  --verify-command "python scripts/track_a.py --strategy {strategy}" \
  --metric-name "Sharpe ratio" \
  --metric-direction "higher_is_better" \
  --guard-command "pytest tests/ -x" \
  --guard-mode "pass_fail"
```

If no guard is defined, the loop skips Phase 5.5 entirely.

## Step 6: Create the COMP Artifact

```bash
specflow create --type competition \
  --title "Track A: single split" \
  --verify-command "python scripts/track_a.py --strategy {strategy}" \
  --metric-name "Sharpe ratio" \
  --metric-direction "higher_is_better"
```

Record baseline metric from the dry-run as the initial reference point.

## Trust Boundary

`verify_command` is executed by the agent with full shell access. Only the project owner should create or edit COMP artifacts. Audit verify commands for safety before the first loop run — the agent trusts them blindly.

## Multi-Competition Pattern

A common pattern is to run two competitions against the same dataset with different evaluation rigor:

- **COMP-001 (Screener):** Fast evaluation (e.g., single in-sample split). Used for rapid exploration loops. Low iteration cost enables bold experimentation.
- **COMP-002 (Validator):** Rigorous evaluation (e.g., walk-forward out-of-sample). Used for validation loops. Confirms that screener findings generalize.

FINDs from COMP-001 inform LOOPs on COMP-002 when the user creates a LOOP with `mode: validate` and reads the screener's confirmed FINDs. The FIND schema's `applies_to` field indicates scope.

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Non-deterministic verify | Metric varies ±5% on same code | Pin seeds, flush caches, use deterministic test ordering |
| Metric diverges randomly | No clear improvement trend across iterations | Verify command depends on mutable state — isolate it |
| No split method documented | Results can't be reproduced | Document dataset, split method, and assets in COMP fields |
| Verify depends on network | Flaky results across runs | Mock external calls or use cached fixtures |
