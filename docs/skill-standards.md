# SpecFlow Skill Standards

## Overview

Skills in SpecFlow are modular, self-contained packages that extend an AI agent's capabilities (like Claude Code or OpenCode) by providing specialized knowledge, workflows, and zero-token deterministic scripts. 

SpecFlow skills follow the **Progressive Disclosure** design principle to fiercely protect the LLM's context window.

## Anatomy of a SpecFlow Skill

A skill directory (e.g., `.claude/skills/specflow-discover/`) strictly contains:

```text
specflow-discover/
├── SKILL.md       # Required: Core instructions and triggers
├── references/    # Optional: Domain knowledge loaded ON DEMAND
└── scripts/       # Optional: Zero-token deterministic shell scripts
```

### 1. `SKILL.md` (The Core)
- **Frontmatter:** Must contain `name` and `description` in YAML. The `description` is the ONLY thing the agent reads to decide whether to trigger the skill. It must clearly state *when* to use it.
- **Body:** Contains imperative, high-level instructions for the workflow. It must be under 500 lines. It should NOT contain deep domain knowledge or large checklists.
- **Single Agent Persona:** SpecFlow does not use explicit personas (like "PM" or "Architect"). The skill simply guides the general agent to scale its ceremony based on the ambiguity of the user's request.

### 2. `references/` (Progressive Disclosure)
- Contains Markdown files with detailed constraints, large checklists, or schema examples.
- **Rule:** The agent only reads a file in `references/` if the `SKILL.md` instructs it to do so based on the current context (e.g., "If the user is building a web app, read `references/web-app-checklist.md`").

### 3. Deterministic Operations (Zero-Token)

SpecFlow is **Python-primary** (D-16/D-17): all deterministic logic lives in the `specflow` Python CLI (`src/specflow/lib/`). Skills do **not** bundle their own shell scripts for validation — they delegate to `specflow <cmd>` (e.g., `uv run specflow artifact-lint`, `specflow trace`, `specflow brief`).

- **Rule:** If a task is deterministic (validating links, computing SHA256 fingerprints, formatting an ID, computing waves), the AI MUST delegate it to a `specflow` CLI command rather than doing it via LLM tokens.
- CLI output is LLM-friendly (e.g., `Success: Validated 45 links`).
- A skill may carry a `scripts/` dir only for genuine per-skill tooling (today only `specflow-pack-author` does); the norm is delegation to the CLI.

> **Template layering:** what ships is `src/specflow/templates/skills/shared/<skill>/`; the live dogfood copy is `.claude/skills/<skill>/`. The two are kept byte-identical (mirror with rsync when editing); `specflow init`/`refresh` copy templates → each host's skill dir.
