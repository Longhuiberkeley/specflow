# Web Application Domain Checklist

Questions for browser-based web applications.

## Frontend

1. **Framework preference?** "For your use case, React has the largest ecosystem, Vue is simpler to adopt, Svelte compiles smaller bundles. Any existing preference or constraint?"
2. **Rendering strategy?** "Server-side rendering (SSR) improves SEO and initial load. Client-side rendering (CSR) enables richer interactivity. Static generation (SSG) for content that rarely changes. Which fits your content?"
3. **Responsive requirements?** "Must the application work on mobile devices, or is desktop-only acceptable?"
4. **Accessibility requirements?** "Does this need to meet WCAG 2.1 AA or any specific accessibility standard?"
5. **Internationalization?** "Will this need to support multiple languages or locales?"

## Backend

6. **API style?** "REST is simpler and widely supported. GraphQL reduces over-fetching for complex data. gRPC for internal microservices. Which matches your client needs?"
7. **Real-time requirements?** "Do any features need live updates (WebSockets, SSE)? Chat, dashboards, collaborative editing?"
8. **File handling?** "Will users upload files? Size limits, storage backend (local, S3, CDN), processing needs?"
9. **Search requirements?** "Full-text search needed? Simple database LIKE queries work up to ~10K records. Elasticsearch for larger datasets."

## State & Data

10. **Session management?** "Cookie-based sessions are simpler. JWT is stateless but needs refresh token handling. OAuth if integrating with identity providers."
11. **Data volume?** "Expected order of magnitude for primary entities: hundreds, thousands, millions?"
12. **Data freshness?** "How stale can displayed data be? Real-time (<1s), near-real-time (<30s), eventual (<5min)?"

## Deployment

13. **Hosting environment?** "Cloud (AWS/GCP/Azure), on-premise, or hybrid? Any compliance restrictions on data residency?"
14. **CI/CD?** "Is there an existing pipeline, or does one need to be established?"
