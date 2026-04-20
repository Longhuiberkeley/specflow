# SpecFlow — Design Decisions

Each decision documents the context, options considered, the resolution, and rationale. New contributors should read this before proposing changes to avoid re-litigating settled decisions.

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

**Decision:** The readiness assessment IS the scope detector. There is only one entry point (`specflow new`) and one generalized agent. If all required readiness dimensions are satisfied within the first exchange, the framework silently chooses the lean path (minimal artifacts, auto-approved). No explicit tracks, no toggles, and no distinct agent personas. Lean artifacts grow naturally through standard workflow.

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
2. `specflow tweak` command — convenience wrapper
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

**Decision:** Python-primary with optional thin shell wrappers. All deterministic logic lives in Python `lib/` modules, exposed via `specflow <subcommand>` CLI commands. Shell scripts in `scripts/` are 3-line wrappers (`exec uv run specflow validate --type <check> "$@"`) that exist solely for CI/CD pipeline compatibility. Future phases (P3 CRUD, P4 impact, P6 compliance) must implement new logic as Python lib functions + CLI subcommands, not as standalone shell scripts.

**Rationale:** Python modules are testable, importable, type-checkable, and have a single maintenance point. Shell wrappers preserve backward compatibility at zero maintenance cost. The P2 duplication incident proved that non-trivial logic in shell scripts is unmaintainable when the same logic must exist in Python for the CLI.

---

### D-17: Skills Are the Primary User Interface

**Context:** The architecture doc presented two parallel user-facing command surfaces: conversational skills (`/specflow-verify`) and programmatic CLI (`uv run specflow validate`). Users experienced confusion about which surface to use and when. The intended workflow is that skills orchestrate everything — calling CLI commands internally as needed.

**Decision:** Users interact with SpecFlow exclusively through `/specflow-*` skill commands in their AI coding tool (Claude Code, OpenCode, Gemini CLI). The Python CLI (`specflow validate`, `specflow status`, etc.) is infrastructure — called by skills internally, by CI/CD pipelines, and by power users who know what they're doing. Documentation and onboarding teach skills first; CLI is referenced as "under the hood."

**Rationale:** The user's mental model should be: type a `/specflow-*` command, it just works. The skill decides whether to run the program silently or engage in conversation based on context. Presenting two parallel surfaces forces users to make meta-decisions about which tool to use, violating the modeless design philosophy (D-03).
