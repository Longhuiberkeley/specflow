# SpecFlow Command Reference

> **This is the skill reference.** For raw CLI commands, see the [CLI Reference](cli-reference.md).

Interface specs for each `/specflow-*` slash command. For a lifecycle overview, see [lifecycle.md](lifecycle.md).

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
- `.claude/skills/` (or `.opencode/`, `.gemini/`) — 9 skill directories
- SpecFlow section appended to `AGENTS.md` (or `CLAUDE.md`)
- `.github/workflows/specflow.yml` (if CI requested)

---

## /specflow-discover

**One-line:** Author requirement artifacts through guided conversation.

**Composes:** `specflow status`, `specflow standards gaps`, `specflow create`, `specflow artifact-lint`

**Flow:**
1. Read project state; assess existing artifacts
2. Progressive disclosure conversation — one question at a time
3. Silent readiness assessment after each exchange (problem clarity, users, scope, success criteria)
4. **Standards gap check** — silently run `specflow standards gaps`; if uncovered clauses found, offer to scaffold REQs via `specflow create --from-standard <clause-id>`
5. Lean path (1 exchange) or full path (multi-exchange with domain deep-dive and cross-cutting concerns)
6. Create REQ artifacts with acceptance criteria; run `specflow artifact-lint`
7. Recommend `/specflow-plan` (full path) or `/specflow-execute` (lean path)

**Writes:**
- `_specflow/specs/requirements/REQ-*.md`
- For lean path: `_specflow/work/stories/STORY-*.md`
- `.specflow/state.yaml` (phase transition)

**Key rules:** 15-20 question cap; escape hatch on "move on"/"skip"; `(Recommended)` labels on defaults.

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
- Links: REQ→ARCH (`derives_from`), ARCH→DDD (`refined_by`), STORY→{REQ,ARCH,DDD}

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

## /specflow-artifact-review

**One-line:** Quality review of one or more specific artifacts — deterministic lint + checklist + LLM judgment.

**Composes:** `specflow artifact-lint`, `specflow checklist-run`

**Flow:**
1. Run deterministic validation (`specflow artifact-lint`) — zero tokens, all 6 checks
2. If blocking issues found, report and stop
3. Show status dashboard (`specflow status`)
4. Assemble review checklists by artifact type, domain tags, phase gates, and learned patterns
5. Run LLM-judged checks against non-automated checklist items
6. Report findings by severity: blocking, warning, info

**Writes:**
- `_specflow/specs/challenges/CHL-*.md` for findings (status `open`)

**Never:** skip automated checks, mutate target artifact status without user confirmation.

---

## /specflow-change-impact-review

**One-line:** Blast-radius review of recent commits/PRs via unreviewed change records.

**Composes:** `specflow document-changes` (precondition if no unreviewed DECs), `specflow change-impact`

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
1. **Deterministic core** (zero questions) — runs horizontal + vertical + cross-cutting checks via `specflow project-audit`
2. Offer **adversarial wings** — up to 16 lenses (security, performance, coupling, edge cases) via parallel subagents (Recommended: Yes, if preparing for a release/milestone)
3. Create AUD artifact for overall run and CHL artifacts for specific findings
4. Present severity breakdown, links to artifacts, next steps

**Writes:**
- `_specflow/specs/audits/AUD-*.md`
- `_specflow/specs/challenges/CHL-*.md`

---

## /specflow-ship

**One-line:** Release workflow — immutable baseline, change records, quick audit.

**Composes:** `specflow baseline create`, `specflow document-changes`, `specflow project-audit --quick`

**Flow:**
1. Ask for release tag; create baseline snapshot
2. Ask for previous tag/commit; generate DEC trail since that anchor
3. Run quick audit on final release state
4. Present release summary (baseline link, DEC list, audit summary)
5. **Advisory gate** — if audit severity ≥ error, warn and require explicit user confirmation to proceed

**Writes:**
- `.specflow/baselines/{tag}.yaml`
- `_specflow/work/decisions/DEC-*.md` (change records)
- Audit report

**Never:** skip the quick audit step.

---

## /specflow-pack-author

**One-line:** LLM-assisted authoring of a standards compliance pack from PDF, URL, or pasted text.

**Composes:** `specflow create`, pack validation script

**Flow:**
1. Ingest source (PDF, URL, or pasted text); extract clauses (`{id, title, description}`)
2. Confirm pack metadata with user; edit as needed
3. Optionally scaffold new artifact type schemas
4. Generate pack directory: `pack.yaml`, `standards/*.yaml`, optional `schemas/*.yaml`, `README.md`
5. Validate with `scripts/validate-pack.sh`
6. Present summary; recommend `/specflow-init --preset {name}` to install

**Writes:**
- `.specflow/packs/{name}/` with all pack files

**Key rule:** Never fabricate clauses not in the source. Preserve original clause IDs.

---

## /specflow-adapter

**One-line:** Manage CI workflows, artifact exchange, standards ingestion, and team RBAC through guided configuration.

**Composes:** `specflow ci generate`, `specflow hook install`, `specflow import`, `specflow export`, config.yaml edits

**Flow:**
1. Ask what the user wants to configure: CI, exchange, standards, team roles, or status overview
2. **CI Setup:** Choose provider, select operations, generate workflow file and pre-commit hook
3. **Exchange Setup:** Import from or export to external tools via exchange adapters (e.g., ReqIF)
4. **Standards Setup:** Configure standards ingestion adapters, point to `/specflow-pack-author` for pack creation
5. **Team Setup:** Configure RBAC roles, transition policies, independence rules, and generate CODEOWNERS
6. **Status:** Show current adapter and team configuration

**Writes:**
- `.specflow/adapters.yaml` (CI, exchange, standards config)
- `.specflow/config.yaml` (team roles and policies)
- `.github/workflows/specflow.yml` (CI workflow)
- `.git/hooks/pre-commit` (pre-commit hook)
- `CODEOWNERS` (role-based code ownership)

**Key rules:** Never overwrite existing CI workflows without confirmation. Explain that pre-commit hooks are advisory — real enforcement requires platform branch protection. RBAC is only active when role lists are non-empty.
