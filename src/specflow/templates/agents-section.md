## SpecFlow

This project uses **SpecFlow** — a spec-driven development framework. All specifications and work items are tracked as Markdown files with YAML frontmatter.

### Where artifacts live

- `_specflow/specs/` — V-model specification artifacts (requirements, architecture, design, tests)
- `_specflow/work/` — Agile delivery artifacts (stories, spikes, decisions, defects)
- `.specflow/` — Framework internals (config, schemas, impact log, baselines). **Do not edit manually.**

### Commands

| Command | Purpose |
|---------|---------|
| `specflow init` | Scaffold the project structure |
| `specflow status` | Show current phase, artifact counts, and issues |
| `specflow validate` | Run validation checks on all artifacts |

### How to work with SpecFlow

1. New requirements or features should be discussed as REQ artifacts in `_specflow/specs/requirements/`
2. Stories in `_specflow/work/stories/` link to specs via `links:` in YAML frontmatter
3. Status flows: `draft` → `approved` → `implemented` → `verified`
4. Never manually edit `.specflow/` internals — use CLI commands
