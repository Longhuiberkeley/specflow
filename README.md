# SpecFlow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-managed-purple.svg)](https://docs.astral.sh/uv/)

TLDR: I want to make a framework that can build production level codebase easier
- You should know what you want to build more or less
- I designed this to be somewhat token efficient
- SpecFlow is basically a 1. python based ALM software, and 2. a set of agent skills that helps you do V-model like development methodology.
  - the ALM part is where the agent can use a CLI tool to edit/ write the artifact tickets
  - the agent will try to generate the best practices and use certain `thinking techniques` to guide you along the way 

---

**Compliance-grade spec tracking, without the portal.**
Your git repo is the ALM. Your AI assistant is the UI.

Traditional ALM asks you to leave your editor, log into a website, and click through forms. SpecFlow doesn't. Every requirement, architecture doc, test, and audit record lives in Markdown in your repo — diffable, reviewable, CI-validated, yours.

## Why this exists

Old-school ALM tools were built for a world where humans typed every line. They made sense when writing code was slow and ceremony was cheap. AI coding assistants flipped that: the code comes out fast, and the ritual is the bottleneck.

SpecFlow keeps the rigor (V-model traceability, impact analysis, audit baselines, standards packs) and drops the parts that slow teams down (servers, licenses, portals, click-through workflows). First-class support for Claude Code and OpenCode; other assistants with file access to the project directory can use the skills, but those two are the primary targets.

## What SpecFlow expects you to bring

SpecFlow does not do ideation. It does not have a PM persona that interrogates your product idea, a CEO agent that validates your business model, or a brainstorming mode that figures out what you should build. That work should happen *before* SpecFlow — on a whiteboard, in a conversation with your team, with your favorite AI chatbot, wherever.

SpecFlow starts when you know what you want to build. `/specflow-discover` captures and structures what's already in your head through a guided conversation (specify + clarify). `/specflow-plan` breaks it into architecture and implementable stories. `/specflow-execute` builds it.

**Already have a codebase?** Install the optional **adoption pack** (`/specflow-init --preset adoption`) and run `/specflow-adopt` — it inventories your existing code/docs/tests, backfills artifacts describing what already exists, and cuts an as-built baseline so forward change is governed from there. Greenfield projects skip this and start at `/specflow-discover`.

If you need help deciding *what* to build, use a tool that does ideation well. When you're ready to specify, track, and build it with compliance-grade rigor — that's SpecFlow.

## Two ways to drive, one engine

SpecFlow is a single engine — the artifact graph plus a deterministic CLI, gates, and traceability — that you can drive two ways:

- **AI-first (the default).** You talk; an agent runs the `/specflow-*` skills, manages the artifact graph, and escalates to you at approval gates. This is the primary experience.
- **ALM / direct (the standalone foundation).** The CLI, phase-gates, V-model tests, baselines, and RBAC work **with no API key** — a human, a team, or CI can drive the whole lifecycle by hand. It's a complete ALM on its own; the AI layer is an optional driver on top, not a dependency.

Both lanes operate on the same substrate and the same gates, so you can mix them: an agent drafts, a human or CI reviewer approves. See the [Lifecycle overview](docs/lifecycle.md) for the two-lane flowchart.

## Feel it in 30 seconds

```bash
# 1. Install the CLI (one time, system level)
$ uv tool install git+https://github.com/Longhuiberkeley/specflow

# 2. Bootstrap your project (creates dirs + installs skills into your repo)
$ cd your-project
$ specflow init
   Detects platform, scaffolds _specflow/ and .specflow/, installs skills.
```

Then, inside your AI assistant:

```
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

**Prerequisites:** [uv](https://docs.astral.sh/uv/) + Claude Code or OpenCode.

**Step 1 — Install the CLI** (one time):

```bash
uv tool install git+https://github.com/Longhuiberkeley/specflow
```

**Step 2 — Bootstrap your project** (per repo):

```bash
cd your-project
specflow init
```

This scaffolds the directory structure and copies skill files (e.g. `.claude/skills/`) into your repo so your AI assistant can recognize `/specflow-*` commands.

**Step 3 — Open your AI assistant** and use the skills:

```
> /specflow-discover "Add SSO to our customer portal"
> /specflow-plan
> /specflow-execute
```

Full walkthrough in the [getting-started guide](docs/getting-started.md).

## What you get

| Feature | How |
|---------|-----|
| **Zero-token CI validation** | Schema, links, status, fingerprints, coverage — deterministic Python, no LLM required |
| **V-model traceability** | REQ → ARCH → DDD → UT/IT/QT, fully linked and linted |
| **Bring-your-own-standard** | Drop a PDF, URL, or pasted text. SpecFlow extracts clauses into compliance schemas |
| **Immutable baselines** | Snapshot, diff, and generate audit evidence between releases |
| **First-class Claude Code + OpenCode** | Skills install automatically; other assistants with project file access may work but are community-supported |
| **Autoresearch loops** | Define a competition + verify command, let your assistant iterate; every experiment becomes a tracked artifact |
| **Docs knowledge surface** *(new)* | `docs/` + root markdown is a recognized surface — `@ID`-cited, shown in `specflow brief`, staleness-warned, never an artifact type |
| **1 runtime dependency** | Just `pyyaml`. Everything else is stdlib. |

## Slash commands

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
| `/specflow-doc` | Author/cite docs (`@ID`), sync the docs index, check staleness |

All core skills accept freeform context. `/specflow-audit I'm worried about REQ coverage` scopes the audit to your concern.

## Autoresearch — autonomous research loops (new in v1.6.0)

If your project lives on a measurable metric (Sharpe ratio, F1 score, BLEU, P99 latency — anything a shell command can print as one number), the **autoresearch pack** turns SpecFlow into an autonomous experimentation lab.

Define a **competition** (dataset + verify command + metric), set a **budget**, and let your assistant iterate: modify → commit → verify → keep/discard → log → repeat. Every iteration becomes an `EXPT` artifact; every loop produces condensed `FIND` artifacts that survive context rot and inform the next run.

```bash
# Install the pack into a project
specflow init --preset autoresearch

# Then either drive from the assistant…
> /specflow-autoresearch:plan
> /specflow-autoresearch         # runs the loop
> /specflow-autoresearch:leaderboard

# …or drive from the CLI (harness-agnostic)
specflow autoresearch plan --competition COMP-001 --profile
specflow autoresearch run --competition COMP-001
specflow autoresearch leaderboard --all
```

What you get out of the box:

- **Multi-criteria competitions** — primary metric for ranking, binary guards for hard floors (max drawdown, test pass, etc.), freeform `auxiliary_metrics` on each EXPT for post-hoc analysis
- **Harness-agnostic CLI** — any LLM harness can drive the loop; no per-platform skill variants
- **Knowledge condensation** — `FIND` artifacts capture what worked / what failed across loops so the next iteration starts smarter, not from scratch
- **Documented anti-leakage and anti-gaming patterns** — read-only eval data, one-number verify output, robustness-adjusted primaries (walk-forward, bootstrap CI, K-fold)

Adapted from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) via [autoresearch_fork](https://github.com/Longhuiberkeley/autoresearch_fork) and [Claude Autoresearch](https://github.com/uditgoenka/autoresearch), then folded into SpecFlow's artifact/V-model model.

## Ops — live deployments & observations (new in v1.10.0)

Most of SpecFlow records what you *build*. The optional **ops pack** records what you *run*: a "deployed-and-observed" memory class with two domain-neutral artifact types.

- **RUN** — a deployment frozen at deploy-time: *what* is live (`deployed_ref`), *where* (`environment`), *when*, and *which REQ/ARCH/EXPT it satisfies*. Immutable, like a baseline for a live system — a change is a new RUN, never an edit.
- **MONITOR** — an append-only, timestamped observation of a RUN (`metrics`, `signals`, `health`, `captures`). Over time the MONITOR chain *is* the drift/performance/freshness ledger; a breached MONITOR `informs` the next action (a retrain LOOP, a rollback DEC).

```bash
specflow init --preset ops
> /specflow-ops          # deploy (RUN) + observe (MONITOR) workflows
specflow trace RUN-001   # REQ/ARCH/EXPT lineage + every MONITOR under this run
specflow brief --next    # flags a breached or unobserved live RUN when ops is active
```

**It complements your MLOps/GitOps stack — it doesn't replace it.** SpecFlow is the *governance ledger and chain of custody*, not a metrics store or a reconciliation controller. `RUN.deployed_ref` points **at** your MLflow model version, W&B artifact, or ArgoCD synced revision; `MONITOR` records the decision-grade observations (the breach, the snapshot, the freshness) and threads them back to the requirement they serve and forward to the action they trigger. The raw telemetry firehose stays in your dashboard; the *why this is live, and what we did about it* lives in SpecFlow — the layer MLflow/W&B/ArgoCD don't give you.

The framework also **adapts artifact guidance to your domain**: `specflow domain suggest` proposes a domain from your dependency manifests (quant/ml seeded), and `discover`/`plan` surface a per-domain **concept→artifact map** so "is this a REQ, a STORY, an autoresearch goal, or a RUN?" is answered at decision time — with the *why* — instead of requiring you to know the boundaries.

## Docs — the knowledge surface (new in v1.11.0)

`docs/` and root markdown (README, AGENTS, CHANGELOG, …) is a **recognized knowledge surface** — indexed, citable, and flagged when stale — but **never a lifecycle artifact type**. There's no `DOC` prefix, no status field, no change record when you edit a doc; git history is the change log.

- **Recognized, not counted as code.** Docs are pulled *out* of the orphan-code scan, so coverage metrics reflect real code rather than prose. `specflow brief` shows a Docs surface block.
- **Citable both ways.** A doc cites a spec with an inline `@ID` marker (`@ARCH-007`, `@DEC-018`); `specflow rebuild-index` builds the reverse index (artifact → citing docs).
- **Staleness is accounting, not policing.** `specflow detect stale-docs` and `/specflow-audit` warn when a doc cites a superseded/cancelled/deprecated artifact. Warnings never block a commit or fail an audit.

Use `/specflow-doc` to author, cite, sync the docs index, and check staleness.

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
| **AI** | Bolted on, if at all | Claude Code + OpenCode first-class, skill-first design |
| **Setup** | Servers, licenses, admins | `uv tool install` + `specflow init` — two commands |
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

After `specflow init`, two directories appear:

| Directory | Purpose | Edit? |
|-----------|---------|-------|
| `_specflow/` | Your specs and work items | Yes — your workspace |
| `.specflow/` | Framework internals (config, schemas, baselines) | No — managed by CLI |

Everything is Markdown with YAML frontmatter. Your repo is the database.

## Install

### Step 1: Install the CLI

```bash
# Latest
uv tool install git+https://github.com/Longhuiberkeley/specflow

# Pin to a release
uv tool install git+https://github.com/Longhuiberkeley/specflow@v1.11.1

# Run without installing (ephemeral)
uvx --from git+https://github.com/Longhuiberkeley/specflow specflow init
```

This makes the `specflow` command available system-wide.

### Step 2: Bootstrap each project

```bash
cd your-project
specflow init
```

This creates `_specflow/` and `.specflow/` in your repo, and copies skill files into the appropriate directory for your AI assistant (`.claude/skills/` for Claude Code, `.opencode/skills/` for OpenCode). After this step, `/specflow-*` slash commands are available in your assistant.

## Docs

- [Getting started](docs/getting-started.md) — tutorial walkthrough
- [Lifecycle overview](docs/lifecycle.md) — flowchart and command tiers
- [Where SpecFlow fits](docs/comparison.md) — what it is, what it isn't, and how it compares to other tools
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
