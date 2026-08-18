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

### 6. Invocation Model — bare `specflow` (Git source, not PyPI)
Users obtain SpecFlow from its Git source — `uv tool install git+https://github.com/Longhuiberkeley/specflow` (puts `specflow` on PATH) or `uvx --from git+... specflow ...` (ephemeral). The public PyPI `specflow` name is an unrelated JSON-Schema package, so SpecFlow is never resolved from PyPI. Once available, SpecFlow is invoked as **bare `specflow`** in skills, checklists, hooks, and hints — NOT `uv run specflow`, which only works where specflow is a declared project dependency (true in this repo only) and is the root cause of the consuming-project bootstrap bug. Clean CI runners are the one exception and bootstrap via `uvx --from git+...@v<ver>` (no specflow preinstalled). Dogfooding skill-driven flows in this repo assumes `specflow` on PATH (`uv tool install --from . specflow`).

### 7. The User Interface Is CLI Skills
The user's primary interface to SpecFlow is **`/specflow-*` conversational skills** invoked inside their AI coding assistant (Claude, Cursor, Cline, etc.). Raw CLI commands like `specflow create` or `specflow artifact-lint` are the deterministic backend that skills call under the hood — they are implementation details, not the user-facing product.

When writing documentation, tutorials, or onboarding material, emphasize skill-based workflows (`/specflow-discover`, `/specflow-plan`, `/specflow-execute`, `/specflow-audit`). Only mention raw CLI commands when explaining what a skill does internally or when providing CI/automation examples.

The install mechanism (`uv tool install`, `uvx`, `python -m specflow`) is our concern, not the user's. Once installed, the user thinks in terms of skills, not shell commands.


<!-- SpecFlow section (auto-generated, do not edit manually) -->
## SpecFlow

**Stop.** This is a SpecFlow project. Describe what you want in plain language — the matching `/specflow-*` skill engages automatically (slash optional). The raw `specflow` CLI is for CI and power users.

You are working in a **SpecFlow** project. Specs and work items are Markdown + YAML. **Never edit `.specflow/` manually** (config, state, schemas, indexes). Artifact YAML in `_specflow/` is CLI-managed: use `specflow update <ID>` for frontmatter/status/link changes. After a true hand-edit, run `specflow artifact-lint`.

### How to talk
Lead with the answer or next action. Then: what's happening · change · why · risks.
One idea per line. No preamble, no closer. First and last line must tell the reader what happened and what to do next.

### Interfaces
**Primary:** `/specflow-*` skills. Vague intent → `/specflow-start` or `specflow brief --next`.
**CLI:** `specflow trace <ID>`, `specflow update <ID>`, `specflow list`, `specflow transitions <ID>` (status maps are type-specific — never assume `draft → approved → implemented`).

### Lifecycle & V-model
`init → discover → plan → execute → artifact-review → ship` (audit / impact-review as needed).
Specs: REQ → ARCH → DDD. Tests: QT verifies REQ, IT verifies ARCH, UT verifies DDD.
Work (STORY / SPIKE / DEC / DEF in `_specflow/work/`) must link to a spec. Unlinked work is a SPIKE.

### Workflow rules
- Every code change traces to a STORY or REQ. No orphan work.
- **No self-approval:** never move `draft` → `approved` without a human. Present; they approve.
- Status changes: `specflow update <ID> --status …` after `specflow transitions <ID>`. Links: `--add-link TARGET:ROLE` / `--remove-link TARGET`.
- After STORY code lands: `specflow update STORY-NNN --status implemented` then `specflow cascade-status STORY-NNN`.
- Prove gates: capture a baseline *before* the change, re-run the same gate after, report the delta.
- Suspect flags: propose a DEF, a resolve, or an update — do not leave them sitting.
- Vague or fresh prompt: `specflow brief --next` first. Do not guess the phase.
- Packs (autoresearch, ops, adopt) are separate subsystems — invoke only when the user names that domain.
- User says skip / proceed anyway: do it, and name the risk.
- Reverse lifecycle ("go back to requirements"): `specflow phase-set <phase> --reason "…"` then the matching skill.
- Docs are a knowledge surface, not an artifact: "update the README" → `/specflow-doc` — never a new REQ/DEC for a doc edit.

### Memory (one line)
`specflow brief` is the digest. Artifacts are memory: spec/ = truth, work/ = what happened, impact-log/ = causality, links = `specflow trace`. Promote reusable / second-pass / interface work from SPIKE to REQ/ARCH/DDD (`derives_from`).
<!-- End SpecFlow section -->

## Release Process

Follow these steps when releasing a new version:

1. **Update `CHANGELOG.md`** — add a version entry with date and highlights (grouped by category: features, fixes, docs)
2. **Bump the version in both sources of truth** — `pyproject.toml` (`version`) and `src/specflow/__init__.py` (`__version__`). `config.py` reads `specflow.__version__`, so both must match.
3. **Update `ROADMAP.md`** — move shipped items from "Planned" to the released section
4. **Run the test suite:** `pytest tests/`
5. **Run self-audit:** `specflow artifact-lint` and `specflow project-audit`
6. **Commit:** `git commit -m "chore: release v1.x.x"`
7. **Tag:** `git tag -a v1.x.x -m "v1.x.x"`
8. **Push:** `git push --follow-tags`
9. **Create a GitHub Release** from the tag with the CHANGELOG excerpt as the body
10. **Publish to PyPI** (if applicable): `uv build && uv publish`

### CHANGELOG Format

The CHANGELOG follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — a bracketed
version and ISO date heading, and a `Total: N tests passing` line closing the entry:

```markdown
## [1.x.x] - YYYY-MM-DD

### Highlights
- One-line summary of the biggest change

### Features
- Description of new feature

### Fixes
- Description of bug fix

### Decisions / Docs
- D-NN (decision summary) / doc update

### Tests
- What was added; Total: N tests passing
```
