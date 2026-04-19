# SpecFlow Lifecycle

The user journey from cold clone to shipped feature, driven by 10 Tier 1 slash commands.

## Lifecycle Flowchart

```
                        ┌───────────────┐
                        │  cold clone   │
                        └───────┬───────┘
                                ▼
                /specflow-init (preset? CI? standards?)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                              ▼
      ┌───────────────────┐          ┌────────────────────┐
      │  lean path        │          │  full path         │
      │  (simple change)  │          │  (new capability)  │
      └─────────┬─────────┘          └──────────┬─────────┘
                ▼                               ▼
       /specflow-discover               /specflow-discover
          (1 exchange)                   (multi-exchange;
                │                         readiness gate)
                │     REQ.status=approved                │
                ▼                               ▼
       /specflow-plan                   /specflow-plan
          (just STORY)                   (ARCH → DDD → STORY)
                │                               │
                │     STORY.status=approved     │
                ▼                               ▼
       /specflow-execute                /specflow-execute
          (impl + UT/IT/QT, parallel waves via specflow go)
                                │
                                ▼
                /specflow-artifact-review
                (deterministic lint + checklist + LLM review)
                                │
         ┌──────────────────────┼──────────────────────┬──────────────────────┐
         ▼                      ▼                      ▼                      ▼
  iterate again      /specflow-change-        /specflow-audit        /specflow-adapter
                     impact-review             (periodic; full-project  (configure CI, roles,
                     (per-commit/PR;            health check; produces   adapters at any time)
                      blast-radius              AUD + CHL artifacts)
                      analysis)                         │
                                │                        │
                                └───────────┬────────────┘
                                            ▼
                                    /specflow-ship
                                    (baseline + DECs + quick audit)
```

## Tier 1 — Slash Commands (the product)

These are what a user learns and uses day-to-day. Each is documented in [commands.md](commands.md) with a full interface spec.

| # | Slash Command | When to Use |
|---|---------------|-------------|
| 1 | `/specflow-init` | Starting a new project; installing skills, packs, CI |
| 2 | `/specflow-discover` | Capturing a new requirement through conversation |
| 3 | `/specflow-plan` | Breaking approved REQs into architecture + stories |
| 4 | `/specflow-execute` | Implementing approved stories with test generation |
| 5 | `/specflow-artifact-review` | Quality review of one or more specific artifacts |
| 6 | `/specflow-change-impact-review` | Blast-radius review of recent commits/PRs |
| 7 | `/specflow-audit` | Periodic full-project health check |
| 8 | `/specflow-ship` | Cutting a release: baseline + change records + quick audit |
| 9 | `/specflow-pack-author` | Authoring a standards compliance pack |

## CLI Reference for Power Users

The slash commands above compose underlying CLI commands (`uv run specflow ...`) behind the scenes. Power users and CI pipelines can invoke these directly. See the [CLI Reference](cli-reference.md) for the full catalog organized by workflow phase.
