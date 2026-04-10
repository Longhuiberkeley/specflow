# SpecFlow Skill Standards

## Overview

Skills in SpecFlow are modular, self-contained packages that extend an AI agent's capabilities (like Claude Code or Gemini CLI) by providing specialized knowledge, workflows, and zero-token deterministic scripts. 

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

### 3. `scripts/` (Zero-Token Operations)
- Contains executable shell or Python scripts.
- **Rule:** If a task is deterministic (e.g., validating links, computing SHA256 fingerprints, formatting an ID), the AI MUST delegate it to a script rather than doing it via LLM tokens.
- Scripts must output clear, LLM-friendly stdout (e.g., `Success: Validated 45 links`).
