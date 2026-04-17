---
name: specflow-init
description: Use when setting up SpecFlow in a new or existing project. Conversational bootstrap that scaffolds directories, installs hooks, generates CI workflows, and recommends next steps.
---

# SpecFlow Init

Conversational bootstrap for a SpecFlow project.

## Workflow

1. Ask the user about their project context:
   - "What type of project is this?" (e.g., Web App, CLI, Library, Firmware)
   - "Do you want to apply an industry standards preset?" (e.g., `iso26262-demo`, `default`, or "None")
   - "Which CI provider do you use?" (e.g., GitHub Actions, GitLab CI, or "None")
   - "Do you have any specific compliance standard packs you want to install?"
2. Run `uv run specflow init` with appropriate flags (e.g. `--preset <preset>`).
3. Install git hook via `uv run specflow hook install` to ensure pre-commit checks run.
4. If a CI provider was requested, generate CI workflow via `uv run specflow ci generate`.
5. Report what was scaffolded (directories, configurations, skills).
6. Recommend running `/specflow-discover` as the next step to start capturing requirements.

## Rules
- When offering the user choices for project type or presets, provide clear, bounded options.
- The preset option should default to "None" unless the user indicates a regulated industry.
- The CI option should be determined if they mention "GitHub" or "GitLab", otherwise default to "None".
- Every skill that offers the user a choice includes "(Recommended)" labels on the suggested default.
