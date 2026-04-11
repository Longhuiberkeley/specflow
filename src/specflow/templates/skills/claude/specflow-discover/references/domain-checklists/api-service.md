# API Service Domain Checklist

Questions for backend services exposing REST, gRPC, GraphQL, or WebSocket APIs.

## API Design

1. **API style?** "REST with JSON is universally supported. gRPC for internal service-to-service with strong typing. GraphQL for flexible client queries. Which clients consume this API?"
2. **API versioning strategy?** "URL path versioning (`/v1/`) is simplest and most visible. Header-based is cleaner but less discoverable. Which fits your client ecosystem?"
3. **Authentication?** "API keys for service-to-service. OAuth 2.0 for user-facing. JWT for stateless verification. mTLS for zero-trust internal. Which threat model applies?"
4. **Rate limiting?** "Needed? Per-user, per-IP, or per-tier? What are acceptable rate limits for your use case?"

## Data & State

5. **Primary data operations?** "CRUD-heavy, read-heavy, write-heavy, or mixed? This shapes caching and indexing strategy."
6. **Data relationships?** "Simple flat records, relational with joins, or graph-like with traversals?"
7. **Idempotency?** "Do clients need safe retries? PUT is idempotent by spec. POST needs idempotency keys for safety."
8. **Pagination pattern?** "Offset-based for small datasets, cursor-based for large or real-time datasets. Expected page sizes?"

## Reliability

9. **Availability target?** "99.9% (8.7h downtime/year), 99.99% (52min/year), 99.999% (5min/year)? Each 9 adds significant operational cost."
10. **Timeout budgets?** "Acceptable latency for the slowest endpoint? Do you have upstream service dependencies with their own latency?"
11. **Circuit breaking?** "If an upstream service is down, should this API fail fast, degrade gracefully, or serve cached data?"
12. **Retry strategy?** "Exponential backoff with jitter is standard. Any operations that must NOT be retried (payments, email sends)?"

## Observability

13. **Logging standard?** "Structured JSON logs for machine parsing, or human-readable for development? Log levels and sampling policy?"
14. **Metrics?** "RED metrics (Rate, Errors, Duration) per endpoint. Custom business metrics needed?"
15. **Tracing?** "Distributed tracing needed? OpenTelemetry is the standard. Required if you have multi-service call chains."
16. **Health checks?** "Liveness (is it running?) and readiness (can it serve traffic?) probes needed?"

## Deployment

17. **Scaling model?** "Horizontal (add instances) or vertical (bigger machine)? Stateless services scale horizontally easily."
18. **Database strategy?** "Single primary, read replicas, or sharded? Connection pooling requirements?"
