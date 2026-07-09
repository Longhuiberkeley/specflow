# SpecFlow — Design Decisions

Each decision documents the context, options considered, the resolution, and rationale. New contributors should read this before proposing changes to avoid re-litigating settled decisions.

This is the human design log. Structured change records (the auto-generated "Change Record" form of a decision) also live as DEC artifacts under `_specflow/work/decisions/` — e.g. @DEC-018 — and are what `/specflow-ship` and `/specflow-change-impact-review` reason over. The two parallel each other; this file is prose, the DEC artifacts are the machine-readable graph.

---

### D-01: Change Management Approach

**Context:** How should SpecFlow handle change records — as forms filled out before work, or as records generated after?

**Options considered:**
- CR as input (fill form before work) — traditional compliance, high friction
- Always-auto CR (framework generates on every change) — zero friction, noisy
- Git-only (no CR artifacts) — simplest, weaker for compliance
- Hybrid (git tracks live, .md synthesized on demand)

**Decision:** Hybrid. Git is the live record. Impact-log entries are automatic. Suspect flags are automatic. The `.md` CR artifact is only materialized on demand via `specflow document-changes` — before a PR, before a baseline, or when a compliance audit asks for it.

**Rationale:** The `.md` CR is a projection of what git + impact-log already know, not a separate thing to maintain. This satisfies compliance requirements (traceability + impact analysis evidence) without developer friction. Compliance standards require evidence and traceability — they do not mandate manual form-filling before writing code.

---

### D-02: Domain Adaptivity

**Context:** HAZ, ASIL, and safety-goal artifacts are meaningless for fintech projects. The framework must not force irrelevant artifact types on projects that don't need them.

**Options considered:**
- Hardcode all artifact types (including safety) — works for automotive, awkward for everyone else
- Mode toggle (`mode: regulated` vs `mode: agile`) — contradicts modeless philosophy
- Schema-driven artifact types installed by industry packs

**Decision:** Schema-driven artifact types. The base framework ships with only the V-model core (REQ, ARCH, DDD, UT, IT, QT, STORY, SPIKE, DEC, DEF). Industry packs add types at install time: `--preset iso26262` adds HAZ, SG, SR; `--preset sox` adds CTRL, EVID. Directories are assembled from base + active packs. Empty directories are not created.

**Rationale:** Different industries need different artifacts. The mechanism (link graph traversal, gap analysis, validation) is identical across domains — only the content changes. This avoids forcing automotive concepts onto fintech projects and vice versa.

---

### D-03: Single Agent & Scale-Adaptive Workflow (No Tracks)

**Context:** Small changes (adding a button, fixing a typo in copy) don't need full discovery ceremony. Complex platforms require deep architecture. How to reduce friction for small changes while supporting massive ones?

**Options considered:**
- Explicit Tracks (e.g., Quick Track vs. Enterprise Track) — high cognitive load for user
- Multiple Personas (PM Agent vs. Architect Agent) — requires user to choose "who" to talk to
- Auto-detect scope via readiness assessment convergence speed

**Decision:** The readiness assessment IS the scope detector. There is only one entry point (`/specflow-discover`) and one generalized agent. If all required readiness dimensions are satisfied within the first exchange, the framework silently chooses the lean path (minimal artifacts, auto-approved). No explicit tracks, no toggles, and no distinct agent personas. Lean artifacts grow naturally through standard workflow.

**Rationale:** Explicit tracks or multiple agent personas contradict the modeless philosophy by forcing the user to make meta-decisions before working. Ceremony should be proportional to ambiguity automatically. If a lean artifact later needs depth, standard validation and readiness checks apply — it's just a spec that evolved.

---

### D-04: Schema Migration Strategy

**Context:** As the framework evolves, schemas gain new fields. Existing artifacts don't have them. How to handle upgrades?

**Options considered:**
- Versioned migrations (`specflow upgrade` rewrites frontmatter)
- Additive-only schemas (new fields always optional)
- Lazy migration (fields added when artifact is touched)

**Decision:** Additive-only + lazy. Schemas never remove fields. New fields default to absent (not null). When an artifact is opened for editing, the framework suggests filling in new fields but doesn't force it.

**Rationale:** Zero migration scripts, zero breaking changes. An artifact created in Phase 1 is still valid in Phase 7. This keeps the framework non-destructive and avoids the complexity of migration tooling.

---

### D-05: Impact-Log Storage Format

**Context:** Impact-log records every fingerprint change and suspect flag event. If stored as a single append-only file, distributed teams will hit git merge conflicts.

**Options considered:**
- Single `impact-log.yaml` (append-only) — simple, merge conflicts
- One file per event, timestamp-first naming
- One file per event, artifact-first naming

**Decision:** One file per event, artifact-first naming (`REQ-001_2026-03-20T14-30-00Z.yaml`). Stored in `.specflow/impact-log/`. Timestamp + artifact ID makes filenames unique.

**Rationale:** Artifact-first naming enables fast querying: "show me everything that happened to REQ-001" is just a glob of `REQ-001_*.yaml`. Near-zero merge conflict probability since different developers rarely modify the same artifact simultaneously. Same pattern applies to `checklist-log/`.

---

### D-06: Dedup Performance Strategy

**Context:** Duplicate detection requires comparing artifacts. At scale (1000+ artifacts), pairwise comparison is O(N^2).

**Decision:** On-demand computation, no pre-cached embeddings. Four-tier approach where each tier filters candidates for the next:

1. Tag overlap (zero cost, instant) — same tags = surface match
2. TF-IDF title similarity (zero cost, fast) — keyword overlap
3. Local embeddings (on-device compute) — semantic similarity, only for candidates surviving tiers 1-2
4. LLM (token cost) — only for ambiguous 0.6-0.9 cosine similarity range

**Rationale:** Tag/keyword search eliminates most false candidates before any computation. Local embeddings (all-MiniLM-L6-v2) compute in milliseconds per candidate. Full dedup scans are infrequent (before milestones) and fast enough locally. Pre-caching embeddings adds complexity for minimal gain — YAGNI.

---

### D-07: Multi-repo / System-of-systems

**Context:** ISO 26262 operates at vehicle level -> system -> subsystem -> component. Each might be a separate repo. The link graph would need to span repositories.

**Decision:** Punt to later phase (P7+). Design the link role vocabulary now (`system_parent`, `provides_to`, `receives_from`) but don't implement cross-repo traversal. A single-repo project can reference external artifacts by ID string — it just can't validate them.

**Rationale:** This is an enterprise-scale problem that shouldn't complicate the single-repo MVP. Full system-of-systems support would need a manifest format or git submodule integration, which is a separate design effort.

---

### D-08: Tool Qualification

**Context:** For ASIL-C/D, ISO 26262 Part 8 requires that tools used in development be qualified. SpecFlow itself would be such a tool.

**Decision:** Punt to P6/P7. SpecFlow will generate its own qualification evidence via dogfooding — since SpecFlow tracks its own development with itself, the test execution records, traceability matrices, and checklist logs serve as qualification evidence. A future `specflow self-qualify` command would generate a tool qualification report.

**Rationale:** This is a meta-problem (the tool qualifying itself) that depends on having the full traceability engine built first. Not blocking for MVP.

---

### D-09: ReqIF Import/Export

**Context:** Enterprises using DOORS or Polarion need interchange via the ReqIF standard.

**Decision:** Implemented in P7 (STORY-018). Full ReqIF 1.2 import and export via `specflow import --adapter reqif` and `specflow export --adapter reqif`. Uses Python's `xml.etree.ElementTree` with no external dependencies. Round-trip preservation of unmapped attributes via `reqif_metadata` frontmatter field. Export covers requirements only; architecture, design, and test export deferred. Bidirectional sync (third verb) deferred.

**Rationale:** ReqIF interchange is essential for supply-chain collaboration with DOORS/Polarion users. The Python implementation replaces the originally planned shell-script approach for maintainability and testability.

---

### D-10: Defect Tracking

**Context:** Production bugs don't fit the STORY or SPIKE model. They need severity, reproducibility, environment metadata.

**Decision:** DEF-* artifacts in `_specflow/work/defects/`. Links to V-model via `fails_to_meet` (which requirement is broken) and `exposed_by` (which test caught it). Closed by a STORY or commit. On closure, the challenge engine's reactive mode automatically extracts a prevention pattern.

**Rationale:** Bugs are work items (something to do), not spec items (something to verify against). The DEF lifecycle (open -> investigating -> fixing -> verified -> closed) is distinct from the spec lifecycle (draft -> approved -> implemented -> verified).

---

### D-11: Typo Cascade Defense

**Context:** A human fixing a typo in REQ-001.md should not flag the entire downstream architecture as suspect. But a single-character change from "SHALL" to "SHOULD" is semantically massive.

**Decision:** 3-tier defense, all zero-token:
1. `update_type: minor` frontmatter field — user explicitly declares cosmetic edits
2. `specflow fingerprint-refresh` command — convenience wrapper
3. Magnitude heuristic fallback — git-based ratio check (<5% = auto-classify minor)

**Rationale:** Explicit intent is better than LLM or Levenshtein guessing. Levenshtein on multi-line markdown is unreliable. LLM calls in pre-commit hooks are slow and expensive. The frontmatter field is explicit, instant, and free. Conservative default: when in doubt, cascade.

---

### D-12: Baseline Storage

**Context:** Compliance requires snapshots of the complete project state at milestones. How to store and compare baselines?

**Decision:** One YAML file per baseline in `.specflow/baselines/`, immutable after creation. Includes artifact statuses, fingerprints, and test summaries. `specflow baseline diff` reads two files directly — no git round-trip needed.

**Rationale:** Each baseline is a standalone file that an LLM or human can diff side-by-side. History is explicitly visible in the repo. Separate files prevent accidental corruption of a monolithic baseline store.

---

### D-13: Lean Artifact Growth (No "Promote" Command)

**Context:** A change that started small might grow in scope. Should there be an explicit mechanism to "promote" lean artifacts to full specs?

**Decision:** No promote command needed. Lean artifacts grow naturally. When more acceptance criteria are added, when architecture links are created, when the artifact is reviewed — it just becomes a fuller spec through standard workflow. No ceremony around the transition.

**Rationale:** An explicit "promote" command creates a ceremony around something that should be gradual. The framework already tracks everything — if a REQ started lean and gained 5 acceptance criteria and 3 links, it's just a well-developed REQ. The origin story is in the git log.

---

### D-14: Coexistence with User AGENTS.md / CLAUDE.md

**Context:** Users often have existing AGENTS.md or CLAUDE.md files with their own conventions. SpecFlow must not destroy them.

**Options considered:**
- Overwrite — destroys user content, unacceptable
- Marker-based merge (update only between markers) — overengineered
- Append during install, simple prompt on reinstall

**Decision:** Append during install. The install command asks which file to target (AGENTS.md, CLAUDE.md, etc.) and appends the SpecFlow instructions section. On reinstall, prompt: "SpecFlow section already exists, overwrite? [y/n]".

**Rationale:** Simple. No merge logic, no markers, no parsing. The SpecFlow section is clearly delineated with a header so users can move or edit it manually if needed.

---

### D-15: Ephemeral Installation Model

**Context:** Installing frameworks globally pollutes system environments and breaks the principle of "Compliance as Code" (where compliance engines must be version-locked to the repository to guarantee reproducible results across machines).

**Decision:** SpecFlow is not installed globally. Users will initialize it in their project directory using `uv run specflow init`, acting exactly like `npx`. This fetches the tool ephemerally, locks it to the local `.venv` or `pyproject.toml`, and scaffolds `.specflow/` and `.claude/skills/` locally.

**Rationale:** This mimics modern javascript tooling (`npx`), ensuring zero system-level pollution while guaranteeing that every developer cloning the repository runs the exact same version of the compliance engine.

---

### D-16: Python-Primary, Shell Wrappers Optional

**Context:** P2's implementation revealed that the original design principle ("all programmatic commands call shell scripts internally") led to ~1000 lines of inline Python duplicated inside shell scripts. The Python CLI already bypassed these scripts entirely — `commands/validate.py` dispatched directly to `lib/validation.py` and `lib/artifacts.py`, never invoking the shell scripts. Bug fixes had to be applied in two places, and the scripts couldn't reliably import from the installed `specflow` package.

**Options considered:**
- Shell-primary (original intent) — Python CLI calls shell scripts, which contain all logic
- Python-primary, no shell scripts — delete scripts entirely
- Python-primary, shell scripts as thin wrappers — keep scripts as 3-line delegators for CI/CD

**Decision:** Python-primary with optional thin shell wrappers. All deterministic logic lives in Python `lib/` modules, exposed via `specflow <subcommand>` CLI commands. Shell scripts in `scripts/` are 3-line wrappers (`exec uv run specflow artifact-lint --type <check> "$@"`) that exist solely for CI/CD pipeline compatibility. Future phases (P3 CRUD, P4 impact, P6 compliance) must implement new logic as Python lib functions + CLI subcommands, not as standalone shell scripts.

**Rationale:** Python modules are testable, importable, type-checkable, and have a single maintenance point. Shell wrappers preserve backward compatibility at zero maintenance cost. The P2 duplication incident proved that non-trivial logic in shell scripts is unmaintainable when the same logic must exist in Python for the CLI.

---

### D-17: Skills Are the Primary User Interface

**Context:** The architecture doc presented two parallel user-facing command surfaces: conversational skills (`/specflow-artifact-review`) and programmatic CLI (`uv run specflow artifact-lint`). Users experienced confusion about which surface to use and when. The intended workflow is that skills orchestrate everything — calling CLI commands internally as needed.

**Decision:** Users interact with SpecFlow exclusively through `/specflow-*` skill commands in their AI coding tool (Claude Code or OpenCode). The Python CLI (`specflow artifact-lint`, `specflow status`, etc.) is infrastructure — called by skills internally, by CI/CD pipelines, and by power users who know what they're doing. Documentation and onboarding teach skills first; CLI is referenced as "under the hood."

**Rationale:** The user's mental model should be: type a `/specflow-*` command, it just works. The skill decides whether to run the program silently or engage in conversation based on context. Presenting two parallel surfaces forces users to make meta-decisions about which tool to use, violating the modeless design philosophy (D-03).

---

### D-18: Frozen, Behavior-Paired Link-Role Vocabulary

**Context:** A project on an older SpecFlow that was driven by free-chat (rarely invoking skills) accumulated ~101 ad-hoc link roles, and an agent proposed a "1.9.1" adding 8 new core roles (`extends`, `mandates`, `cancels`, `deprecates`, and inverse roles `superseded_by` / `derives` / `refines` / `produces`). The proposal misdiagnosed the cause: unknown roles are a **warning, not a rejection** (`lib/lint.py`), so nothing forced the proliferation — it came from unconstrained authoring. The proposed roles also duplicated existing semantics or belonged in a different mechanism.

**Options considered:**
- Expand the core vocabulary with the 8 proposed roles
- Add inverse roles so relationships can be authored from either end
- Keep the vocabulary frozen; close the real gaps with behavior + status

**Decision:** The link-role vocabulary is **frozen and behavior-paired** — a role exists only when a query or validation consumes it (the "dead vocabulary" principle). New roles arrive through packs with matching behavior, never ad-hoc. Three rules follow:
- **Inverses are queries, not vocabulary.** Each edge is stored once and traversed both ways; `specflow trace <ID>` shows upstream and downstream. No `superseded_by` / `implemented_by` / `refines`.
- **Lifecycle is status, not links.** Retirement is modeled as `status`: `superseded` (has successor via the `supersedes` link), `cancelled` (terminated, no replacement), `deprecated` (discouraged). Added in 1.9.1 to spec/work schemas. No `cancels` / `deprecates` roles.
- **Near-misses get normalized, not blessed.** `lib/role_normalize.py` maps common ad-hoc roles to their canonical equivalent and `artifact-lint` surfaces the suggestion, keeping the vocabulary self-reinforcing even under free-chat authoring.

**Rationale:** Adding roles without consuming behavior is dead vocabulary that fragments traceability and invites further drift. `derives_from` already carries evidence lineage and `refined_by` covers additive specs for every query that exists, so `extends` / `mandates` / broadened `informs` add ambiguity without capability. The durable fix for sloppy authoring is a louder, more helpful linter plus a real home for lifecycle states — not a bigger dictionary.

---

### D-19: Mid-Project Adoption via an Opt-In Pack (As-Built Baseline)

**Context:** SpecFlow's narrative and tooling were greenfield-only: `init → discover → plan → execute → ship`, with ReqIF the sole import path. A team with an *existing* codebase had no guided way in — they'd hand-author every artifact for code that already exists, or pretend to start at day zero. Yet the primitives for adoption already existed and were lifecycle-agnostic: `create` accepts any valid status directly (no transition prerequisite), `baseline create` snapshots whatever artifacts exist regardless of status, and `detect orphan-code --retro-link` plus `reconcile` already do retroactive code↔artifact linking.

**Decision:** Adoption is delivered as an **opt-in `adoption` pack** (not a core skill), because greenfield users who started with `/specflow-init` never need it — only brownfield adopters install it (`/specflow-init --preset adoption`). The pack adds a single skill, `/specflow-adopt`, that drives the existing CLI (zero new Python). The one new concept is the **as-built baseline**: inventory the project → backfill core artifacts (REQ/ARCH/DDD/STORY/DEC/UT/IT/QT) describing what already exists → cut `baseline adoption-v0`, the reference point from which `ship`/`audit`/`change-impact-review` measure drift. Provenance is recorded with **existing fields only** — `tags: [backfilled]` + `rationale` — no new status, no new artifact type, no schema change (consistent with D-18's frozen-vocabulary discipline). Adoption is **incremental and resumable**, not one-shot: one subsystem boundary per pass, `detect orphan-code` as the progress meter, interleaved with forward work (new features stay un-`backfilled`, governed by the normal lifecycle). Conflicting sources (README↔code, doc↔test) are surfaced to the user, never silently resolved.

**Rationale:** Greenfield-lean core + opt-in pack matches the autoresearch pack model and keeps SpecFlow unburdened for the common case. Recording reality at honest statuses (`implemented`/`verified` for code that exists) honors accounting-not-policing without contorting the forward lifecycle. Reusing `create`/`baseline`/`detect`/`reconcile` means adoption adds no new code paths to maintain and can't drift from core semantics. The as-built baseline turns "migration" into a handshake: you don't leave anything, you capture what exists and govern change from there.

---

### D-20: Adoption Links Code via ARCH/DDD; STORY Reserved for Forward Action; `output_files` Globs Are Core

**Context:** D-19 (v0.1 of the adoption pack) instructed the agent to create "one STORY per logical unit of existing functionality" with `output_files` listing the code. In practice, on a brownfield repo, this produced hundreds of `status: verified` STORYs whose only real content was a file list — zombie action-artifacts, since the *action* had already happened. STORY records the *doing*; adoption records the *system side* (what exists). A backfilled STORY for shipped code is semantically wrong: there is nothing to do, and the forward-lifecycle machinery (draft→approved→implemented→verified, wave planning, reconcile) is meaningless for code that shipped years ago.

A second problem: D-19 listed `output_files` paths one-by-one. On a 200k-LOC Java monorepo, listing every `.java` file in an ARCH's `output_files` is non-starter ceremony, and the existing orphan meter silently *skipped* glob patterns (`**/*.java`) so glob-based coverage was invisible to the progress meter. The `reconcile` command also skipped globs, and the source-drift check did the same — three consumers with the same gap.

**Decision:** Three coordinated changes, all consistent with D-18's frozen-vocabulary discipline:

1. **Code-linking homes are ARCH and DDD, not STORY.** Adoption creates **zero** STORYs. ARCH `output_files` is the custody record for a component's code (typically a package glob like `src/main/java/com/acme/payments/**/*.java`); DDD `output_files` is the finer-grained file set it details. The orphan meter credits `output_files` on STORY/REQ/ARCH/DDD so lean (ARCH-only) adoption still moves the coverage meter. STORY is reserved for forward action: it appears only when someone changes adopted code, `specified_by` the existing ARCH, with `output_files` = the specific files the change touched (a subset of the ARCH's glob).

2. **`output_files` globs are a core feature.** `lib.files.expand_output_files` is the single source of truth for resolving output_files entries (literal paths + `**` globs, filtered through the same exclude rules as source scanning). All three consumers — orphan meter, reconcile, source-drift lint — route through it, so a package glob in any artifact's `output_files` is honored uniformly: credited for coverage, accepted as reconcile evidence, and hash-checked for drift.

3. **Completeness is derived from the graph, not stored.** `specflow adopt status` is a new subcommand that projects adoption progress and per-artifact completeness on demand: coverage %, per-ARCH boundary dashboard (depth skeleton/full, drift flag, parent REQ), per-artifact report (realization neighbors, acceptance-criteria count, linked tests, provenance, depth, gaps, drift). `specflow brief` gains an Adoption section gated on `backfilled` tags. No `adoption-progress.yaml` state file — the graph + `backfilled` tag + `source-fingerprints.yaml` already encode everything; projecting them avoids a second source of truth that would drift.

The default huge-repo strategy becomes **skeleton-first**: one ARCH per component across the whole project (no REQ, no DDD, no STORY) gets every component under coverage with 15-30 artifacts, then `adopt status` flags which components deserve REQ (behavior) + DDD (internals) deepening based on churn, criteria count, missing tests, and drift.

**Rationale:** Semantically, code realizes an architecture — a backfilled STORY for shipped code is a category error. Concentrating code refs on ARCH/DDD is also where the file/globs work *belongs* and where it compounds: one ARCH glob covers a whole package in every downstream view. Globs as a core feature are the only way to make huge-codebase adoption tractable. Deriving completeness from the graph respects the AGENTS.md "the repository IS the database" philosophy; a stored progress file would be a second source of truth guaranteed to drift. The skeleton-first strategy makes the sequential core *work* at any scale, and `adopt status` gives the agent a cheap steering signal for "where to deepen next" — replacing the orphan-count vs lean-depth tension from the v0.1 review. STORY remains the honest action artifact: a non-`backfilled` STORY is the marker that says "this adopted code is now under forward governance," which is the precise moment of graduation.

---

### D-21: Ops Pack (RUN/MONITOR) — a "Deployed-and-Observed" Memory Class; Domain-Neutral Core with Auto-Adaptive Concept→Artifact Maps

**Context:** SpecFlow's four memory classes — spec (REQ/ARCH/DDD), work (STORY/SPIKE/DEC/DEF), review (AUD/CHL/REVIEW), research (COMP/LOOP/EXPT/FIND) — covered what to build, what was done, what was reviewed, and what was *reproducibly* researched. Two regimes had no home: (1) **live/ephemeral data** that exists only briefly and is not reproducible (so frozen EXPT does not fit), and (2) **deployed systems observed over time** — a live model/bot, its drift, its retrain triggers. The question "how do I track artifacts/metrics in a live run?" had no SpecFlow answer. A second, broader problem: artifact-type choice ("is this a REQ, a STORY, an autoresearch goal, or a RUN?") relied on the user being an expert; the framework should adapt to the domain instead.

**Decision:** Two coordinated additions, both shipped as additive packs/skills with no breaking changes:

1. **A new `ops` memory class with two domain-neutral artifact types.** **RUN** is a deployment frozen at deploy-time (what is deployed — `deployed_ref` path/version/fingerprint — where, when, satisfying which REQ/ARCH; like a baseline but for a live system). **MONITOR** is an append-only timestamped observation of a RUN (free-form `metrics`, `signals`, `health`, and `captures` for ephemeral-data refs + freshness). Over time MONITORs *are* the observation/metric ledger; a breached MONITOR `informs` the next action (a retrain LOOP, a rollback DEC). The schemas carry **no** domain-specific fields (no drift/oos_decay/`model`) — those live in per-domain maps. This serves both ephemeral capture (RUN=the capture job, MONITOR=each batch + freshness) and MLOps (RUN=the deployment, MONITOR=performance/drift). Link-role discipline follows D-18: reuse `derives_from` (spec satisfaction / promoted-from lineage), `belongs_to` (MONITOR→RUN), `informs` (MONITOR→retrain/DEC); add `deploys` only if a `specflow trace` query proves ambiguity.

2. **Auto-adaptive concept→artifact maps.** Each domain checklist (e.g. `quant.md`, `ml.md`) opens with a Concept→Artifact Map (profit/edge → autoresearch metric, not a REQ; no-lookahead → REQ; live data → RUN/MONITOR; drift → MONITOR). `discover`/`plan` surface the relevant map when `domain` is set, and **packs contribute their own rows** (autoresearch→COMP/EXPT; ops→RUN/MONITOR), so a project's full concept→artifact mapping assembles from domain + installed packs — no user expertise required. A new `specflow domain suggest` (extensible signal table, quant/ml seeded) proposes a domain from dependency manifests for the user to confirm. `brief --next` becomes pack-state-aware (a running LOOP, a breached/stale MONITOR) so routing adapts to the project's actual subsystems.

**Rationale:** The frozen/reproducible semantics of EXPT deliberately exclude live systems — a deployment is ongoing, its metrics change, and the honest record is an append-only journal (MONITOR), not an immutable result. Keeping RUN/MONITOR domain-neutral is what makes the ops class useful beyond ML: a web service's RUN has latency/error-rate MONITORs; an embedded RUN has sensor MONITORs; drift is merely one signal type for quant. Pushing every domain-specific concept into a per-domain map (not the core schema) is the same discipline as D-18/D-20 — the core stays small and frozen, domains extend it. The maps are the generalization lever: a quant project, an ML pipeline, a game, or an embedded system each gets correct artifact guidance by adding a checklist + map, and the framework adapts rather than being quant-shaped. This directly addresses the "skill trigger quality / which-artifact" friction: guidance is surfaced at decision time with the *why*, not left for the user to derive. Runtime guidance lives natively (pack `context_snippet`, `SKILL.md`, `references/`); this `docs/` entry is the human design-log rationale only, consistent with D-18/D-20.

**Positioning (complement, not replacement):** RUN/MONITOR are deliberately a *governance ledger and chain of custody*, not a metrics store, a monitoring dashboard, or a reconciliation controller. They sit one layer **above** the MLOps/GitOps toolchain: `RUN.deployed_ref` points *at* an MLflow model version / W&B artifact / ArgoCD synced revision, and MONITOR records the *decision-grade* observations (a breach, a captured snapshot, freshness) — not the raw telemetry firehose, which stays in the specialist tool. The value SpecFlow adds is exactly what those tools are weak on: *why* this is live (`derives_from` the REQ/ARCH/EXPT) and *what was done about it* (breach `informs` a retrain LOOP / rollback DEC). This altitude is what keeps the abstraction universal across MLOps, GitOps, embedded, and web — and it is why the schemas stay free-form (`deployed_ref`, `metrics`, `signals`, `captures` accommodate any tool's identifiers without schema change). Known limits, tracked as deferred roadmap items: no auto-ingestion adapter (monitoring breach → flagged MONITOR via webhook); a single-valued `deployed_ref` (multi-component deployments use multiple `derives_from` links, no first-class bill-of-materials); and no dedicated rollback/supersede link role (handled today by a new RUN `derives_from` the prior + `retired` status).

---

### D-22: Docs as a Knowledge Surface — Recognized, Cited, Staleness-Checked; Never an Artifact Type

**Context:** A `docs/` folder carries prose that isn't a spec or a story — project-structure explanations, architecture rationale, experiment notes, onboarding. SpecFlow's artifacts (REQ→ARCH→DDD→STORY→DEC) are forward-looking, lifecycle-bound assertions the audit machinery checks; most `docs/` content is backward-looking or reference prose — a different genre. Two problems: (1) `docs/` was a complete blind spot — not indexed, not linked, not surfaced by `brief`/`status`/`trace`; (2) a latent coverage lie — `.md` in `SOURCE_EXTENSIONS` with `docs` absent from `EXCLUDE_DIRS` meant `docs/*.md` + root markdown counted as orphan *code*, silently deflating coverage. The question was whether docs should become a new artifact type. The user's instinct — "most doc edits should be git-history-only, no DEC" — ruled out lifecycle artifacts.

**Decision:** `docs/` (+ root markdown) is a recognized **knowledge surface**, NOT an artifact type. Five properties, all honoring "accounting, not policing" and D-18's frozen-vocabulary discipline:

1. **Recognized; excluded from code metrics.** `lib/files.py:docs_surface_paths` defines the configurable surface (a `docs:` block in config.yaml — `roots` default `docs/`, root-level `*.md` always recognized, `extra_files`, `exclude`); `scan_source_files` subtracts it, fixing the orphan-code miscount.
2. **Indexed + visible.** `lib/docs.py` discovers docs (reusing `compute_fingerprint`); `specflow rebuild-index` writes a derived `_specflow/docs-index.yaml` cache; `specflow brief` and `specflow adopt status` show a Docs surface block. No state file — files on disk remain source of truth.
3. **Citable both ways; no new link role.** Docs cite artifacts with inline `@ID` markers (`@ARCH-007`, `@DEC-018.2`); `extract_citations` (schema-driven prefix set so pack types count) + `build_reverse_index` map artifact → citing docs. The reverse direction is an optional `doc_refs:` frontmatter field (metadata, not a link role). D-18 respected.
4. **Staleness = warning only.** `check_stale` flags docs citing superseded/cancelled/deprecated artifacts; surfaced in `specflow detect stale-docs` and as a non-blocking `docs-staleness` audit concern. Never in the commit hook; never escalates an audit exit.
5. **Absorbed on adoption.** `/specflow-adopt` registers the docs surface at `adoption-v0`, so a mid-project start doesn't orphan existing docs.

Docs are NOT artifacts: no `DOC` prefix, no status, no `_index.yaml` lifecycle entry, no DEC on edit. The existing guards (`is_spec_artifact_path`, `discover_artifacts` scope, `document_changes.py` path filter) are unchanged. A new `/specflow-doc` skill (concise SKILL.md + 4 reference files) is the authoring/citing/syncing UX; `init`/`adopt`/`audit`/`brief` fold the surface in automatically. The one new CLI subcommand is `specflow detect stale-docs`.

**Rationale:** Forcing prose into the lifecycle machinery would be policing — it would fight the git-history-only instinct, pressure the frozen vocabulary (D-18), and flatten the free `docs/x/y/z` structure into `_specflow/<type>/`. The knowledge-surface model gives docs visibility (solving "outdated info hiding in a folder nobody knows about") at near-zero cost: a derived cache, a `@ID` convention, and a warning wing — none of which break, block, or add ceremony. The bug fix (docs miscounted as orphan code) is paid for by the same `docs_surface_paths` primitive. This is the D-20 code-linking philosophy extended to prose: record reality at the baseline, then account for drift — never police it.
