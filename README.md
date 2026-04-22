# SpecFlow

**Compliance-grade spec tracking, without the portal.**
Your git repo is the ALM. Your AI assistant is the UI.

Traditional ALM asks you to leave your editor, log into a website, and click through forms. SpecFlow doesn't. Every requirement, architecture doc, test, and audit record lives in Markdown in your repo — diffable, reviewable, CI-validated, yours.

## Why this exists

Old-school ALM tools were built for a world where humans typed every line. They made sense when writing code was slow and ceremony was cheap. AI coding assistants flipped that: the code comes out fast, and the ritual is the bottleneck.

SpecFlow keeps the rigor (V-model traceability, impact analysis, audit baselines, standards packs) and drops the parts that slow teams down (servers, licenses, portals, click-through workflows). It runs wherever your AI assistant runs — Claude Code, Cursor, Cline, and 11 others.

## Feel it in 30 seconds

```bash
$ uv tool install git+https://github.com/Longhuiberkeley/specflow
```

Then, inside your AI assistant:

```
> /specflow-init
   Detects platform, scaffolds _specflow/ and .specflow/, offers CI wiring.

> /specflow-discover  "Add SSO to our customer portal"
   Guided conversation. Surfaces hidden assumptions. Writes REQ-001..003
   as Markdown in _specflow/specs/.

> /specflow-plan
   Proposes architecture, decomposes into stories, creates ARCH/DDD/STORY
   artifacts with V-model links in place.

> specflow status
   SpecFlow Status
   ──────────────────────────────────────────────────
     Phase:     planning
     Project:   my-portal
     Specs:     3 REQ | 2 ARCH | 4 DDD | 0 UT | 0 IT | 0 QT
     Work:      7 STORY | 0 SPIKE | 0 DEC | 0 DEF
     Coverage:  REQ 100% (3/3) | Chain 80% (4/5)
     → Run /specflow-execute to start implementing
```

The whole workflow is a conversation, not a portal. Everything you see above is a file you can `git diff`.

## Quick start

**Prerequisites:** [uv](https://docs.astral.sh/uv/) + any supported AI coding assistant.

```bash
uv tool install git+https://github.com/Longhuiberkeley/specflow
```

Open your assistant, point it at your repo, and run `/specflow-init`. That's it. Full walkthrough in the [getting-started guide](docs/getting-started.md).

## What you get

| Feature | How |
|---------|-----|
| **Zero-token CI validation** | Schema, links, status, fingerprints, coverage — deterministic Python, no LLM required |
| **V-model traceability** | REQ → ARCH → DDD → UT/IT/QT, fully linked and linted |
| **Bring-your-own-standard** | Drop a PDF, URL, or pasted text. SpecFlow extracts clauses into compliance schemas |
| **Immutable baselines** | Snapshot, diff, and generate audit evidence between releases |
| **Runs in 14 AI assistants** | Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, Copilot, Roo, QwenCoder, Kiro, KiloCoder, Codex, Trae, Junie |
| **1 runtime dependency** | Just `pyyaml`. Everything else is stdlib. |

## The 10 slash commands

| Command | What it does |
|---------|---------|
| `/specflow-init` | Bootstrap the project, install skills, wire CI |
| `/specflow-discover` | Capture requirements through conversation |
| `/specflow-plan` | Break REQs into architecture + stories |
| `/specflow-execute` | Implement stories with test generation |
| `/specflow-artifact-review` | Deep review of a specific artifact |
| `/specflow-change-impact-review` | Blast-radius review of recent changes |
| `/specflow-audit` | Periodic full-project health check |
| `/specflow-ship` | Release: baseline + change records + audit |
| `/specflow-pack-author` | Author a standards compliance pack |
| `/specflow-adapter` | CI, exchange (ReqIF), standards, team RBAC |

All 10 skills accept freeform context. `/specflow-audit I'm worried about REQ coverage` scopes the audit to your concern.

## Philosophy

- **Your git repo is the database.** No SQLite, no PostgreSQL, no server. The filesystem is authoritative.
- **Zero tokens for CI.** All validation is deterministic Python. LLMs are opt-in at the skill layer, never required for gatekeeping.
- **Bring your own standard.** We don't ship copyrighted packs. Feed SpecFlow your own ISO 26262 / ASPICE / policy PDF and it extracts clauses.
- **Skills over clicks.** The user-facing interface is `/specflow-*` commands in your assistant. The CLI underneath is for CI, scripts, and power users.

> `#vibe-compliance` — if vibe-coding lets you build by intent, vibe-compliance lets you verify by intent. SpecFlow handles the ceremony so you can focus on the decisions.

## ALM, but make it friendly

DOORS and Polarion exist because compliance is real. They solved a real problem — requirements management at scale for regulated industries — and they're still the right answer for some teams. What they ask in return is a server, a license, a login, and a click-through workflow for every edit.

SpecFlow is for teams that want the rigor without the portal tax.

| | Traditional ALM | SpecFlow |
|---|---|---|
| **Home** | Web server / desktop client | Your git repository |
| **Interface** | Browser forms | `/specflow-*` in your AI assistant |
| **CI** | External integration | Native — `artifact-lint` runs in your existing pipeline |
| **AI** | Bolted on, if at all | 14 assistants, skill-first design |
| **Setup** | Servers, licenses, admins | `uv tool install` — one command |
| **Lock-in** | Proprietary database | Markdown + YAML + git |

Already on DOORS or Polarion? SpecFlow speaks **ReqIF 1.2** both ways for supply-chain interchange.

## Skills vs. CLI

Most users only see the slash commands. The raw CLI sits underneath for CI and automation.

```bash
specflow init --platform claude-code
specflow status
specflow artifact-lint
specflow project-audit
```

Full reference: [CLI reference](docs/cli-reference.md). 30 subcommands.

## Directory layout

After `/specflow-init`, two directories appear:

| Directory | Purpose | Edit? |
|-----------|---------|-------|
| `_specflow/` | Your specs and work items | Yes — your workspace |
| `.specflow/` | Framework internals (config, schemas, baselines) | No — managed by CLI |

Everything is Markdown with YAML frontmatter. Your repo is the database.

## Install

```bash
# Latest
uv tool install git+https://github.com/Longhuiberkeley/specflow

# Run without installing
uvx --from git+https://github.com/Longhuiberkeley/specflow specflow init

# Pin to a release
uv tool install git+https://github.com/Longhuiberkeley/specflow@v1.0.0
```

## Docs

- [Getting started](docs/getting-started.md) — tutorial walkthrough
- [Lifecycle overview](docs/lifecycle.md) — flowchart and command tiers
- [Command reference](docs/commands.md) — per-skill interface spec
- [CLI reference](docs/cli-reference.md) — raw CLI for CI
- [Architecture](docs/architecture.md) — technical design
- [Design decisions](docs/decisions.md) — resolved trade-offs
- [Team setup](docs/team-setup.md) — RBAC and role-based access
- [Authoring a pack](docs/authoring-a-pack.md) — creating compliance packs

## Roadmap

[ROADMAP.md](ROADMAP.md) for the full plan. [CHANGELOG.md](CHANGELOG.md) for release history.

## Not to be confused with

SpecFlow here is a Python-based spec-driven development framework for filesystem-native specification tracking. It is **not** affiliated with:

- **SpecFlow for .NET** ([specflow.org](https://specflow.org)) — a BDD framework for .NET by Tricentis. If you're looking for .NET BDD testing, you want them.
- **SpecStoryAI** ([github.com/specstoryai/specflow](https://github.com/specstoryai/specflow)) — an AI-powered development tool.

## License

MIT
