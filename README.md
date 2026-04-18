# SpecFlow

I built SpecFlow because I saw a gap opening up. AI coding assistants are fast enough now that traditional agile rituals -- standups, sprint planning, backlog grooming -- are becoming the bottleneck, not the code. But V-model and waterfall, while rigorous, were designed for a world where humans wrote every line. We need compliance-grade rigor at AI speed.

The beauty of process engineering is that it offsets individual talent and responsibility to a system. A good framework increases safety and reliability regardless of who is writing the code. This is why automotive (ASPICE), aerospace (DO-178C), and medical (IEC 62304) industries mandate structured verification -- not because they love paperwork, but because the system catches what individuals miss.

I believe spec-driven AI development is going mainstream for this reason. The speed of AI coding demands the structure of compliance engineering. Not because you love process -- because you want to ship fast and sleep at night.

SpecFlow is my attempt at an easy-to-use agentic framework with a small set of `/skills` that make it easy to start and easy to scale. Inspired by compliance-as-code, I want to enable **vibe-compliance**: the same way vibe-coding lets you build by intent, vibe-compliance lets you verify by intent. Vibe-ASPICE, vibe-SOC2, vibe-ISO26262, vibe-DO-178C -- the framework handles the ceremony so you can focus on the decisions.

**9 slash commands. No database. No cloud. Your repo IS the compliance artifact.**

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

## The 9 Slash Commands

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

## Install

```bash
# Install from GitHub (requires uv)
uv tool install git+https://github.com/anomalyco/specflow

# Or run without installing
uvx --from git+https://github.com/anomalyco/specflow specflow init

# Pin to a specific release
uv tool install git+https://github.com/anomalyco/specflow@v0.1.0
```

Supports 14 AI coding platforms: Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, GitHub Copilot, Roo Code, QwenCoder, Kiro, KiloCoder, Codex, Trae, and Junie.

## Learn More

- [Getting started](docs/getting-started.md) -- tutorial walkthrough
- [Lifecycle overview](docs/lifecycle.md) -- flowchart and command tiers
- [Command reference](docs/commands.md) -- per-skill interface spec
- [CLI reference](docs/cli-reference.md) -- raw CLI commands for power users and CI
- [Architecture](docs/architecture.md) -- technical design
- [Design decisions](docs/decisions.md) -- resolved trade-offs

## For Power Users

You can invoke CLI commands directly for CI pipelines or when you prefer the terminal:

```bash
specflow init --platform claude-code
specflow status
specflow artifact-lint
specflow project-audit
```

See the [CLI reference](docs/cli-reference.md) for the full command catalog.

## License

MIT
