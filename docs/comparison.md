# SpecFlow — Where It Fits

A plain-language guide to what SpecFlow is, what it isn't, and how it relates to other tools in the AI-assisted development space.

---

## What SpecFlow Is

- **A filesystem-native ALM.** Requirements, architecture, tests, defects, and audit records live as Markdown+YAML in your git repo. No server, no database, no portal.
- **A deterministic validation engine.** Schema checks, V-model traceability, coverage metrics, suspect flags, and baselines run as pure Python — zero LLM tokens spent on CI.
- **A context-engineering system for AI agents.** Since v1.8.0, SpecFlow acts as structured, version-controlled memory that any AI assistant can read to reconstruct full project state. `specflow brief` gives a fresh agent everything it needs in one call.
- **Host-agnostic.** SpecFlow ships no LLM client. First-class on Claude Code and OpenCode; other assistants with project file access can use the skills. The intelligence comes from your host; the structure comes from SpecFlow.
- **A compliance-grade spec tracker.** V-model traceability (REQ → ARCH → DDD → UT/IT/QT), immutable baselines, standards packs, ReqIF interchange — the rigor of DOORS/Polarion without the portal tax.

## What SpecFlow Isn't

- **Not a code generator.** SpecFlow doesn't write code. It structures the *thinking* around code — requirements, architecture, design decisions, test plans — so that when your AI assistant writes code, it writes the *right* code.
- **Not a chatbot wrapper.** No prompt chaining, no "ask the AI and hope." Skills are structured workflows with gates, not open-ended conversations.
- **Not a proprietary platform.** No accounts, no SaaS, no vendor lock-in. Your repo is the database. Git is the transport. Markdown is the format.
- **Not SpecFlow for .NET.** [specflow.org](https://specflow.org) is a BDD framework by Tricentis. Unrelated.
- **Not SpecStoryAI.** [github.com/specstoryai/specflow](https://github.com/specstoryai/specflow) is a different project. Unrelated.

## What SpecFlow expects you to bring

Several AI coding frameworks include an upfront ideation or validation phase — a PM persona that interrogates your product idea, a CEO agent that stress-tests your business model, or a mandatory brainstorming session that figures out what you should build. SpecFlow does not have this, and that's deliberate.

SpecFlow starts when you know what you want to build. Here's how the workflow maps:

| Phase | What it does | Closest equivalent in other tools |
|-------|-------------|-----------------------------------|
| `/specflow-discover` | Structured elicitation — captures and clarifies requirements you already have. One question at a time, silent readiness assessment, 15-20 question cap. | spec-kit's Specify + Clarify steps |
| `/specflow-plan` | Architecture proposal → detailed design → SPIDR story decomposition with full V-model links. | spec-kit's Plan + Tasks, but with traceability |
| `/specflow-execute` | Implement stories, generate V-model verification tests (UT/IT/QT), phase closure. | Most tools' "implement" step, but with test generation tied to the spec chain |

If you need help deciding *what* to build — product validation, market fit, MVP scoping — do that first. Use a whiteboard, a conversation with your team, or one of the tools that does ideation well (BMAD's PM persona, gstack's `/office-hours`, superpowers' brainstorming phase). When you're ready to specify, track, and build with compliance-grade rigor, SpecFlow picks up from there.

SpecFlow trusts that you've done the thinking. Our job is to make sure the thinking survives into the codebase — structured, traceable, and validated.

> **Existing codebase?** SpecFlow's default flow is greenfield, but the optional **adoption pack** (`/specflow-init --preset adoption` → `/specflow-adopt`) inventories an existing codebase, backfills specs for what already exists, and cuts an as-built baseline — so you can adopt SpecFlow mid-project rather than start over.

---

## SpecFlow vs. AI Coding Frameworks

A new wave of tools adds structure to AI-assisted development. They share a premise — *unstructured AI coding produces mediocre results* — but solve it differently.

| | **BMAD-METHOD** | **gstack** | **superpowers** | **spec-kit** | **SpecFlow** |
|---|---|---|---|---|---|
| **Core idea** | Specialized agent personas (PM, Architect, Dev…) guide you through agile workflows | Map AI to startup team roles (CEO, Designer, QA…) with sprint methodology | Enforce TDD and structured planning — "mandatory workflows, not suggestions" | Spec-driven development: specs are executable artifacts that generate implementations | V-model spec tracking with deterministic validation; your repo is the ALM |
| **Methodology** | Agile (34+ workflows, scale-adaptive planning) | Sprint: Think → Plan → Build → Review → Test → Ship | Brainstorm → Plan → Implement (TDD) → Review | Constitution → Specify → Clarify → Plan → Tasks → Implement | V-model: Discover → Plan → Execute → Review → Ship, with phase gates |
| **Artifacts** | Agent-generated docs (design docs, PRDs) | Design docs, sprint plans, review reports | Planning docs, test plans | Spec files, task lists, implementation plans | Linked artifact graph: REQ → ARCH → DDD → UT/IT/QT + STORY/DEC/DEF |
| **Validation** | Agent judgment | Agent judgment + browser testing | TDD enforcement | Quality analysis tools | Deterministic Python: schema, links, status, fingerprints, coverage — zero tokens |
| **CI integration** | None built-in | None built-in | None built-in | GitHub Actions (generated) | Native: `artifact-lint` runs in any CI, no API key needed |
| **Compliance** | Not addressed | Not addressed | Not addressed | Presets for standards | Full: standards packs, baselines, ReqIF, RBAC, audit evidence |
| **Install** | `npx bmad-method install` | Clone + setup script | Clone + skills | `uv` + `specify init` | `uv tool install` + `specflow init` |
| **Standalone (no AI)** | No | No | No | No | Yes — the CLI is a complete ALM with no API key |

### The key difference

Most AI coding frameworks are **agent orchestration layers** — they give AI assistants better prompts, personas, and workflows. SpecFlow is a **data model** — a structured artifact graph with deterministic validation that any agent (or human, or CI) can read and write.

Agent frameworks ask: *"How should the AI behave?"*
SpecFlow asks: *"What should persist after the conversation ends?"*

They're complementary. You could use BMAD's PM persona to *discover* requirements, then track them in SpecFlow's artifact graph with full V-model traceability and CI validation. The frameworks structure the conversation; SpecFlow structures the output.

---

## SpecFlow vs. AI Memory Systems

Since v1.8.0, SpecFlow functions as a structured memory system for AI-assisted development. But it works very differently from the vector/graph memory frameworks designed for conversational AI.

| | **Mem0 / Zep** | **LangChain / LlamaIndex Memory** | **Letta** | **Cognee** | **SpecFlow** |
|---|---|---|---|---|---|
| **What it remembers** | Facts, entities, preferences extracted from chat | Conversation history, summaries, entity mentions | Full conversation with tiered context management | Knowledge graphs built from unstructured data | Project structure: requirements, architecture, decisions, defects, test plans |
| **Storage format** | Vector DB + metadata | Vector DB / in-memory / DB | OS-like tiered storage (RAM ↔ disk) | Knowledge graph (nodes + edges) | Markdown + YAML files in git |
| **Retrieval** | Semantic search, metadata filtering | Buffer, summary, entity, or graph retrieval | Context window management with archival | Graph traversal + vector search | `specflow brief` — deterministic digest, no search needed |
| **Reasoning** | The LLM reasons over retrieved facts | The LLM reasons over retrieved context | The LLM reasons over managed context layers | Graph enables relational reasoning | The artifact graph *is* the reasoning structure — links, coverage, suspect flags |
| **Session continuity** | Cross-session user memory | Per-chain or per-agent memory | Persistent across sessions | Persistent knowledge graph | Persistent across sessions, teams, and AI hosts — it's files in git |
| **Determinism** | Probabilistic (embedding similarity) | Probabilistic | Probabilistic | Probabilistic + graph rules | Fully deterministic — same input, same output, every time |
| **Target use case** | Chatbots, personal assistants | RAG pipelines, document QA | Long-running conversational agents | Research agents, knowledge management | Software projects with compliance-grade tracking |

### The key difference

Conversational memory systems are **probabilistic** — they store embeddings, search by similarity, and hope the right context surfaces. SpecFlow's memory is **deterministic** — artifacts are structured files with explicit links, and `specflow brief` assembles a complete project digest from the artifact graph.

Conversational memory remembers *what was said*.
SpecFlow memory remembers *what was decided and why*.

### The four-axis memory model (v1.8.0)

SpecFlow's recall operates on four axes:

| Axis | What it covers | Example |
|------|---------------|---------|
| **Semantic** | The artifact graph — requirements, architecture, design, tests | "What does REQ-003 require?" |
| **Episodic** | Decisions, defects, and their resolution history | "Why did we choose PostgreSQL over SQLite?" |
| **Temporal** | Change records, baselines, and diff evidence | "What changed between v1.0 and v1.1?" |
| **Relational** | V-model links, suspect flags, coverage chains | "Which tests verify REQ-003? Is anything suspect?" |

A fresh agent running `specflow brief` gets all four axes in one call — no vector search, no embedding, no API key. The agent reconstructs project state from structured files, not probabilistic retrieval.

---

## Where SpecFlow Fits

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    AI-Assisted Development                       │
    │                                                                  │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
    │  │  Agent        │  │  Memory       │  │  SpecFlow            │  │
    │  │  Frameworks   │  │  Systems      │  │                      │  │
    │  │              │  │              │  │  Structured artifact   │  │
    │  │  BMAD        │  │  Mem0, Zep   │  │  graph + deterministic│  │
    │  │  gstack      │  │  Letta       │  │  validation + context │  │
    │  │  superpowers │  │  Cognee      │  │  engineering           │  │
    │  │  spec-kit    │  │  LangChain   │  │                      │  │
    │  │              │  │              │  │  "What persists after  │  │
    │  │  "How should │  │  "What does  │  │   the conversation    │  │
    │  │   the AI     │  │   the AI     │  │   ends?"              │  │
    │  │   behave?"   │  │   remember?" │  │                      │  │
    │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
    │         │                 │                      │              │
    │         └─────────────────┼──────────────────────┘              │
    │                           │                                      │
    │                    ┌──────▼───────┐                              │
    │                    │  Your code   │                              │
    │                    │  Your repo   │                              │
    │                    └──────────────┘                              │
    └─────────────────────────────────────────────────────────────────┘
```

SpecFlow doesn't replace agent frameworks or memory systems. It occupies a distinct layer:

- **Agent frameworks** structure the *conversation*. SpecFlow structures the *output*.
- **Memory systems** remember *interactions*. SpecFlow remembers *artifacts and decisions*.
- **Agent frameworks** need an LLM to function. SpecFlow's CLI works with zero API keys.
- **Memory systems** are probabilistic. SpecFlow is deterministic.

If you're building a chatbot, use Mem0. If you're building a RAG pipeline, use LlamaIndex. If you want your AI assistant to build production software with compliance-grade tracking, version-controlled memory, and CI-validated specs — that's SpecFlow.

---

## Further Reading

- [Lifecycle overview](lifecycle.md) — the two-lane flowchart
- [Architecture](architecture.md) — the two-axis artifact model
- [Design decisions](decisions.md) — resolved trade-offs
- [README](../README.md) — quick start and feature overview
