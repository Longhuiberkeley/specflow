# AGENTS.md

## Welcome, AI Agents!

This repository contains the **SpecFlow** framework: a zero-database, filesystem-native, and scale-adaptive specification tracking tool designed to bridge agile workflows and ASPICE/ISO-compliant verification.

You are interacting with the framework's source code, NOT a project using the framework. Follow these guidelines while developing SpecFlow.

## Design Philosophy

### 1. The Repository IS the Database
Do not write logic that relies on a database. All specifications, work tracking, and states are managed via Markdown files with YAML frontmatter. The file tree is the ultimate source of truth.

### 2. Modeless & Scale-Adaptive
Ceremony adapts to ambiguity. SpecFlow has no "Tracks" (Quick/Standard/Enterprise) and no personas. 
When building features, assume a single generalized agent handles everything. If a user has a simple task, SpecFlow handles it with lean artifacts. If the task is complex, it scales up to full V-Model tracking. Avoid creating toggles, settings, or modes for this behavior.

### 3. Bring-Your-Own-Standard
SpecFlow does not ship with proprietary "Extension Packs" or gated industry standards. Instead, it relies on open YAML schema definitions. Users import their own standards (e.g., a PDF of ISO 26262 or an internal policy document), and SpecFlow parses them into executable compliance schemas.

### 4. Compliance as Code
We enforce compliance through CI/CD. Traceability matrices, linkage rules, and checklist requirements are validated locally by zero-token shell/Python scripts, not just by LLM inference. Ensure any new validation rule you add operates deterministically.

### 5. Context Efficiency (Skill Standards)
When writing AI skills for SpecFlow's internal agents (e.g., inside `.claude/skills/`), strictly adhere to the standards outlined in `docs/skill-standards.md`.
- Keep `SKILL.md` under 500 lines.
- Store domain knowledge in `references/`.
- Store deterministic operations in `scripts/`.

### 6. Ephemeral Local Execution (Like npx)
We do not install SpecFlow globally for users. Users will install it directly into their repository ephemerally using `uv run specflow install` to scaffold directories. Ensure scripts and instructions respect this local execution paradigm to avoid system-level pollution.


<!-- SpecFlow section (auto-generated, do not edit manually) -->
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

<!-- End SpecFlow section -->
