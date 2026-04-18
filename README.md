# SpecFlow

I built SpecFlow because I saw a gap opening up. AI coding assistants are fast enough now that traditional agile rituals -- standups, sprint planning, backlog grooming -- are becoming the bottleneck, not the code. But V-model and waterfall, while rigorous, were designed for a world where humans wrote every line. We need compliance-grade rigor at AI speed.

The beauty of process engineering is that it offsets individual talent and responsibility to a system. A good framework increases safety and reliability regardless of who is writing the code. This is why automotive (ASPICE), aerospace (DO-178C), and medical (IEC 62304) industries mandate structured verification -- not because they love paperwork, but because the system catches what individuals miss.

I believe spec-driven AI development is going mainstream for this reason. The speed of AI coding demands the structure of compliance engineering. 

SpecFlow is my attempt at an easy-to-use agentic framework with a small set of `/skills` that make it easy to start and easy to scale. Inspired by compliance-as-code, I want to enable **vibe-compliance**: the same way vibe-coding lets you build by intent, vibe-compliance lets you verify by intent. Vibe-ASPICE, vibe-SOC2, vibe-ISO26262, vibe-DO-178C -- the framework handles the ceremony so you can focus on the decisions.

**10 slash commands. No database. No cloud. Your repo IS the compliance artifact.**

## Why SpecFlow?

**Zero-database, zero-cloud, zero-lock-in.** Your repository IS the compliance artifact. Every spec, traceability link, and audit record lives in Markdown + YAML — version-controlled, diffable, and auditable by humans and CI alike.

- **Seamless onboarding.** One command (`/specflow-init`) scaffolds everything. No servers to provision, no accounts to create, no web UI to learn. Your AI assistant already knows what to do.
- **Scale-adaptive ceremony.** Fixing a typo? SpecFlow stays out of your way. Building a safety-critical subsystem? Full V-model traceability activates automatically. No toggles, no modes — the framework reads the room.
- **Compliance as code, not paperwork.** Traceability matrices, linkage rules, and phase-gate checklists run as deterministic Python in CI — zero LLM tokens, zero guesswork. Compliance evidence is generated from your git history on demand.
- **Bring-your-own-standard.** Feed SpecFlow a PDF, URL, or pasted text from ISO 26262, DO-178C, SOC 2, or your internal policy. It extracts clauses into executable compliance schemas. No proprietary extension packs.
- **14 AI coding platforms.** Works with Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, GitHub Copilot, Roo Code, and more — today. The skill layer is portable by design.
- **Built for AI speed.** Token budgets, progressive disclosure, subagent isolation, and zero-token programmatic validation mean your AI assistant spends tokens on decisions, not bookkeeping.

## Quick Start

Open your AI coding assistant and run:

```
/specflow-init
```

Then:

```
/specflow-discover → /specflow-plan → /specflow-execute → /specflow-ship
```

Each slash command is a guided conversation -- the AI assistant handles the ceremony, you make the decisions.

Read the **[getting-started guide](docs/getting-started.md)** for a full walkthrough.

## Skills vs CLI

SpecFlow has two interfaces that work together:

| Interface | When | Example |
|-----------|------|---------|
| **Skills** (`/specflow-*`) | Interactive work in your AI assistant | `/specflow-discover` |
| **CLI** (`specflow <cmd>`) | CI pipelines, automation, terminal | `specflow artifact-lint` |

Skills compose CLI commands under the hood. Use skills for day-to-day work; use the CLI for automation and CI.

## The 10 Slash Commands

| Command | Purpose |
|---------|---------|
| `/specflow-init` | Bootstrap project, install skills, optional CI |
| `/specflow-discover` | Capture requirements through conversation |
| `/specflow-plan` | Break REQs into architecture + stories |
| `/specflow-execute` | Implement stories with test generation |
| `/specflow-artifact-review` | Quality review of specific artifacts |
| `/specflow-change-impact-review` | Blast-radius review of recent changes |
| `/specflow-audit` | Full-project periodic health check |
| `/specflow-ship` | Release: baseline + change records + audit |
| `/specflow-pack-author` | Author a standards compliance pack |
| `/specflow-adapter` | Manage CI, exchange, standards ingestion, team RBAC |

## Install

```bash
# Install from GitHub (requires uv)
uv tool install git+https://github.com/Longhuiberkeley/specflow

# Or run without installing
uvx --from git+https://github.com/Longhuiberkeley/specflow specflow init

# Pin to a specific release
uv tool install git+https://github.com/Longhuiberkeley/specflow@v0.1.0
```

Supports 14 AI coding platforms: Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, GitHub Copilot, Roo Code, QwenCoder, Kiro, KiloCoder, Codex, Trae, and Junie.

## Learn More

- [Getting started](docs/getting-started.md) -- tutorial walkthrough
- [Lifecycle overview](docs/lifecycle.md) -- flowchart and command tiers
- [Command reference](docs/commands.md) -- per-skill interface spec
- [CLI reference](docs/cli-reference.md) -- raw CLI commands for power users and CI
- [Architecture](docs/architecture.md) -- technical design
- [Design decisions](docs/decisions.md) -- resolved trade-offs
- [Team setup](docs/team-setup.md) -- RBAC and role-based access control

## For Power Users

You can invoke CLI commands directly for CI pipelines or when you prefer the terminal:

```bash
specflow init --platform claude-code
specflow status
specflow artifact-lint
specflow project-audit
```

See the [CLI reference](docs/cli-reference.md) for the full command catalog.

## Roadmap

SpecFlow ships incrementally. Here's what's live and what's coming:

| Status | Release | What's Included |
|--------|---------|-----------------|
| **Live** | v0.1.0 | Scaffolding (`init`), manual specification, zero-token validation engine, 10 slash commands |
| **Next** | v0.2.0 | Full AI lifecycle: discovery conversations, traceability (fingerprints, impact analysis), execution orchestration, context-specific review |
| **Planned** | v0.3.0 | Compliance-ready: LLM-assisted pack authoring from PDF/URL/text, standards gap analysis, baselines |
| **Planned** | v1.0.0 | Team-ready: git-based RBAC, defect lifecycle, draft ID renumbering, CI integration, test records |
| **Future** | v1.x | Intelligence: 3-tier deduplication, dead-code and similarity detection, prevention pattern learning |

See the [implementation plan](docs/plan.md) for the full phase breakdown.

## License

MIT
