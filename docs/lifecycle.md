# SpecFlow Lifecycle

SpecFlow is **one engine driven two ways**:

- **AI-first (the default experience).** You talk; an agent runs the `/specflow-*` skills, manages the artifact graph, and escalates to you at approval gates. The intelligence comes from your host harness (Claude Code, Codex, OpenCode, …) — **SpecFlow itself makes zero external API calls** and ships no LLM client of its own.
- **ALM / direct (the standalone foundation).** The artifact graph, deterministic CLI, phase-gates, traceability, V-model tests, baselines, and RBAC work **with no API key** — a human, a team, or CI can drive the whole lifecycle by hand. This is a complete ALM in its own right; the AI layer is an optional driver on top of it, not a dependency.

Both lanes operate on the **same substrate and the same gates**, so you can mix them: an agent drafts in the AI-first lane, a reviewer approves in the ALM lane via CLI or CI. The skills never do anything you couldn't do by hand — they just compose the same `specflow …` commands.

> **Approval, in each lane.** "No self-approval" restrains the *agent*: it may never move an artifact from `draft` to `approved` on its own. In the ALM lane the human *is* the operator and approves directly by running `specflow update <ID> --status approved` (or via a reviewer / CI gate). Approval is always a human act — the lanes only differ in who surfaces the decision.

## Lifecycle Flowchart

Two lanes, one engine. AI-first is the default; ALM/direct stands alone.

```mermaid
flowchart TB
    classDef engine fill:#eef2ff,stroke:#7c83db,color:#111;
    classDef gate fill:#fff0f0,stroke:#cc7a7a,color:#111;
    classDef pack fill:#f0fff4,stroke:#5aa56a,color:#111;

    subgraph AI["AI-first lane — default driver (conversational · agent-driven · zero external API calls)"]
        direction TB
        BR["specflow brief<br/>recall / orient (resume any session)"] --> AID["/specflow-discover/"]
        AID --> AG1{{"human approval gate<br/>agent presents · no self-approval · risk tiers"}}
        AG1 --> AIP["/specflow-plan/"]
        AIP --> AG2{{"human approval gate"}}
        AG2 --> AIE["/specflow-execute/<br/>waves; gate blocks draft specs"]
        AIE -. "suspect?" .-> DFS["specflow defect-from-suspect"]
    end

    subgraph ALM["ALM / direct lane — standalone (CLI · CI · no agent)"]
        direction TB
        ALS["specflow status / trace<br/>read state"] --> ALC["specflow create / update"]
        ALC --> ALG["human runs update --status approved<br/>(reviewer / CI / operator)"]
        ALG --> ALL["specflow artifact-lint --gate"]
    end

    subgraph ENG["One engine — the artifact graph + deterministic gates"]
        direction LR
        REQ --> ARCH --> DDD --> STORY
        STORY -. "verified by" .-> TST["UT / IT / QT"]
        STORY --> WRK["DEC · DEF · AUD"]
    end

    ADOPT["/specflow-adopt (adoption pack)<br/>existing codebase → backfill → as-built baseline"]
    ADOPT -.-> ENG
    AI ==> ENG
    ALM ==> ENG
    ENG ==> REV["/specflow-artifact-review/"]
    REV ==> NEXT["/specflow-change-impact-review/<br/>· /specflow-audit · /specflow-adapter/"]
    NEXT ==> SHIP["/specflow-ship/<br/>baseline + DECs + quick audit"]

    %% Optional pack-activated extensions — not mandatory lanes; the engine works without them.
    RES["autoresearch pack (optional) · offline experiments<br/>COMP → LOOP → EXPT → FIND (frozen, reproducible)"]
    OPS["ops pack (optional) · live operations<br/>RUN (deploy-time freeze) → MONITOR (observation journal)<br/>references your MLflow / W&amp;B / ArgoCD via deployed_ref"]
    ENG -. "measurable metric" .-> RES
    ENG -. "deployed live" .-> OPS
    RES -. "promote (derives_from)" .-> OPS
    OPS -. "breach informs → retrain LOOP / rollback DEC" .-> ENG

    class ENG engine
    class AG1,AG2 gate
    class RES,OPS pack
```

<details>
<summary>Plain-text (ASCII) version of the same flowchart</summary>

```
                 ┌────────────────────────────────────────────────┐
                 │   ONE ENGINE — the artifact graph + gates        │
                 │   REQ → ARCH → DDD → STORY                       │
                 │   STORY verified by UT / IT / QT                 │
                 │   + DEC · DEF · AUD                              │
                 │   deterministic CLI · phase-gates · trace · lint │
                 └──────────▲───────────────────────────▲──────────┘
                            │                            │
   AI-FIRST (default driver)│                            │ ALM / DIRECT (standalone)
   conversational·agent-led │      same commands,        │ CLI · CI · no agent
   ─────────────────────────│      same gates            │ ────────────────────────
   specflow brief  (recall) ─┘                           └─ specflow status / trace
            │                                                       │  (read state)
            ▼                                                       ▼
   /specflow-discover                                       specflow create / update
            │                                                       │
   ╔════════▼════════╗  human approves                              ▼
   ║ APPROVAL GATE   ║  (agent presents,                   human runs update
   ║ REQ → approved  ║   no self-approval, tiers)          --status approved
   ╚════════┬════════╝                                     (reviewer / CI / operator)
            ▼                                                       │
   /specflow-plan                                                   ▼
            │                                              specflow artifact-lint --gate
   ╔════════▼════════╗                                             │
   ║ APPROVAL GATE   ║                                             │
   ║ STORY → approved║                                             │
   ╚════════┬════════╝                                             │
            ▼                                                       │
   /specflow-execute ──suspect?──▶ specflow defect-from-suspect    │
   (gate blocks draft specs) ◀─────── resolve / DEF                │
            │                                                       │
            └───────────────────────┬───────────────────────────────┘
                                    ▼
                         /specflow-artifact-review
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
   /specflow-change-        /specflow-audit         /specflow-adapter
    impact-review            (periodic full-          (configure CI, roles,
    (per-commit/PR;           project health;          adapters at any time)
     blast radius)            AUD + CHL)
                                    │
                                    ▼
                            /specflow-ship
                            (baseline + DECs + quick audit)

   ── Optional pack-activated extensions (the engine runs without them) ──────────
   autoresearch (offline):  COMP → LOOP → EXPT → FIND       (frozen, reproducible)
   ops (live ops):          RUN  → MONITOR                  (deploy freeze + journal)
         EXPT ──promote (derives_from)──▶ RUN               (offline result → live)
         MONITOR breach ──informs──▶ retrain LOOP / rollback DEC   (back to engine)
   RUN.deployed_ref points AT your MLflow / W&B / ArgoCD — SpecFlow is the
   governance ledger over them, not a replacement for the dashboard.
```
</details>

## Adoption — bringing an existing project in

Everything above assumes you **start** with SpecFlow. If you have an **existing** codebase, install the optional **adoption pack** and run `/specflow-adopt` instead of starting at `/specflow-discover`:

```
/specflow-init --preset adoption   # install the adoption pack
/specflow-adopt                     # inventory → backfill → as-built baseline
```

`/specflow-adopt` records the project's **current state** as artifacts (REQ/ARCH/DDD/DEC, tagged `backfilled`, with honest statuses like `implemented`/`verified` for code that already exists), cuts an **as-built baseline** (`adoption-v0`), and retro-links existing code. From that point, drift is measured against the adoption snapshot — not from zero — and **forward work resumes through the normal lifecycle** (`/specflow-discover` → plan → execute). New features are *not* `backfilled`; they're governed-forward.

Adoption is **incremental and resumable**: one subsystem boundary per pass, `specflow detect orphan-code` as the progress meter, interleaved with ongoing development. It reuses the core artifact model (no new types/statuses) and surfaces conflicting sources to you rather than guessing. See the adoption pack's README and the `/specflow-adopt` skill for detail.

> Greenfield projects (started with `/specflow-init`) do **not** need the adoption pack — go straight to `/specflow-discover`.

## Docs — the knowledge surface

`docs/` (and root markdown — README, AGENTS, CHANGELOG, …) is a **recognized knowledge surface**: indexed, citable, and flagged when stale — but **never** a lifecycle artifact type. No `DOC` prefix, no status, no `_index.yaml` lifecycle entry, no DEC when you edit. Git history is the doc change log.

- **Recognized, not counted as code.** Docs are pulled *out* of the orphan-code scan, so coverage metrics reflect real code rather than prose. `specflow brief` shows a Docs surface block (count, areas, how many cite an artifact).
- **Citable both ways.** A doc cites a spec with an inline `@ID` marker (`@ARCH-007`, `@DEC-018`); `specflow rebuild-index` builds a reverse index (artifact → citing docs). Citations use no new link role (frozen vocabulary D-18 respected).
- **Staleness is accounting, not policing.** `specflow detect stale-docs` and `/specflow-audit` warn when a doc cites a superseded/cancelled/deprecated artifact. Warnings never block a commit or fail an audit.
- **Absorbed on adoption.** `/specflow-adopt` registers the docs surface at `adoption-v0`, so a mid-project start doesn't leave existing docs as a blind spot of outdated info.

**Dual-mode framing.** AI-first: docs are recall context the agent reads to understand the project (cited back to the spec graph, so prose and specs stay consistent). ALM/standalone: docs are the human-readable mirror of the spec graph, kept honest by staleness warnings. Use `/specflow-doc` for authoring, citing, syncing, and staleness checks.

## Tier 1 — Slash Commands (the AI-first product)

These are what a user learns and uses day-to-day in the AI-first lane. Each is documented in [commands.md](commands.md) with a full interface spec.

| # | Slash Command | When to Use |
|---|---------------|-------------|
| 1 | `/specflow-init` | Starting a new project; installing skills, packs, CI |
| 2 | `/specflow-discover` | Capturing a new requirement through conversation |
| 3 | `/specflow-plan` | Breaking approved REQs into architecture + stories |
| 4 | `/specflow-execute` | Implementing approved stories with test generation |
| 5 | `/specflow-artifact-review` | Quality review of one or more specific artifacts |
| 6 | `/specflow-change-impact-review` | Blast-radius review of recent commits/PRs |
| 7 | `/specflow-audit` | Periodic full-project health check |
| 8 | `/specflow-ship` | Cutting a release: baseline + change records + quick audit |
| 9 | `/specflow-adapter` | Configuring CI workflows, roles/RBAC, and adapters (any time) |
| 10 | `/specflow-pack-author` | Authoring a standards compliance pack |

## Tier 2 — The CLI = a standalone ALM (no agent required)

Every slash command above composes underlying `uv run specflow …` commands. Those commands **are the product** for the ALM / direct lane — power users, teams, and CI pipelines invoke them directly with no API key:

- **Recall & navigation:** `specflow brief` (one-call digest), `specflow status`, `specflow trace <ID>`
- **Authoring:** `specflow create`, `specflow update --status <status>`
- **Gates & validation:** `specflow artifact-lint [--type … | --gate <name>]`
- **Defects:** `specflow defect-from-suspect <ID> --req <REQ>` (suspect → DEF with traceability)
- **Release & change:** `specflow baseline`, `specflow document-changes`, `specflow project-audit`

See the [CLI Reference](cli-reference.md) for the full catalog organized by workflow phase.
