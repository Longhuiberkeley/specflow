# AGENTS.md

## Welcome, AI Agents!

This repository contains the **SpecFlow** framework: a zero-database, filesystem-native, and scale-adaptive specification tracking tool designed to bridge agile workflows and ASPICE/ISO-compliant verification.

You are interacting with the framework's source code, NOT a project using the framework. Follow these guidelines while developing SpecFlow.

## Design Philosophy

### 1. The Repository IS the Database
Do not write logic that relies on a database. All specifications, work tracking, and states are managed via Markdown files with YAML frontmatter. The file tree is the ultimate source of truth.

### 2. Modeless & Scale-Adaptive
Ceremony adapts to ambiguity. SpecFlow has no "Tracks" (Quick/Standard/Enterprise) and no personas. 
When building features, assume a single generalized agent handles everything. If a user has a simple task, SpecFlow handles it with lean artifacts. If the task is complex, it scales up to full V-Model tracking. Avoid creating toggles, settings, or modes for this behavior.

### 3. Bring-Your-Own-Standard
SpecFlow does not ship with proprietary "Extension Packs" or gated industry standards. Instead, it relies on open YAML schema definitions. Users import their own standards (e.g., a PDF of ISO 26262 or an internal policy document), and SpecFlow parses them into executable compliance schemas.

### 4. Compliance as Code
We enforce compliance through CI/CD. Traceability matrices, linkage rules, and checklist requirements are validated locally by zero-token shell/Python scripts, not just by LLM inference. Ensure any new validation rule you add operates deterministically.

### 5. Context Efficiency (Skill Standards)
When writing AI skills for SpecFlow's internal agents (e.g., inside `.claude/skills/`), strictly adhere to the standards outlined in `docs/skill-standards.md`.
- Keep `SKILL.md` under 500 lines.
- Store domain knowledge in `references/`.
- Store deterministic operations in `scripts/`.

### 6. Ephemeral Local Execution (Like npx)
We do not install SpecFlow globally for users. Users will install it directly into their repository ephemerally using `uv run specflow init` to scaffold directories. Ensure scripts and instructions respect this local execution paradigm to avoid system-level pollution.

### 7. The User Interface Is CLI Skills
The user's primary interface to SpecFlow is **`/specflow-*` conversational skills** invoked inside their AI coding assistant (Claude, Cursor, Cline, etc.). Raw CLI commands like `specflow create` or `uv run specflow artifact-lint` are the deterministic backend that skills call under the hood — they are implementation details, not the user-facing product.

When writing documentation, tutorials, or onboarding material, emphasize skill-based workflows (`/specflow-discover`, `/specflow-plan`, `/specflow-execute`, `/specflow-audit`). Only mention raw CLI commands when explaining what a skill does internally or when providing CI/automation examples.

The install mechanism (`uv tool install`, `uvx`, `python -m specflow`) is our concern, not the user's. Once installed, the user thinks in terms of skills, not shell commands.


<!-- SpecFlow section (auto-generated, do not edit manually) -->
## SpecFlow

**Stop.** This is a SpecFlow project. All engineering work flows through `/specflow-*` skills.

You are working in a **SpecFlow** project (spec-driven development). 
Specs and work items are Markdown + YAML files. Do not edit `.specflow/` manually.

### Interfaces
**Primary:** Use `/specflow-*` skills (e.g., `/specflow-discover`, `/specflow-plan`, `/specflow-execute`).
**CLI:** Use `specflow <cmd>` (e.g. `specflow trace <ID>`, `specflow update <ID>`) for automation and CI — not as a substitute for the skill workflow.

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

**Recall before you act:**
- Run `specflow status` for a project-wide overview (phase, counts, stale items).
- Scan `_index.yaml` files in relevant directories — they give you title + status + tags for every artifact without reading full bodies.
- Read `.specflow/state.yaml` for current phase; `.specflow/config.yaml` for domain context.
- Use `specflow trace <ID>` to walk the link chain and understand context.
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
- **Status Flow:** `draft` → `approved` → `implemented` → `verified`.
- **Updates:** Use `specflow update <ID> --status <status>` for all YAML/status changes.
- **Cascading:** When STORY code lands: `specflow update STORY-NNN --status implemented` then `specflow cascade-status STORY-NNN`.
- **Evidence:** Don't assume "verified." Capture the gate baseline *before* you change — test pass/fail counts and the names of currently-failing tests (or `artifact-lint` counts if no test runner exists yet). After implementing, re-run the *same* gate and report the delta ("baseline 2 failing {a,b} → still 2" / "now 3: +c, I caused it"). Never claim "no regressions" without a captured baseline to diff against.
- **Validation:** Run `specflow artifact-lint` after manual artifact edits.
- **Suspect resolution:** When an artifact is flagged `suspect`, actively propose resolution to the human (create DEF, mark resolved, or update the artifact). Do not let suspect flags sit unresolved.

### Routing
- Use core `/specflow-*` skills for ALL engineering work: requirements, architecture, stories, implementation, review, release.
- Packs (e.g., autoresearch) are **separate subsystems**. Only use pack skills when the user explicitly asks for that pack's domain. Never invoke pack skills for codebase exploration, bug investigation, feature implementation, or general engineering — those are core engineering.
- **By default**, new features go through the full pipeline. Typo fixes and trivial changes may use the lean path — but still trace to a STORY.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a blocking check, articulate: "Proceeding past [specific item]. Risk: [what could go wrong]. Noted."

### When to Escalate (Permanence Test)
SPIKE/STORY are throwaway; REQ/ARCH/DDD (and, for research, COMP) are durable. When work outgrows a one-off answer — you're building something reusable, iterating a second time, defining an interface, or needing it to survive this session — promote to a durable artifact when ANY of these holds:
- **Reuse** — the output will be depended on by future work (a dataset object, a pipeline, an API client), not a one-off answer.
- **Second pass** — you're iterating on the same thing again; it has stopped being exploratory.
- **Interface** — it defines a contract other code/research will call (→ ARCH/DDD).
- **Survival** — it must outlive this session / be understood by a fresh agent.

To promote, create the REQ/ARCH/DDD (or hand-author a new COMP) and link `derives_from` the originating SPIKE/COMP so context and traceability carry forward — don't silently keep spiking. See `specflow-execute/references/escalation-and-promotion.md` for the recipe.
<!-- End SpecFlow section -->

## Release Process

Follow these steps when releasing a new version:

1. **Update `CHANGELOG.md`** — add a version entry with date and highlights (grouped by category: features, fixes, docs)
2. **Update `pyproject.toml`** — bump the `version` field
3. **Update `ROADMAP.md`** — move shipped items from "Planned" to the released section
4. **Run the test suite:** `pytest tests/`
5. **Run self-audit:** `uv run specflow artifact-lint` and `uv run specflow project-audit`
6. **Commit:** `git commit -m "chore: release v1.x.x"`
7. **Tag:** `git tag -a v1.x.x -m "v1.x.x"`
8. **Push:** `git push --follow-tags`
9. **Create a GitHub Release** from the tag with the CHANGELOG excerpt as the body
10. **Publish to PyPI** (if applicable): `uv build && uv publish`

### CHANGELOG Format

```markdown
## v1.x.x (YYYY-MM-DD)

### Highlights
- One-line summary of the biggest change

### Features
- Description of new feature (#PR)

### Fixes
- Description of bug fix (#PR)

### Documentation
- Description of doc update
```
