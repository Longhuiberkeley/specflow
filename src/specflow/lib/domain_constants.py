"""Shared domain constants for autoresearch and linting."""

# Domain-recommended auxiliary metrics for EXPT logging.
# Used by both autoresearch.py (plan --profile) and artifact_lint.py (autoresearch-logging check).
DOMAIN_RECOMMENDED: dict[str, list[str]] = {
    "quant": ["max_drawdown", "total_trades", "win_rate", "profit_factor", "oos_decay"],
    "ml": ["val_loss", "learning_rate", "batch_size", "epochs", "architecture"],
    "nlp": ["perplexity", "token_count", "rouge_l", "bertscore_f1"],
    "systems": ["p50_latency_ms", "p99_latency_ms", "memory_mb", "throughput_rps"],
    "safety_critical": ["false_positive_rate", "false_negative_rate", "precision", "recall"],
}
