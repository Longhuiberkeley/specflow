## SpecFlow

**Stop.** This is a SpecFlow project. Describe what you want in plain language and the matching `/specflow-*` skill engages automatically — the slash is optional shorthand. The raw `specflow` CLI is for CI and power users, not the primary interface.

You are working in a **SpecFlow** project (spec-driven development).
Specs and work items are Markdown + YAML files. **Never edit `.specflow/` manually** — it holds config (`config.yaml`), state (`state.yaml`), schemas, and indexes that the CLI owns. The artifact YAML in `_specflow/` is also CLI-managed: use `specflow update <ID>` for frontmatter/status/link changes. If you truly must hand-edit an artifact file, run `specflow artifact-lint` afterward so indexes and fingerprints stay consistent.

### Interfaces
**Primary:** Use `/specflow-*` skills (e.g., `/specflow-discover`, `/specflow-plan`, `/specflow-execute`).
**Intent-first (no slash required):** The user may describe intent in plain language ("add SSO," "review REQ-003," "are the docs stale?"); match it to the right skill and run it — the slash form is optional. When intent is vague, `/specflow-start` (the router) fires and points at the right skill.
**CLI:** Use `specflow <cmd>` (e.g. `specflow trace <ID>`, `specflow update <ID>`) for automation and CI — not as a substitute for the skill workflow.

### CLI cheat-sheet
- **Canonical types:** requirement, architecture, detailed-design, unit-test, integration-test, qualification-test, review, story, spike, decision, defect, best-practice, audit, challenge (+ pack types like experiment/finding/competition/loop/run/monitor when installed). Abbreviations like `dec`, `req`, `qt`, `ut`, `ddd`, `def` are accepted everywhere a type is taken.
- **Inspect a type:** `specflow schema <type>` — shows settable fields (`--set` keys) and the full status-transition map.
- **Query artifacts:** `specflow list [--type T] [--status S] [--tags x,y] [--json]`.
- **Legal next statuses:** `specflow transitions <ID>` — status transitions are type-specific; run this before any `--status` change you're unsure about.

### Core Lifecycle
`init → discover → plan → execute → artifact-review → ship` (Audit & impact-review as needed).

### The V-Model & Work
Specs: `REQ` (Requirements) → `ARCH` (Architecture) → `DDD` (Detailed Design).
Tests: `QT` (verify REQ), `IT` (verify ARCH), `UT` (verify DDD).
Work: `STORY`, `SPIKE`, `DEC`, `DEF` (in `_specflow/work/`) must link to specs.

### Memory & Context

SpecFlow IS your persistent memory. You do not have reliable conversation memory across sessions — you have artifacts.

**Four-axis memory:**
- `spec/` = **semantic memory** (persistent truth, blueprints). REQ/ARCH/DDD survive every session.
- `work/` = **episodic memory** (what happened, when, why). STORY/SPIKE/DEC record the journey.
- `impact-log/` = **temporal memory** (causality — what changed, why, what it affected). Suspect propagation tracks downstream impact.
- `links` = **relational memory** (how artifacts connect). `specflow trace <ID>` walks the graph.

**Knowledge surfaces (learnings) — `specflow brief` shows their counts + dormancy:**
- **BP** (`_specflow/specs/best-practices/`) = **proactive / domain** guidance. Seeded at `/specflow-discover`; contribute one whenever you apply a reusable practice (`specflow create --type best-practice --status approved --tags …`). Consumed by plan/execute/review/audit and auto-loaded into `checklist-run` for artifacts whose tags or `applies_to` match.
- **PREV** (`.specflow/checklists/learned/`) = **reactive / incident** patterns. Auto-captured from review findings (blocking/warning from learnable techniques) and from `specflow done`; recalled via `specflow patterns` and auto-loaded into `checklist-run` for matching tags.
- **FIND** (autoresearch) = accumulated research knowledge. **CHL** (challenges) = review findings awaiting resolution.
- A wired-but-empty surface is the silent failure mode of this system. If `brief` shows `0 PREV` or no active BPs, the loop isn't firing — capture one rather than let it stay dormant.

**Docs — the knowledge surface (not an artifact):**
- `docs/` + root markdown (README, AGENTS, CHANGELOG, …) is recognized prose, indexed and shown in `specflow brief`. It is NOT an artifact type — no status, no lifecycle, no `_index.yaml` entry.
- Cite specs from a doc with inline `@ID` markers (e.g. `@ARCH-007`, `@DEC-018`). `specflow detect stale-docs` and `/specflow-audit` warn (never block) if a doc cites a superseded/cancelled/deprecated artifact.
- Editing a doc is git-history-only — it never creates a REQ/ARCH/DEC. Use `/specflow-doc`.

**Recall before you act:**
- Run `specflow brief` for a one-call deterministic digest (phase, inventory by status, suspects, next wave, recent changes); use `brief --next` when you only need the next step. This is the default first move on any vague or fresh prompt — cheaper and more complete than scanning files by hand.
- For a wider dashboard view, run `specflow status` (phase, counts, stale items).
- Drill down only when brief points at something specific: scan `_index.yaml` files in relevant directories (title + status + tags for every artifact without reading full bodies), and read `.specflow/state.yaml` for the current phase / `.specflow/config.yaml` for domain context.
- Use `specflow trace <ID>` to walk the link chain and understand context.
- Use `specflow rtm --gaps` for the project-wide requirements-traceability matrix (REQ → ARCH → STORY → verifying tests, gaps flagged per row).
- Use `git log --since=<date> -- _specflow/` for temporal recall — "what changed recently."
- Check `.specflow/impact-log/` for causality — what changed and why.
- For research: read FIND artifacts first — they are accumulated knowledge that survives context rot.
- Run `specflow artifact-lint` to detect context debt (orphans, broken links, missing coverage).

**Journal as you work:**
- Non-trivial decisions → DEC artifact (not just enacted and forgotten).
- Discoveries, dead-ends, rationale → the work artifact you're executing.
- Use the Permanence Test (below): ephemeral → work/, reusable → spec/.
- If you find yourself working on something unlinked → convert to SPIKE or promote to a linked STORY.

**Context management for fresh sessions:**
- A fresh agent reads `_index.yaml` files to reconstruct project state cheaply.
- Prefer breadth-first (scan indexes) then depth (read specific artifacts), not the reverse.
- Run `specflow artifact-lint` to assess memory health before starting work.

### Workflow Rules
- **Traceability:** Every code change must trace to a STORY or REQ. No orphan work.
- **STORY linkage:** Every STORY must link to at least one spec artifact (REQ, ARCH, or DDD). Unlinked work is research — use SPIKE for that.
- **No self-approval:** Agents may NEVER move an artifact from `draft` to `approved` without human confirmation. Plan phase is conversational — the human iterates as long as needed. The agent presents, the human approves.
- **Status Flow:** Status transitions are TYPE-SPECIFIC — run `specflow transitions <ID>` for legal next states (e.g. a DEF goes `open → investigating → closed`, a REQ goes `draft → approved → implemented → verified`). Do not assume a single linear flow across types.
- **Updates:** Use `specflow update <ID> --status <status>` for all YAML/status changes. Use `specflow update <ID> --add-link TARGET:ROLE` / `--remove-link TARGET` to manage links; `--links '...'` replaces the whole list.
- **Cascading:** When STORY code lands: `specflow update STORY-NNN --status implemented` then `specflow cascade-status STORY-NNN`.
- **Evidence:** Don't assume "verified" — prove it. Capture the gate baseline *before* you change (test pass/fail counts, or `artifact-lint` counts if there's no test runner yet), then re-run the *same* gate after and report the delta. Never claim "no regressions" without a captured baseline to diff against.
- **Validation:** Run `specflow artifact-lint` after manual artifact edits.
- **Suspect resolution:** When an artifact is flagged `suspect`, actively propose resolution to the human (create DEF, mark resolved, or update the artifact). Do not let suspect flags sit unresolved.

### Routing
- Use core `/specflow-*` skills for ALL engineering work: requirements, architecture, stories, implementation, review, release.
- **Orient first on a vague or fresh prompt:** run `specflow brief --next` (or `/specflow-start`) to get the deterministic next-step recommendation, then route to the matching skill. Do not guess the phase from memory — read it.
- `/specflow-doc` for writing/citing/syncing docs and checking doc staleness. Docs are a knowledge surface, not artifacts — a decision is still a DEC, a requirement is still a REQ; `/specflow-doc` is only for the prose that explains and cites them.
- **Research / experiment routing:** bare "research whether X" / "prototype Y" / a quick throwaway spike → create a **SPIKE** (`specflow create --type spike`) — it is a work artifact, not a routable skill. Reproducible / overnight / competition-scoped experimentation → the **autoresearch** pack (`/specflow-autoresearch`, needs a COMP with a verify command). A multi-source fact-checked report → the host's `deep-research` skill. Do not route any of these to `/specflow-discover` (it authors requirements, not research).
- Packs (e.g., autoresearch) are **separate subsystems**. Only use pack skills when the user explicitly asks for that pack's domain. Never invoke pack skills for codebase exploration, bug investigation, feature implementation, or general engineering — those are core engineering.
- **By default**, new features go through the full pipeline. Typo fixes and trivial changes may use the lean path — but still trace to a STORY.
- **Reverse lifecycle (rewinds):** When the user says "go back to requirements," "rethink the architecture," "this approach isn't working," or similar, run `specflow phase-set <phase> --reason "<why>"` before or alongside routing to the matching skill (`discovering`/`specifying` for discover, `planning` for plan, `executing` for execute) — this keeps recorded phase state honest so `brief --next` doesn't route off a stale forward-only assumption.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a blocking check, articulate: "Proceeding past [specific item]. Risk: [what could go wrong]. Noted."

### When to Escalate (Permanence Test)
SPIKE/STORY are throwaway; REQ/ARCH/DDD (and, for research, COMP) are durable. When work outgrows a one-off answer — you're building something reusable, iterating a second time, defining an interface, or needing it to survive this session — promote to a durable artifact when ANY of these holds:
- **Reuse** — the output will be depended on by future work (a dataset object, a pipeline, an API client), not a one-off answer.
- **Second pass** — you're iterating on the same thing again; it has stopped being exploratory.
- **Interface** — it defines a contract other code/research will call (→ ARCH/DDD).
- **Survival** — it must outlive this session / be understood by a fresh agent.

To promote, create the REQ/ARCH/DDD (or hand-author a new COMP) and link `derives_from` the originating SPIKE/COMP so context and traceability carry forward — don't silently keep spiking. See `specflow-execute/references/escalation-and-promotion.md` for the recipe.
