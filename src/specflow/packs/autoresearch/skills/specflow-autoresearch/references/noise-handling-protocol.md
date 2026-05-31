# Noise Handling Protocol

When to read: during Phase 5 of `autonomous-loop-protocol.md`, only when the COMP metric is volatile (benchmark times, ML accuracy, financial metrics). For deterministic metrics (test coverage %, bundle size in bytes), skip this file entirely — single-run verification is sufficient.

Some metrics are inherently noisy. A single measurement can mislead: a "kept" decision may be noise, a "discard" may be a real improvement hidden under variance. But BEFORE picking a noise strategy, validate that the EXPT itself was even valid.

## EXPT Validity Gate (mandatory before noise strategy selection)

Not all noisy results deserve noise handling. Some EXPTs are so fundamentally broken that noise handling would just polish garbage. Apply this gate first:

| Check | Question | If fail |
|-------|----------|---------|
| **Execution integrity** | Did the verify command run to completion without errors? | If crash/error, this is a crash-recovery situation — see crash-recovery-protocol. Noise handling does not apply. |
| **Parameter validity** | Were the intended parameters actually applied? (Check logs for silent config overwrites, YAML parsing errors, default fallbacks) | If parameters were silently wrong, the EXPT is invalid. Log as `design_quality: 1` and discard. Do NOT run noise handling. |
| **Data integrity** | Is the input data identical to what was expected? (Check row counts, date ranges, file hashes) | If data drifted or was truncated, the EXPT is testing a different condition than intended. Log as invalid. |
| **Baseline comparability** | Is the baseline metric from the same code snapshot / environment? | If the environment changed (new dependency version, different hardware, different seed convention), the delta may be an artifact. Flag with `environment_note`. |

Only after ALL four checks pass should you apply the noise strategies below. An EXPT that fails the validity gate is not "noisy" — it's invalid. Log it, extract the lesson (per Phase 6.6), and move on.

## Strategy 1: Multi-Run Verification

```bash
# Median of 3 runs (reliable for moderately noisy metrics):
for i in 1 2 3; do
  <verify_command> 2>&1 | <extract_pattern>
done | sort -n | sed -n '2p'
```

## Strategy 2: Minimum Improvement Threshold

Ignore improvements smaller than the noise floor. If metric improved but `delta < noise_threshold`, treat as discard. Prevents keeping noise as if it were signal.

## Strategy 3: Confirmation Run

```
IF metric_improved:
    second_metric = run_verify()
    IF abs(second_metric - first_metric) / first_metric < 0.01:
        STATUS = "keep"     # confirmed — both runs agree
    ELSE:
        STATUS = "discard"  # first result was noise
```

## Strategy 4: Environment Pinning

```bash
# Pin random seeds for ML/statistical workloads
PYTHONHASHSEED=42 python train.py --seed 42

# Deterministic test ordering
pytest -p no:randomly

# Flush caches before benchmarking
redis-cli FLUSHALL 2>/dev/null; <verify_command>
```

## When to Use Each Strategy

| Metric Type | Noise Level | Strategy |
|-------------|-------------|----------|
| Test coverage (%) | None | No special handling |
| Bundle size (bytes) | None | No special handling |
| Benchmark time (ms) | Medium | Multi-run median (3 runs) |
| ML training loss | High | Environment pinning + confirmation run |
| Financial metrics (Sharpe, etc.) | High | Warm-up + multi-run + min-delta |

## Preventing Premature Rollbacks

When a metric seems worse but could be noise:

```
IF metric_worse AND abs(delta) < noise_floor:
    second_result = run_verify()
    IF second_result also worse:
        STATUS = "discard"
    ELSE:
        STATUS = "keep"
        LOG "NOISE: initial regression not confirmed on re-run"
```

## Noise Probe at Setup Time

During COMP setup (`specflow autoresearch plan --profile`), the noise variance probe runs `verify_command` three times on the unchanged baseline and reports min/max/mean/stdev. If stdev > ~5% of mean, the metric is noisy enough that you MUST pick one of the strategies above before committing a long budget. Record the chosen strategy in `COMP.noise_characterization`.
