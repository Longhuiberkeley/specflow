## SpecFlow

This project uses **SpecFlow** — a spec-driven development framework.
All specifications and work items are tracked as Markdown + YAML frontmatter.
The primary interface is `/specflow-*` slash commands in your AI assistant.

### Where Artifacts Live

- `_specflow/specs/` — V-model specification artifacts (requirements, architecture, design, tests)
- `_specflow/work/` — Agile delivery artifacts (stories, spikes, decisions, defects)
- `.specflow/` — Framework internals (config, schemas, impact log, baselines). **Do not edit manually.**

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/specflow-init` | Bootstrap project structure, install skills, optional CI |
| `/specflow-discover` | Capture requirements through guided conversation |
| `/specflow-plan` | Break approved REQs into architecture + stories |
| `/specflow-execute` | Implement stories with test generation |
| `/specflow-artifact-review` | Quality review of specific artifacts |
| `/specflow-change-impact-review` | Blast-radius review of recent commits/PRs |
| `/specflow-audit` | Full-project periodic health check |
| `/specflow-ship` | Release: baseline + change records + quick audit |
| `/specflow-pack-author` | Author a standards compliance pack |

### Skills vs CLI

| Interface | When to Use | Example |
|-----------|-------------|---------|
| **Skills** (`/specflow-*`) | Interactive work in your AI assistant | `/specflow-discover` |
| **CLI** (`specflow <cmd>`) | CI pipelines, automation, terminal | `specflow artifact-lint` |

Skills compose CLI commands internally. You can always use the CLI directly when you prefer the terminal or need automation.

### Lifecycle Flow

```
init → discover → plan → execute → artifact-review → ship
                                    ├── audit (periodic health check)
                                    └── change-impact-review (per-commit/PR)
```

### Artifact Status Lifecycle

When working with artifacts, **always update their status** as work progresses:

| Trigger | Action | Command |
|---------|--------|---------|
| Creating a new artifact | Set `status: draft` | `specflow create --type <type> --status draft` |
| User approves the artifact | Update to `status: approved` | `specflow update <ID> --status approved` |
| Code implementing the artifact is written | Update to `status: implemented` | `specflow update <ID> --status implemented` |
| Tests pass and review is complete | Update to `status: verified` | `specflow update <ID> --status verified` |

When implementing stories via `/specflow-execute`, also update linked ARCH and DDD artifacts to `implemented` once the code that realizes them is written. Do not wait for the story to be fully complete -- update spec status as the corresponding code lands.

### Working Principles

- **Trace before implement.** Every code change traces to a STORY or REQ. No orphan work.
- **Evidence over claims.** "Verified" means an artifact proves it — run the checks, don't assume.
- **State assumptions explicitly.** If uncertain, ask rather than silently picking an interpretation.
- **Fail early.** Run `specflow artifact-lint` after changes, not at release time.
- **Surgical changes.** Touch only what the request requires. Match existing conventions.
- **Label defaults.** When offering choices, mark the suggested option with "(Recommended)".
- **Escape hatches.** If the user says "move on" or "skip", proceed with what you have.

### Conventions

- Status flow: `draft` → `approved` → `implemented` → `verified`
- Stories link to specs via `links:` in YAML frontmatter
- `.specflow/` internals are managed by CLI commands — never edit manually
- Use `specflow update <ID>` for all status transitions and frontmatter changes
- Run `specflow artifact-lint` after creating or updating artifacts
