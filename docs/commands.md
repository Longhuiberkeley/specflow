# SpecFlow Command Reference

> **This is the skill reference.** For raw CLI commands, see the [CLI Reference](cli-reference.md).

Interface specs for each `/specflow-*` slash command. For a lifecycle overview, see [lifecycle.md](lifecycle.md).

---

## /specflow-start

**One-line:** Orient on project state and route to the right next skill — the safe default when intent is vague.

**Composes:** `specflow brief --next`

**Flow:**
1. Run `specflow brief --next` (free, deterministic) for a next-step recommendation.
2. If unambiguous, tell the user exactly which skill to run next (e.g. *"REQs approved, no ARCH yet → `/specflow-plan`"*).
3. If intent is ambiguous, ask **one** disambiguating question (e.g. review one artifact vs. change-impact vs. whole-project audit), then route.

**Note:** This skill is a thin, host-neutral router — it never creates or modifies artifacts and never calls the Skill tool itself (it points you at the right `/specflow-*` skill). Prefer it over guessing. For a brand-new project, start with `/specflow-init` instead.

---

## /specflow-init

**One-line:** Bootstrap a SpecFlow project — scaffolds directories, installs skills, optional CI and standards packs.

**Composes:** `specflow init`, `specflow hook install`, `specflow ci generate`

**Flow:**
1. Ask: project type, standards preset, CI provider, compliance packs
2. Run `specflow init` with appropriate flags
3. Install git pre-commit hook
4. Optionally generate CI workflow
5. Report what was scaffolded; recommend `/specflow-discover`

**Writes:**
- `.specflow/` internals (config, schemas, checklists, adapters)
- `_specflow/` artifact directories (specs/, work/)
- `.claude/skills/` — 13 skill directories (incl. the `specflow-start` router, `specflow-doc`, `specflow-references`). OpenCode consumes this tree; other hosts (Cursor, Windsurf, …) get their own copy.
- SpecFlow section appended to the platform's `instruction_file` (`AGENTS.md` for Claude Code/OpenCode; leftover `CLAUDE.md` sentinels are stripped and a one-line `@AGENTS.md` import is added to `CLAUDE.md` so Claude Code keeps loading the shared guidance)
- `.github/workflows/specflow.yml` (if CI requested)

---

## /specflow-discover

**One-line:** Frame a fuzzy idea, then author requirement artifacts through guided conversation.

**Composes:** `specflow status`, `specflow standards gaps`, `specflow create`, `specflow artifact-lint`

**Flow:**
0. Frame a fuzzy idea first (only when readiness is near zero): ≤5 questions with recommended answers, premise ledger, option briefs plus do-nothing, hard stop, go / clarify / kill DEC tagged `framing`
1. Read project state; assess existing artifacts
2. Elicitation conversation — lean path after a complete first message, full path otherwise
3. Silent readiness assessment after each exchange (problem clarity, users, scope, success criteria)
4. **Standards gap check** — silently run `specflow standards gaps`; if uncovered clauses found, offer to scaffold REQs via `specflow create --from-standard <clause-id>`
5. Lean path (1 exchange) or full path (multi-exchange with domain deep-dive and cross-cutting concerns)
6. Create REQ artifacts with acceptance criteria; run `specflow artifact-lint`
7. Recommend `/specflow-plan` (full path) or `/specflow-execute` (lean path)

**Writes:**
- `_specflow/specs/requirements/REQ-*.md`
- For lean path: `_specflow/work/stories/STORY-*.md`
- `.specflow/state.yaml` (phase transition)

**Key rules:** five-question cap for framing only (elicitation has no numeric cap; readiness is assessed silently each exchange); escape hatch on "move on"/"skip"; `(Recommended)` labels on defaults; no self-approval of framing DECs.

---

## /specflow-plan

**One-line:** Break approved REQs into architecture, detailed design, and implementable stories.

**Composes:** `specflow artifact-lint`, `specflow create`

**Flow:**
1. Gate check — all target REQs must be `status: approved`
2. Read and summarize requirements back to user
3. Architecture proposal — discuss component structure; create ARCH artifacts
4. Detailed design (where needed) — create DDD artifacts for complex logic
5. Story breakdown using SPIDR decomposition — Spike, Path, Interface, Data, Rules
6. Validate with `specflow artifact-lint`
7. Present artifact set; user approves; recommend `/specflow-execute`

**Writes:**
- `_specflow/specs/architecture/ARCH-*.md`
- `_specflow/specs/detailed-design/DDD-*.md`
- `_specflow/work/stories/STORY-*.md`
- Links: REQ `refined_by` ARCH, ARCH `refined_by` DDD (the upper artifact holds the link; `ARCH derives_from REQ` is the legacy shape), STORY→{REQ,ARCH,DDD}

---

## /specflow-execute

**One-line:** Implement approved stories with test generation and optional phase closure.

**Composes:** `specflow go`, `specflow update`, `specflow create`, `specflow done`, `specflow artifact-lint`

**Flow:**
1. Verify stories are `status: approved`; check for suspect flags on linked specs
2. Present stories with priorities and dependencies; user selects
3. Implement in parallel waves (independent stories) or dependency order
4. Update story status to `implemented`
5. Create V-model verification tests: REQ→QT, ARCH→IT, DDD→UT
6. Validate with `specflow artifact-lint`
7. **Phase closure** (optional): offer to run `specflow done` — summarize accomplishments, extract prevention patterns, recommend archival

**Writes:**
- Source code per story specifications
- `_specflow/specs/unit-tests/UT-*.md`, `integration-tests/IT-*.md`, `qualification-tests/QT-*.md`
- Updated STORY/DDD status (`implemented`)

---

## Reviewing & checking: local vs. agent

Review in SpecFlow is a **spectrum across two axes** — *scope* (one artifact ↔ whole project) and *depth* (deterministic/local ↔ agent-judged). After the external-LLM removal, the entire deterministic tier needs **no agent and zero tokens** — a human or CI can run it directly. You only climb into agent territory when you ask for depth.

| | **Local / deterministic** (zero-token, no agent) | **Agent-judged** (your harness) |
|---|---|---|
| **One artifact** | `specflow artifact-lint`, `specflow checklist-run <ID>`, `specflow artifact-review <ID>` *(defaults to `--depth quick`)* | `/specflow-artifact-review <ID>` → `--depth normal` / `deep` |
| **Recent changes** | `specflow change-impact` (suspect flags) | `/specflow-change-impact-review` |
| **Whole project** | `specflow project-audit --quick`, `specflow detect …` | `/specflow-audit` |

Rules of thumb:

- **Just want a quick local sanity check?** Run `specflow artifact-lint` (structural checks) or `specflow artifact-review <ID>` — both default to deterministic-only and cost nothing.
- **Want judgment on a specific artifact?** `/specflow-artifact-review <ID>`; add "go deep" / `--depth deep` for adversarial lenses.
- **Reviewing a whole project or release?** `/specflow-audit` (full) or `specflow project-audit --quick` (fast, deterministic core only).

The deterministic core always runs first in every path; the agent layer only adds the parts that genuinely need reasoning.

---

## /specflow-artifact-review

**One-line:** Quality review of one or more specific artifacts — deterministic lint + checklist + thinking technique prompts.

**Composes:** `specflow artifact-lint`, `specflow checklist-run`

**Flow:**
1. Run deterministic validation (`specflow artifact-review <ID>` composes `specflow artifact-lint`) — zero tokens, all deterministic checks
2. Stop only on blocking findings that name the artifact under review; blockers on other artifacts are reported as context
3. Assemble review checklists by artifact type, domain tags, phase gates, and learned patterns
4. Display agent-judged checks for the host agent to evaluate (self-contained, no external API)
5. Report findings by severity: blocking, warning, info

**Writes:**
- `_specflow/specs/challenges/CHL-*.md` for findings (status `open`)

**Never:** skip automated checks, mutate target artifact status without user confirmation.

---

## /specflow-change-impact-review

**One-line:** Blast-radius review of recent commits/PRs via unreviewed change records.

**Composes:** `specflow change-impact` (run `specflow document-changes` upstream first if you want change records for recent commits; the skill itself does not call it)

**Flow:**
1. Discover all DEC artifacts with `review_status: unreviewed`; if none found, exit cleanly (idempotent)
2. For each DEC, compute blast radius via `specflow change-impact`
3. Review impacted artifacts against architectural constraints and requirements
4. File CHL artifacts for findings; set DEC `review_status` to `reviewed` (clean) or `flagged` (issues)

**Writes:**
- `_specflow/specs/challenges/CHL-*.md` for findings
- Updated DEC `review_status`

**Key property:** Idempotent — running twice with no new commits does nothing. Work scales with delta, not project size.

---

## /specflow-audit

**One-line:** Full-project periodic health review — deterministic core with optional adversarial wings.

**Composes:** `specflow project-audit`

**Flow:**
1. **Deterministic core** (zero questions) — runs horizontal + vertical + cross-cutting checks via `specflow project-audit`; `specflow findings-baseline diff` separates new lint findings from the known debt recorded in `.specflow/findings-baseline.yaml`
2. Offer **adversarial wings** — the full lens catalog, 23 lenses (security, performance, coupling, edge cases, research) via parallel subagents (Recommended: Yes, if preparing for a release/milestone)
3. Create AUD artifact for overall run and CHL artifacts for specific findings
4. Present severity breakdown, links to artifacts, next steps

**Writes:**
- `_specflow/specs/audits/AUD-*.md`
- `_specflow/specs/challenges/CHL-*.md`

---

## /specflow-ship

**One-line:** Release workflow — verify, change records, lens pass, approval, then the immutable baseline.

**Composes:** `specflow renumber-drafts`, `specflow findings-baseline`, `specflow project-audit --quick`, `specflow verify`, `specflow phase-set`, `specflow document-changes`, `specflow risk-tier`, `specflow baseline create --evidence`

**Flow:**
1. Confirm the release tag (proposed from the last tag); pre-flight `specflow renumber-drafts` so slug IDs get sequential IDs before a baseline cites them, then accept the renumbered findings with `findings-baseline update --accept-new` on the user's go-ahead
2. Re-run the test suite and `project-audit --quick` — a red suite blocks the release; `specflow artifact-lint` must be green against the committed findings baseline (new escalating findings are fixed, or accepted as known debt with `findings-baseline update --accept-new` on the user's go-ahead)
3. Promote to verified (advisory): `specflow verify --all`, the `verifying-to-complete` gate, one Tier 2 `implemented → verified` batch on the user's go-ahead, then `phase-set verifying`
4. Generate the DEC trail since the previous tag
5. Adversarial lens pass, then present the release summary (DEC list, audit summary, risk profile from `specflow risk-tier`, confidence persisted on the DEC)
6. **Approval gate** — audit severity ≥ error warns; the release proceeds only on the user's explicit go-ahead
7. After approval: `baseline create <tag> --evidence`, record `phase-set complete`, and hand off

**Writes:**
- `.specflow/baselines/{tag}.yaml` and `{tag}-evidence.md`
- `_specflow/work/decisions/DEC-*.md` (change records) and DEC `risk_profile.confidence`
- Renumbered artifact IDs, `verified` statuses on approval, `.specflow/findings-baseline.yaml`
- Audit report

**Never:** skip the quick audit step.

---

## /specflow-doc

**One-line:** The `docs/` knowledge surface — write/cite/sync prose docs and flag staleness. Docs are recognized, indexed, and citable, but **never** lifecycle artifacts.

**Composes:** `specflow rebuild-index`, `specflow brief`, `specflow detect stale-docs`, `specflow project-audit`

**Flow:**
1. Author/revise the doc; cite specs inline with `@ID` markers (e.g. `@ARCH-007`, `@DEC-018`).
2. (Optional) add a `specflow-doc:` frontmatter block (title/audience/last_reviewed) — metadata only.
3. `specflow rebuild-index` → writes the derived `_specflow/docs-index.yaml` (doc → citations reverse index).
4. `specflow brief` → shows the Docs surface block (count, areas, top-cited).
5. `specflow detect stale-docs` → warns if a doc cites a superseded/cancelled/deprecated artifact.

**Writes:** `_specflow/docs-index.yaml` (derived cache). **Never** writes an artifact, an `_index.yaml` lifecycle entry, or a DEC — editing a doc is git-history-only.

**Key property:** Docs are excluded from the code-orphan scan (so coverage metrics reflect code, not prose), and citations are scanned schema-driven so pack artifact types count. Staleness is warning-only (accounting, not policing). NOT for decisions (DEC), requirements (REQ), throwaway research (SPIKE), or reproducible experiments (EXPT).

---

## Best Practice Artifacts (BP)

**One-line:** Domain-specific best practices as first-class SpecFlow artifacts, seeded deterministically and traceable through the artifact graph.

**Composes:** `specflow practices seed`, `specflow practices validate`, `specflow create --type best-practice`

**Flow:**
1. **During discover** — `specflow practices seed` previews the domain's practices; `specflow practices seed --create` writes them as draft BPs the user approves.
2. **During plan** — in-scope approved BPs are bound to the work with `guided_by` links (REQ, ARCH or STORY holds `--add-link <BP-ID>:guided_by`); plan seeds BPs the same way if none exist yet.
3. **During execute** — the agent applies the bound BPs; `specflow artifact-lint` (`bp-application`) checks application from those graph bindings and test status.

**Writes:** `_specflow/specs/best-practices/BP-NNN.md`

**Key property:** BPs are traceable artifacts with `derives_from` (→ standards), `applies_to` (→ REQ/ARCH/DDD/STORY), and `supersedes` (→ older BPs). If a BP is wrong, supersede it and trace the impact. No external API calls.

---

## /specflow-pack-author

**One-line:** LLM-assisted authoring of a standards compliance pack from PDF, URL, or pasted text.

**Composes:** `specflow create`, pack validation script

**Flow:**
1. Ingest source (PDF, URL, or pasted text); extract clauses (`{id, title, description}`)
2. Confirm pack metadata with user; edit as needed
3. Optionally scaffold new artifact type schemas
4. Generate pack directory: `pack.yaml`, `standards/*.yaml`, optional `schemas/*.yaml`, `README.md`
5. Validate with `.claude/skills/specflow-pack-author/scripts/validate-pack.sh`
6. Present summary; recommend `/specflow-init --preset {name}` to install

**Writes:**
- `.specflow/packs/{name}/` with all pack files

**Key rule:** Never fabricate clauses not in the source. Preserve original clause IDs.

---

## /specflow-adapter

**One-line:** Manage CI workflows, artifact exchange, and team RBAC through guided configuration.

**Composes:** `specflow ci generate`, `specflow hook install`, `specflow import`, `specflow export`, config.yaml edits

**Flow:**
1. Ask what the user wants to configure: CI, exchange, team roles, or skill/schema upgrades
2. **CI Setup:** Choose provider, select operations, generate workflow file and pre-commit hook
3. **Exchange Setup:** Import from or export to external tools via exchange adapters (e.g., ReqIF)
4. **Team Setup:** Configure RBAC roles, transition policies, independence rules, and generate CODEOWNERS
5. **Upgrades:** Refresh copied skills, schemas, and checklists after a SpecFlow upgrade

**Writes:**
- `.specflow/adapters.yaml` (CI, exchange config)
- `.specflow/config.yaml` (team roles and policies)
- `.github/workflows/specflow.yml` (CI workflow)
- `pre-commit` in the git hooks directory git actually runs (honors `core.hooksPath`; a hooksPath from global or system config is refused unless `--force`)
- `CODEOWNERS` (role-based code ownership)

**Key rules:** `specflow ci generate` preserves an existing workflow file that differs (warn; `--force` backs it up and overwrites, `--dry-run` previews). The pre-commit hook blocks on RBAC, broken links and schema failures and warns on the rest — the local layer; durable enforcement is branch protection plus CI. `specflow hook install` never replaces a hook it does not own. RBAC is only active when role lists are non-empty.
