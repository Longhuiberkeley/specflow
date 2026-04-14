# SpecFlow Lifecycle

The user journey from cold clone to shipped feature, side-by-side with the command surface that realizes it.

## Lifecycle flowchart

```
                        ┌───────────────┐
                        │  cold clone   │
                        └───────┬───────┘
                                ▼
                /specflow-init (preset? CI? standards?)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
      ┌───────────────────┐         ┌────────────────────┐
      │  lean path        │         │  full path         │
      │  (simple change)  │         │  (new capability)  │
      └─────────┬─────────┘         └──────────┬─────────┘
                ▼                              ▼
       /specflow-discover              /specflow-discover
          (1 exchange)                   (multi-exchange;
                │                         readiness gate)
                │     REQ.status=approved                 │
                ▼                              ▼
       /specflow-plan                  /specflow-plan
          (just STORY)                   (ARCH → DDD → STORY)
                │                              │
                │     STORY.status=approved    │
                ▼                              ▼
       /specflow-execute               /specflow-execute
          (impl + UT/IT/QT, parallel waves via specflow go)
                                │
                                ▼
                /specflow-artifact-review
                (deterministic lint + checklist + LLM +
                 optional adversarial lenses; auto-runs
                 dedup + similarity internally)
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
  iterate again        /specflow-release     /specflow-change-
                       (baseline +            impact-review
                        document-changes +    (per-commit/PR;
                        project-audit)         only unreviewed DECs)
                                │
                                ▼
                       /specflow-project-audit
                       (periodic; scope + depth chosen conversationally;
                        composes subagent fan-out)
```

## Tiered command table

### Tier 1 — featured user-facing skills

These are what a user learns and uses day-to-day. Each is documented in [commands.md](commands.md) with full interface spec.

| Skill | When to use |
|---|---|
| `/specflow-init` | Starting a new project; installing a standards pack |
| `/specflow-discover` | Capturing a new requirement |
| `/specflow-plan` | Breaking an approved REQ into architecture + stories |
| `/specflow-execute` | Implementing approved stories |
| `/specflow-artifact-review` | Reviewing one or more artifacts for quality |
| `/specflow-project-audit` | Periodic full-project health check |
| `/specflow-document-changes` | Emitting DEC records from git history (readable by humans) |
| `/specflow-change-impact-review` | Reviewing unreviewed DECs with LLM + blast-radius analysis |
| `/specflow-release` | Cutting a release: baseline + document-changes + quick audit |
| `/specflow-pack-author` | LLM-assisted authoring of a standards pack |

### Tier 2 — CLI commands available via the thin `/cmd [optional message]` skill wrapper pattern

These are reachable by chat but not featured; use when composed from Tier 1 or invoked explicitly.

`specflow baseline`, `specflow status`, `specflow create`, `specflow update`, `specflow go`, `specflow done`, `specflow fingerprint-refresh`, `specflow renumber-drafts`, `specflow import`, `specflow export`, `specflow hook`.

### Tier 3 — CLI-only, intended for CI or power users

No headline skill. Invoked from `specflow` directly or from CI workflows.

`specflow artifact-lint`, `specflow checklist-run`, `specflow detect {dead-code,similarity}`.
