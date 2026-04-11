# Data Pipeline Domain Checklist

Questions for ETL pipelines, data processing, streaming, and batch jobs.

## Data Flow

1. **Pipeline pattern?** "Batch (scheduled runs), streaming (continuous), or lambda architecture (both)? Batch is simpler, streaming adds operational complexity but lower latency."
2. **Data sources?** "Files (CSV, JSON, Parquet), databases (CDC, queries), APIs, message queues, logs? How many distinct sources?"
3. **Data sinks?** "Data warehouse, data lake, search index, API delivery, file export? One or multiple destinations?"
4. **Data volume?** "Per-run or per-day volume: MB, GB, TB? This determines processing framework and storage choices."

## Processing

5. **Transform complexity?** "Simple column mapping/renaming, aggregations, joins across sources, or complex ML feature engineering?"
6. **Schema handling?** "Fixed schema known upfront, schema evolution needed, or schema-on-read? How do you handle schema drift?"
7. **Late-arriving data?** "Can data arrive out of order or late? How late? Watermarks and windowing strategies needed?"
8. **Deduplication?** "Is duplicate data possible at the source? Idempotent processing or explicit dedup needed?"

## Reliability

9. **Exactly-once processing?** "Needed? At-least-once with idempotent sinks is simpler. Exactly-once requires transactional sinks or two-phase commit."
10. **Failure recovery?** "Restart from beginning of failed batch, resume from checkpoint, or reprocess from a timestamp? Checkpoint frequency?"
11. **Data quality checks?** "Schema validation, null checks, range checks, referential integrity? Fail the pipeline or quarantine bad records?"
12. **Monitoring?** "Lag metrics (how far behind real-time), throughput, error rate, data freshness? Alerting thresholds?"

## Operational

13. **Scheduling?** "Cron-based, event-driven, continuous, or manual trigger? Dependency management between pipeline stages?"
14. **Environment management?** "Dev, staging, production pipelines? How are pipeline configurations promoted between environments?"
15. **Backfill support?** "Need to reprocess historical data? Parameterized date ranges for reruns?"
16. **Secret management?** "Database credentials, API keys — where do pipeline jobs get their secrets? Vault, env vars, cloud secret manager?"
