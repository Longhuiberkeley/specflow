# Cross-Cutting Concerns Checklist

Fire only relevant items based on project type. Skip items marked with `— skip if <condition>`.

## Error Handling

- **Error propagation:** "How should errors surface to users? Error codes with messages, structured error responses, or exception hierarchies?" — skip if CLI tool (usually stderr + exit code)
- **Error recovery:** "Should the system retry transient failures automatically? If so, what's the retry budget (max attempts, backoff)?" — skip if library (consumer decides)
- **Error boundaries:** "If one component fails, should the whole system fail or degrade gracefully? What's the minimum viable functionality?"

## Security

- **Authentication:** "How do users prove their identity?" — skip if CLI tool (usually OS-level auth), skip if data pipeline (usually service accounts)
- **Authorization:** "Once authenticated, what are users allowed to do? Role-based, attribute-based, or ACL-based?" — skip if single-user tool
- **Data at rest:** "Does sensitive data need encryption at rest? What's considered sensitive in this system?" — skip if library (consumer stores data)
- **Data in transit:** "TLS for all communications? Certificate management strategy?" — skip if local-only CLI
- **Input validation:** "Where are the trust boundaries? External input must be validated; internal calls can be trusted."
- **Secrets management:** "Where do API keys, tokens, and credentials live? Environment variables, vault, cloud secret manager?"

## Observability

- **Logging:** "What events need logging? Structured (JSON) or unstructured? Log level policy (what's INFO vs DEBUG vs WARN)?" — skip if library (consumer logs)
- **Metrics:** "What's the health of the system? RED metrics (Rate, Errors, Duration) per operation. Custom business metrics?" — skip if library
- **Alerting:** "What conditions warrant immediate human attention? PagerDuty vs Slack notification vs log-only?"
- **Tracing:** "Can you follow a request end-to-end? Distributed tracing with correlation IDs?" — skip if single-process tool

## Scalability

- **Expected load:** "Current users and projected growth. Requests per second, concurrent users, data volume per time unit." — skip if library
- **Bottleneck identification:** "CPU-bound, I/O-bound, memory-bound, or network-bound? This shapes scaling strategy."
- **Scaling strategy:** "Scale up (bigger machine) or scale out (more machines)? Stateless services scale out easily."
- **Caching:** "What data is read-heavy and rarely changes? Cache at what layer (application, CDN, database)?"

## Deployment & Operations

- **Deployment frequency:** "How often will this be deployed? Continuous, daily, weekly, monthly?" — skip if library
- **Rollback strategy:** "If a deployment fails, how quickly can you revert? Blue-green, canary, or rolling updates?" — skip if library or CLI
- **Configuration management:** "How do you manage environment-specific config (dev/staging/prod)? Feature flags needed?"
- **Database migrations:** "How are schema changes managed? Forward-only migrations with rollback scripts?" — skip if no database
