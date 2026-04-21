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

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — Python package manager. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An AI coding assistant (Claude Code, Cursor, Gemini CLI, etc.)

## Install

```bash
# Install from GitHub
uv tool install git+https://github.com/Longhuiberkeley/specflow

# Or run without installing
uvx --from git+https://github.com/Longhuiberkeley/specflow specflow init

# Pin to a specific release
uv tool install git+https://github.com/Longhuiberkeley/specflow@v0.2.0
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
- [Authoring a pack](docs/authoring-a-pack.md) -- creating compliance packs
- [Authoring an adapter](docs/authoring-an-adapter.md) -- writing custom adapters

## For Power Users

You can invoke CLI commands directly for CI pipelines or when you prefer the terminal:

```bash
specflow init --platform claude-code
specflow status
specflow artifact-lint
specflow project-audit
```

See the [CLI reference](docs/cli-reference.md) for the full command catalog.

## SpecFlow vs. Traditional ALM Tools

SpecFlow is **not** a replacement for IBM DOORS, Siemens Polarion, or Jama Connect. Those tools serve a different audience — systems engineers working in dedicated web UIs with supply-chain-scale interchange workflows. SpecFlow serves **developers and AI assistants** who want compliance-grade rigor without leaving their repo.

Where SpecFlow fits:

| | Traditional ALM (DOORS, Polarion) | SpecFlow |
|---|---|---|
| **Home** | Web server / desktop client | Your git repository |
| **Interface** | Click-through web forms | `/specflow-*` slash commands + CLI |
| **CI** | External integration, often manual | Native — `artifact-lint` in CI, zero tokens |
| **AI** | Limited or none | 14 AI coding platforms, skill-first design |
| **Setup** | Server provisioning, licenses | `uv run specflow init` — one command |
| **Audience** | Systems engineers, compliance officers | Developers, AI assistants, small teams |

SpecFlow complements traditional ALM through **ReqIF import/export** (already built) — teams can exchange requirements with DOORS/Polarion users while keeping their own workflow in the repo.

## Directory Layout

After running `/specflow-init`, two directories appear in your repo:

| Directory | Purpose | Edit? |
|-----------|---------|-------|
| `_specflow/` | Your specs and work items — requirements, architecture, stories, decisions, defects | Yes — this is your workspace |
| `.specflow/` | Framework internals — config, schemas, baselines, impact logs, checklists | No — managed by CLI commands |

Everything is plain Markdown + YAML frontmatter. Your repo IS the database. See [architecture](docs/architecture.md) for the full directory tree.

## Roadmap

**v0.2.0 is the current release** — 10 slash commands, zero-token validation engine, V-model traceability, ReqIF import/export, RBAC, baselines, dedup, and 14 platform support.

Next up: compliance preset packs, evidence reports, and deeper gap analysis (v0.3.0).

See [ROADMAP.md](ROADMAP.md) for the full plan and [CHANGELOG.md](CHANGELOG.md) for what shipped in each version.

## License

MIT
