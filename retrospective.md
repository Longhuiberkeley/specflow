# SpecFlow Retrospective — Post-P8

**Date:** 2026-04-14
**Snapshot:** `master @ 2350afb`
**Scope:** All 8 phases (P0 Foundation → P8 Intelligence & Scaling) have shipped. This document assesses what landed against the original vision in `docs/plan.md`, identifies gaps, and defines the direction for the next chapter of work.

The retrospective is intentionally honest: principles that only partially landed are graded as such, confusing command names are called out as confusing, and deferred features are re-evaluated rather than restated.

---

## Table of Contents

1. [Vision-vs-reality gap](#1-vision-vs-reality-gap)
2. [End-to-end lifecycle](#2-end-to-end-lifecycle)
3. [Command surface rework](#3-command-surface-rework)
4. [Featured skill interface specs](#4-featured-skill-interface-specs)
5. [Missing connective tissue](#5-missing-connective-tissue)
6. [Documentation restructure](#6-documentation-restructure)
7. [Change-audit pipeline](#7-change-audit-pipeline)
8. [Project-audit design](#8-project-audit-design)
9. [Adversarial review: challenge lenses](#9-adversarial-review-challenge-lenses)
10. [Compliance rework — BYOC](#10-compliance-rework--byoc)
11. [Adapter framework](#11-adapter-framework)
12. [Dead-code disposition](#12-dead-code-disposition)
13. [Revised next-steps list](#13-revised-next-steps-list)
14. [Appendix A — old-to-new name map](#appendix-a--old-to-new-name-map)

---

## 1. Vision-vs-reality gap

Summary against the six design principles declared in `docs/plan.md`.

| Principle | Grade | One-line verdict |
|---|---|---|
| Modeless | **Delivered** | No mode flags; state is descriptive, not prescriptive. |
| Filesystem-native | **Delivered** | Markdown + YAML end-to-end; zero DB/cloud dependency. |
| Programmatic-first | **Delivered** | All logic in `lib/`; shell scripts are 3-line `exec` wrappers. |
| Ceremony adapts to ambiguity | **Delivered** | Readiness assessment + auto-lean path implemented. |
| Bring-Your-Own-Standard | **Partial** | Mechanism correct; feature undelivered. No real packs ship; one stub demo. |
| Cross-platform | **Partial** | Core CLI works on Windows via `uv run`; documented shell-wrapper entry points are Bash-only; git hook script is Bash; unsupported-agent detection does not degrade gracefully. |

### Evidence

**Modeless — Delivered.**
No user-facing mode flag exists. `src/specflow/lib/config.py:59` stores `state.yaml.current` but skills only *warn* on mismatch — `.claude/skills/specflow-discover/SKILL.md:11-16` explicitly lets users proceed through the warning. Search for mode-flag semantics (`--mode`, `MODE=`, etc.) returns zero matches in the CLI.

**Filesystem-native — Delivered.**
Grep for `sqlite|postgres|\.db"|mongo|redis` across `src/specflow/lib/` returns zero matches. Baselines (`lib/baselines.py:53-106`), impact log (`lib/impact.py:59-71`), standards (`lib/standards.py:19-42`), and config (`lib/config.py:65-74`) are all plain YAML on disk. Every artifact is a Markdown file with YAML frontmatter (`lib/artifacts.py:112-145`).

**Programmatic-first — Delivered.**
All 18 shell scripts in `scripts/` are exactly three lines: shebang, `set -euo pipefail`, `exec uv run specflow …`. Deterministic logic sits in `lib/`; command entry points (`commands/*.py`) import directly from lib modules rather than shelling out. Skills call `uv run specflow …` rather than embedding Python or shell.

**Ceremony adapts to ambiguity — Delivered.**
Readiness assessment at `.claude/skills/specflow-discover/references/readiness-assessment.md:1-32` defines four required dimensions; when met in a single exchange, the skill takes the lean path (`SKILL.md:34-44`): single REQ + single STORY, both auto-approved. There is no "promote" command; lean artifacts grow naturally via `specflow update`. Decision D-13 explicitly rejected a promote command.

**Bring-Your-Own-Standard — Partial.**
The mechanism works: `src/specflow/lib/scaffold.py:92-168` installs a pack, registering new artifact types and copying schemas. Runtime type registration at `lib/artifacts.py:148-156` adds types to module-level dicts without restart. The ecosystem, however, is effectively empty:

- Only one pack exists: `src/specflow/packs/iso26262/`.
- That pack's standard file (`packs/iso26262/standards/iso26262.yaml`) is **19 lines**, containing 5 clauses that are all explicitly labeled "Stub clause — …". Real ISO 26262 contains hundreds of requirements across 12 parts.
- `docs/plan.md:26` promised "PDF standard ingestion" for P6; `lib/standards.py` only reads YAML. The PDF path was never shipped.

The mechanism is correct. The feature didn't ship. The framework currently claims BYOS capability its only concrete artifact does not substantiate — one demo pack with stub clauses and a never-shipped PDF-ingestion path. "Partial" reflects that the pluggability exists but the delivered content is essentially zero.

**Cross-platform — Partial.**
Path abstraction uses `pathlib.Path` throughout `lib/`. `lib/platform.py:15-23` detects Claude Code / OpenCode / Gemini CLI. The picture is split by entry point:

- **Core CLI via `uv run specflow …`** works on Windows. Artifacts are plain YAML/Markdown; no POSIX-specific code paths in `lib/`.
- **Shell wrappers (`scripts/*.sh`)** all hardcode `#!/usr/bin/env bash`. No PowerShell equivalents. Windows users without WSL or Git Bash cannot run them.
- **Git hook script** (`specflow hook install` writes `.git/hooks/pre-commit`) is Bash; breaks on Windows without Git Bash.
- **Unsupported-agent detection** returns the platform name but no code path gracefully degrades — the vision's "degrades gracefully on Cursor, Windsurf, Cline" is aspirational.

If the documented entry point is `uv run specflow`, Windows works. If the documented entry point is `./scripts/foo.sh` (as AGENTS.md suggests for CI contexts), Windows is blocked on that path. The fix is not parallel `.ps1` wrappers everywhere — it's the adapter framework ([§11](#11-adapter-framework)) letting each adapter emit its own shell.

---

## 2. End-to-end lifecycle

The user journey from cold clone to shipped feature, side-by-side with the command surface that realizes it.

### Lifecycle flowchart

```
                        ┌───────────────┐
                        │  cold clone   │
                        └───────┬───────┘
                                ▼
                /specflow-init (preset? CI? standards?)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
      ┌───────────────────┐         ┌────────────────────┐
      │  lean path        │         │  full path         │
      │  (simple change)  │         │  (new capability)  │
      └─────────┬─────────┘         └──────────┬─────────┘
                ▼                              ▼
       /specflow-discover              /specflow-discover
          (1 exchange)                   (multi-exchange;
                │                         readiness gate)
                │     REQ.status=approved                 │
                ▼                              ▼
       /specflow-plan                  /specflow-plan
          (just STORY)                   (ARCH → DDD → STORY)
                │                              │
                │     STORY.status=approved    │
                ▼                              ▼
       /specflow-execute               /specflow-execute
          (impl + UT/IT/QT, parallel waves via specflow go)
                                │
                                ▼
                /specflow-artifact-review
                (deterministic lint + checklist + LLM +
                 optional adversarial lenses; auto-runs
                 dedup + similarity internally)
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
  iterate again        /specflow-release     /specflow-change-
                       (baseline +            impact-review
                        document-changes +    (per-commit/PR;
                        project-audit)         only unreviewed DECs)
                                │
                                ▼
                       /specflow-project-audit
                       (periodic; scope + depth chosen conversationally;
                        composes subagent fan-out)
```

### Tiered command table

**Tier 1 — featured user-facing skills.** These are what a user learns and uses day-to-day. Each is documented in `docs/commands.md` with full interface spec (see [§4](#4-featured-skill-interface-specs)).

| Skill | When to use |
|---|---|
| `/specflow-init` | Starting a new project; installing a standards pack |
| `/specflow-discover` | Capturing a new requirement |
| `/specflow-plan` | Breaking an approved REQ into architecture + stories |
| `/specflow-execute` | Implementing approved stories |
| `/specflow-artifact-review` | Reviewing one or more artifacts for quality |
| `/specflow-project-audit` | Periodic full-project health check |
| `/specflow-document-changes` | Emitting DEC records from git history (readable by humans) |
| `/specflow-change-impact-review` | Reviewing unreviewed DECs with LLM + blast-radius analysis |
| `/specflow-release` | Cutting a release: baseline + document-changes + quick audit |
| `/specflow-pack-author` | LLM-assisted authoring of a standards pack |

**Tier 2 — CLI commands available via the thin `/cmd [optional message]` skill wrapper pattern.** These are reachable by chat but not featured; use when composed from Tier 1 or invoked explicitly.

`specflow baseline`, `specflow status`, `specflow create`, `specflow update`, `specflow go`, `specflow done`, `specflow fingerprint-refresh` (was `tweak`), `specflow renumber-drafts` (was `sequence`), `specflow import`, `specflow export`, `specflow hook`.

**Tier 3 — CLI-only, intended for CI or power users.** No headline skill. Invoked from `specflow` directly or from CI workflows.

`specflow artifact-lint` (was `validate`), `specflow checklist-run` (was `check`), `specflow detect {dead-code,similarity}`.

---

## 3. Command surface rework

The confusing naming (validate / verify / check / audit / compliance / impact) was a product of phase-by-phase accretion; each phase introduced verbs without auditing the whole taxonomy. Post-P8 we rename for clarity.

### Rename table

| Old | New | Category | Notes |
|---|---|---|---|
| `specflow validate` | `specflow artifact-lint` | Tier 3 CLI | Programmer-familiar "lint" semantics |
| `specflow check` | `specflow checklist-run` | Tier 3 CLI | Verb-noun; what it does |
| `specflow verify` | `specflow artifact-review` | Tier 1 | LLM-driven review; composes lint + checklist-run + adversarial |
| `specflow audit` | `specflow project-audit` | Tier 1 | Scope marker disambiguates from artifact-review |
| `specflow compliance` | **removed** | — | Folded into `project-audit` as a scope choice |
| `specflow impact` | `specflow change-impact` | Tier 1 CLI | "Of what on what" is now explicit |
| `specflow tweak` | `specflow fingerprint-refresh` | Tier 2 | Says what it does |
| `specflow sequence` | `specflow renumber-drafts` | Tier 2 | Says what it does |
| `specflow detect` | unchanged | Tier 3 CLI | Already clear; CI-only |
| `specflow baseline` | unchanged | Tier 2 | |
| `specflow document-changes` | unchanged | Tier 1 | Already long and clear |
| `specflow init`, `status`, `create`, `update`, `go`, `done`, `hook`, `import`, `export` | unchanged | Various | Already clear |

### Featured skills (Tier 1) — final list

- `/specflow-init`
- `/specflow-discover`
- `/specflow-plan`
- `/specflow-execute`
- `/specflow-artifact-review`
- `/specflow-project-audit`
- `/specflow-document-changes`
- `/specflow-change-impact-review`
- `/specflow-release`
- `/specflow-pack-author`

### Removed

- `/specflow-validate` — merged into artifact-review
- `/specflow-check` — merged into artifact-review
- `/specflow-compliance` — merged into project-audit
- `/specflow-detect` — folded into artifact-review and project-audit; CLI remains for CI

### Python filename renames

- `lib/validation.py` → `lib/lint.py`
- `commands/validate.py` → `commands/artifact_lint.py`
- `commands/verify.py` → `commands/artifact_review.py`
- `commands/check.py` → `commands/checklist_run.py`
- `commands/impact.py` → `commands/change_impact.py`
- `commands/tweak.py` → `commands/fingerprint_refresh.py`
- `commands/sequence.py` → `commands/renumber_drafts.py`
- `.claude/skills/specflow-verify/` → `.claude/skills/specflow-artifact-review/`

Full rename (including updates to phase docs that reference old names). Phase docs are being archived (see [§6](#6-documentation-restructure)), so that churn is subsumed into the archive move.

---

## 4. Featured skill interface specs

One block per Tier 1 skill. These are the contract for each skill — what it reads, writes, promises to do. This section feeds directly into `docs/commands.md` once the retrospective recommendations are implemented.

### /specflow-init

**One-line:** Bootstrap a SpecFlow project.

**Composes:** directory scaffolding, schema installation, optional pack installation, optional CI template.

**Inputs:**
- Project root directory (default: cwd)
- Preset selection (conversational: "what kind of project?")
- Optional standards pack
- Optional CI template (GitHub Actions today; more providers deferred)

**Reads:** nothing on first run; on re-init, reads existing `.specflow/config.yaml` to avoid clobber.

**Writes:**
- `.specflow/config.yaml`, `.specflow/state.yaml`
- `.specflow/schema/*.yaml` (from templates)
- `.specflow/checklists/` (from templates)
- `_specflow/specs/**/_index.yaml` scaffold
- `_specflow/work/` scaffold
- `.github/workflows/specflow.yml` (if CI requested)
- Standards pack content if a pack chosen

**Side effects:** none beyond directory creation.

**Exit:** summary of what was scaffolded + recommended next skill (`/specflow-discover`).

---

### /specflow-discover

**One-line:** Author requirement artifacts through conversation.

**Composes:** readiness assessment → lean or full path → REQ creation (+ STORY for lean path).

**Inputs:**
- Free-text description of the need
- Optional domain context (LLM may ask)

**Reads:**
- `.specflow/state.yaml` (for phase awareness)
- `_specflow/specs/requirements/*.md` (to detect duplicate REQs via dedup)
- `.specflow/checklists/discovery/*.yaml` (domain prompts)

**Writes:**
- `_specflow/specs/requirements/REQ-*.md` (status `approved` if lean, `draft` otherwise)
- For lean path: `_specflow/work/stories/STORY-*.md` (status `approved`)
- `.specflow/state.yaml` (transition to `specifying` or next phase)

**Side effects:** transitions project state; links REQs upstream if user mentions related existing REQs.

**Exit:** artifact IDs created + next recommended skill (`/specflow-plan` for full path, `/specflow-execute` for lean).

---

### /specflow-plan

**One-line:** Break approved REQs into architecture, detailed design, and implementable stories.

**Composes:** REQ gate check → ARCH design conversation → optional DDD → STORY breakdown.

**Inputs:**
- Target REQ IDs (explicit or LLM-resolved)
- Free-text architectural preferences

**Reads:**
- `_specflow/specs/requirements/*.md` (source REQs — gates on `status: approved`)
- `_specflow/specs/architecture/*.md` (existing ARCHs for reuse)
- `_specflow/specs/detailed-design/*.md`
- `.specflow/schema/` (for new artifact validation)

**Writes:**
- `_specflow/specs/architecture/ARCH-*.md`
- `_specflow/specs/detailed-design/DDD-*.md` (when granularity warrants)
- `_specflow/work/stories/STORY-*.md`
- Links: REQ→ARCH (`refined_by`), ARCH→DDD (`specified_by`), STORY→{REQ,ARCH,DDD}

**Side effects:** none.

**Exit:** artifact summary + story count + next skill (`/specflow-execute`).

---

### /specflow-execute

**One-line:** Implement approved stories; generate unit/integration/qualification tests.

**Composes:** STORY gate check → wave planning (`specflow go --dry-run`) → parallel wave execution → test artifact creation.

**Inputs:**
- Target STORY IDs (default: all `status: approved` stories)
- Optional wave-size override

**Reads:**
- `_specflow/work/stories/STORY-*.md` (gates on `status: approved`)
- Linked ARCH, DDD, REQ artifacts
- `.specflow/schema/`

**Writes:**
- Source code (language-agnostic; writes wherever the story specifies)
- `_specflow/specs/tests/unit/UT-*.md`
- `_specflow/specs/tests/integration/IT-*.md`
- `_specflow/specs/tests/qualification/QT-*.md`
- Updated STORY status (`implemented`)
- `.specflow/locks/*.json` (during execution; released on completion)
- `.specflow/execution-state.yaml`

**Side effects:** code changes; status transitions on stories and tests. Locks are acquired per-artifact for parallel safety.

**Exit:** implemented story count + test count + next skill (`/specflow-artifact-review`).

---

### /specflow-artifact-review

**One-line:** LLM-driven quality review of one or more artifacts.

**Composes:** `artifact-lint` (deterministic) → `checklist-run` → LLM judgment → optional adversarial lenses (see [§9](#9-adversarial-review-challenge-lenses)).

**Inputs:**
- Artifact IDs (explicit) or free-text scope ("the auth redesign", "everything changed this week")
- Depth selector: `quick` | `normal` | `deep` (LLM resolves or user chooses)
- Optional lens selection (adversarial modes)

**Reads:**
- `_specflow/specs/**/*.md` (target artifacts)
- `_specflow/work/**/*.md`
- `.specflow/checklists/review/*.yaml`
- `.specflow/schema/*.yaml`

**Writes:**
- `_specflow/specs/challenges/CHL-*.md` — one artifact per finding, status `open`
- `.specflow/impact-log/*.yaml` — if fingerprints shift during review
- (Never mutates target artifact status without user confirm)

**Side effects:** creates CHL links to targets; may recompute fingerprints.

**Exit:** findings summary (by severity) + "improve now?" prompt offering concrete remediation commands.

**Exit codes (CLI):** 0 = clean; 2 = open findings; 3 = tool error.

---

### /specflow-project-audit

**One-line:** Project-wide health review, scope and depth chosen conversationally.

**Composes:** horizontal fan-out (per artifact type) + vertical fan-out (per V-model thread) + cross-cutting concerns, all via subagents.

**Inputs (conversational):**
- Scope:
  - (a) Internal coherence only
  - (b) Against installed standard X (auto-detected from `.specflow/standards/`)
  - (c) Both
  - (d) Full (above + adversarial lenses)
- Depth:
  - Quick (~2 min, programmatic-heavy, sampled artifacts)
  - Detailed (~10 min, LLM per artifact type)
  - Exhaustive (~30 min, per-artifact + cross-cutting + full lens fan-out)

**Reads:**
- Entire `_specflow/specs/` and `_specflow/work/`
- `.specflow/standards/*.yaml` (auto-detection source)
- `.specflow/baselines/*.yaml` (drift anchors)
- `.specflow/impact-log/`

**Writes:**
- `.specflow/audits/{timestamp}/report.md` — top-level summary
- `.specflow/audits/{timestamp}/subagent-*.md` — per-lens/per-chunk findings
- `_specflow/specs/audits/AUD-*.md` — audit artifact (new type) with `review_status: open`
- CHL artifacts for specific findings

**Side effects:** may spawn many subagents; always announces expected token budget before starting.

**Exit:** summary + link to audit report + severity counts.

**Exit codes (CLI):** 0 = clean; 2 = findings at severity ≥ warn; 3 = findings at severity ≥ error; 4 = tool error.

---

### /specflow-document-changes

**One-line:** Emit decision records (DECs) from git history — meant to be read by humans.

**Composes:** git log since anchor → grouping by concern → DEC artifact generation.

**Rationale for standalone existence:** safety-critical users are expected to *read* DECs themselves as part of their audit process. This skill does not perform LLM review; it produces readable records. LLM review is a separate skill (`/specflow-change-impact-review`) that the user invokes when they want automated analysis.

**Inputs:**
- Anchor: baseline tag, commit SHA, or date (default: most recent baseline)
- Optional filter: paths, artifact types, authors

**Reads:**
- Git history via `git log`
- `.specflow/baselines/` (for default anchor resolution)
- `_specflow/specs/**` (to tag which artifacts changed)

**Writes:**
- `_specflow/specs/decisions/DEC-*.md` with `review_status: unreviewed`
- Links from DEC to affected artifacts

**Side effects:** none beyond DEC creation. Does not flip any existing status.

**Exit:** DEC count + list of IDs + "run `/specflow-change-impact-review` to analyze" prompt.

---

### /specflow-change-impact-review

**One-line:** LLM-review of unreviewed DECs, scoped by blast radius.

**Composes:** preflight `document-changes` (if no unreviewed DECs exist) → blast-radius computation → subagent review per DEC → `review_status` flip.

**Key property:** idempotent. Running twice in a row with no new commits finds nothing to do. Work scales with the delta, not project size.

**Inputs:**
- Optional DEC filter (default: all `review_status: unreviewed`)
- Optional review depth (quick / normal / deep)

**Reads:**
- `_specflow/specs/decisions/DEC-*.md`
- `.specflow/impact-log/`
- Linked artifacts (blast-radius expansion)

**Writes:**
- CHL artifacts for findings, linked to affected DEC + downstream artifacts
- Updates DEC `review_status`: `unreviewed` → `reviewed` or `flagged`
- `.specflow/impact-log/*.yaml` entries for suspect cascades

**Side effects:** may flag downstream artifacts as `suspect`; user clears via `specflow change-impact --resolve`.

**Exit:** DEC-reviewed count + findings summary + suspect-artifact list.

---

### /specflow-release

**One-line:** Cut a release: baseline + document-changes + quick project-audit.

**Composes:** `specflow baseline create` → `/specflow-document-changes` → `/specflow-project-audit --quick` → release report.

**Inputs:**
- Release version / tag (conversational)
- Optional "do full audit instead of quick"

**Reads:** everything the three sub-skills read.

**Writes:**
- `.specflow/baselines/{tag}.yaml`
- DEC artifacts since previous baseline
- `.specflow/audits/{release-tag}/report.md`
- Release summary at `.specflow/releases/{tag}.md`

**Side effects:** creates an immutable baseline; subsequent changes are measured against it.

**Exit:** release summary + links to baseline, DECs, audit report.

**Release-gate behavior:** if audit severity exceeds `error`, release is advisory only — user must explicitly confirm to proceed.

---

### /specflow-pack-author

**One-line:** LLM-assisted authoring of a standards pack from PDF, URL, or pasted text.

**Composes:** source ingestion → clause extraction → schema scaffolding → pack manifest generation → optional install.

**Replaces:** the P6 PDF-ingestion promise that was never shipped as a parser. Now it's an LLM-assisted authoring tool, which is more pragmatic and more correct.

**Inputs:**
- Source: PDF file, URL, or pasted text
- Pack name, version
- Optional artifact type(s) the pack should add

**Reads:**
- Source document
- `.specflow/schema/` (to know what schemas already exist)

**Writes:**
- `.specflow/packs/{name}/pack.yaml`
- `.specflow/packs/{name}/standards/{name}.yaml`
- `.specflow/packs/{name}/schemas/*.yaml` (if pack defines new artifact types)
- `.specflow/packs/{name}/README.md`

**Side effects:** none until user runs `specflow init --pack {name}` to install.

**Exit:** pack directory + preview of generated clauses + install command.

---

## 5. Missing connective tissue

### Onboarding — poor

- `README.md` is **1 line** at commit `2350afb` (confirmed via Read).
- `docs/` is organized by phase number (`docs/phases/P0..P8-*.md`), not by user task. This is maintainer-view, not user-view.
- No `docs/getting-started.md`, `docs/quickstart.md`, or tutorial. A fresh user has no "start here" signal.

### Discoverability — fair

- `specflow --help` lists 18 commands alphabetically by argparse order; no workflow grouping. Post-rename this is worse (more commands, same lack of structure).
- Skill names are self-explanatory for Claude Code users who see them via `.claude/skills/`; other users never encounter them unless they read `AGENTS.md:35-61`.

### Recovery — mixed

- Errors are diagnostic but **not prescriptive.** `lib/validation.py` reports which fields are missing or which IDs are malformed, but never tells the user which command to run to fix them.
- Fingerprint mismatch does not suggest `fingerprint-refresh` (the rename is an improvement over "tweak" but the error guidance is still missing).
- Lock recovery: `lib/locks.py:94` `break_stale_lock()` exists but is never called. A crashed `specflow go` wave leaves a stale lock with no exposed recovery command. This is a half-shipped feature (see [§12](#12-dead-code-disposition)).

### Required fixes

1. **Write `README.md` + `docs/getting-started.md`.** Tutorial-shaped, transcript-style. Defer the tutorial until after the command rename lands so we don't obsolete it.
2. **Group `specflow --help` output by workflow phase** using argparse subparser groups (Discover / Plan / Execute / Review / Release / CI).
3. **Make errors prescriptive.** When lint reports a missing field, append the exact `specflow update` command that would fix it.
4. **Expose recovery primitives** as CLI commands (see [§12](#12-dead-code-disposition)): `specflow unlock`, `specflow locks`, `specflow rebuild-index`.

---

## 6. Documentation restructure

### Archive plan

Move `docs/phases/P0-*.md` through `docs/phases/P8-*.md` to `docs/.archive/phases/` with a one-line README explaining their historical nature:

> Historical phase-build docs from P0–P8. Preserved for design rationale and maintainer reference. Not user-facing.

Rationale: these docs were scaffolding used during bootstrap when `work/` did not yet track tasks. Now that the tracking infrastructure exists, phase docs are redundant with git history + current artifact state. Archiving (rather than deleting) preserves greppability.

### Target `docs/` structure

```
docs/
├── getting-started.md        (new; tutorial, written post-rename)
├── lifecycle.md              (new; flowchart + tiered command table)
├── commands.md               (new; interface spec per featured skill — see §4)
├── authoring-a-pack.md       (new; BYOC guide)
├── architecture.md           (existing; trim to maintainer essentials)
├── decisions.md              (existing; keep as design history)
├── skill-standards.md        (existing; keep)
└── .archive/
    └── phases/               (old P0–P8 docs)
```

`README.md` in the repo root expands to a proper project README: one-paragraph what-is, install line, link to `docs/getting-started.md`, link to `docs/lifecycle.md`.

---

## 7. Change-audit pipeline

Previously document-changes and impact existed as separate unrelated commands. They should be composed as a pipeline with a vetting mechanism so re-runs don't re-process already-reviewed changes.

### Pipeline

```
git commit
    │
    ▼
/specflow-document-changes
    │  scans git since anchor (baseline tag / commit SHA / date)
    │  emits DEC-{n} at _specflow/specs/decisions/
    │  each DEC has review_status: unreviewed
    ▼
/specflow-change-impact-review
    │  reads DEC where review_status == unreviewed
    │  for each DEC:
    │    - compute blast radius via specflow change-impact (programmatic)
    │    - launch subagent: "did this change preserve intent? any contradictions?"
    │    - write findings as CHL linked to DEC
    │    - flip DEC.review_status → reviewed | flagged
    ▼
results visible in CHL artifacts; user addresses flagged ones
```

### The `review_status` field

Standard on any artifact that is the *output* of a review process: DEC, CHL, AUD.

Values:
- `open` / `unreviewed` — not yet processed
- `reviewed` — processed with no concerns raised
- `flagged` — processed and concerns raised (requires user action)
- `addressed` — concerns resolved via linked mitigation (commit, STORY, DEC)
- `accepted` — concerns reviewed by user and accepted with rationale (stored in artifact body)
- `stale` — target of the finding changed materially after review (auto-flagged for re-review)

Schema addition required in `templates/schemas/decision.yaml`, `templates/schemas/challenge.yaml` (new), and `templates/schemas/audit.yaml` (new).

### Per-commit cost: bounded by blast radius

Scoping fix for the per-commit dimension of the N×M problem. Every commit previously implied re-checking all artifacts (O(changes × artifacts)); scoping by blast radius bounds per-commit work to the impact cone of each unreviewed DEC.

`/specflow-change-impact-review` uses `specflow change-impact` output to identify the blast radius of *each* unreviewed DEC. Subagent review is scoped to that cone, not the whole project. Full project-audit remains a separate, less-frequent operation ([§8](#8-project-audit-design)).

**Per-provider dimension NOT addressed here.** Shipping CI workflows per provider (GitHub Actions × GitLab CI × Jenkins × …) is a different N×M axis and remains open until the adapter framework lands ([§11](#11-adapter-framework)). Claiming "N×M solved" based on this section alone would overreach.

---

## 8. Project-audit design

`/specflow-project-audit` is the periodic full-project health review. It is conversational on scope and depth, and it composes subagents to stay tractable.

### Conversational scope selection

```
User: /specflow-project-audit

LLM: I see 47 artifacts across 5 types and 1 installed standard pack (iso26262-demo).
     Scope?
       a) Internal coherence only
       b) Against iso26262-demo
       c) Both (a) + (b)
       d) Full: above + adversarial lenses

     Depth?
       1) Quick      (~2 min, deterministic-heavy, sampled LLM)
       2) Detailed   (~10 min, LLM per artifact type + cross-cutting)
       3) Exhaustive (~30 min, per-artifact + full lens fan-out)

     Estimated token spend at depth 2: ~$3.20
     Confirm?
```

No `--compliance` flag. Standards auto-detected from `.specflow/standards/*.yaml`.

### Chunking strategy

Three parallel fan-out axes:

| Axis | Subagent allocation | What each checks |
|---|---|---|
| **Horizontal** (per artifact type) | 1 per type | "Are all REQs internally consistent? Contradictions?" "Do all ARCHs trace to REQs?" Per-type invariants. |
| **Vertical** (per V-model thread) | 1 per top-level REQ | Follow REQ→ARCH→DDD→STORY→tests as a coherent slice; check thread-level coherence. |
| **Cross-cutting** (per concern) | 1 each | Consistency, completeness, baseline-drift, standards-coverage, NFR-coverage, test-coverage. |

### Token-budget controls

- **Sample mode** (default at Quick depth): 20% of STORYs + all REQs + all ARCHs.
- **Baseline anchor**: diff against `.specflow/baselines/latest.yaml` to shrink scope.
- **Dedup preflight**: feed deduplicated artifact set so redundant work doesn't double-audit.
- **Fingerprint cache**: reuse subagent findings if the target's fingerprint hasn't changed since last audit. Stored at `.specflow/audits/.cache/{fingerprint}.md`.
- **Upfront spend estimate**: skill announces expected token cost before launching subagents; user must confirm.

### Outputs

- `.specflow/audits/{timestamp}/report.md` — top-level summary
- `.specflow/audits/{timestamp}/subagent-*.md` — per-lens/per-chunk findings
- `_specflow/specs/audits/AUD-{timestamp}.md` — audit artifact (new type), `review_status: open`
- CHL artifacts for specific findings (created on severity ≥ warn)

---

## 9. Adversarial review: challenge lenses

Adversarial passes are the biggest quality lever the framework currently lacks. Ship as lenses invoked inside `/specflow-artifact-review` and `/specflow-project-audit --full`. Each lens runs as its own subagent in parallel; findings aggregate as CHL artifacts.

Document all lenses now; implement progressively. Starter set (for first implementation): devil's-advocate, premortem, assumption-surfacing, red/blue team.

### Full lens catalog

1. **Devil's advocate** — Assume the artifact is wrong. Find evidence that the requirement, design, or story is mistaken, misguided, or unnecessary.

2. **Premortem** — Fast-forward six months: this artifact's implementation failed. What caused it? Enumerate plausible failure modes and their precursors.

3. **Red team / blue team** — Attacker vs. defender. Especially valuable on security-adjacent REQs and on ARCHs with trust boundaries. Red identifies exploits; blue identifies defenses; both findings persist.

4. **Stress-scale (×100)** — What breaks at 100× the stated scale — data volume, users, request rate, cost? Surface both hard limits (throughput, latency budgets) and soft limits (operational burden, on-call load).

5. **Assumption surfacing** — Enumerate every implicit assumption the artifact rests on. For each, attack it: what if it's false? What if it changes mid-project?

6. **Dependency shock** — For each external dependency (library, API, team, vendor): what if it disappears, changes terms, degrades in performance, or gets deprecated?

7. **Reversal** — What if we did the opposite? Sometimes reveals that the "obvious" direction is a bias rather than a reasoned choice.

8. **Five-whys** — Recursively ask "why" of each requirement's rationale. Usually exposes either a deeper root cause or a specious justification.

9. **Outside view (base-rate reasoning)** — Ignore project-specific details. How often do projects of this class succeed? What's the reference-class failure rate? Does this project's plan reflect that?

10. **Worst-case user** — Who abuses this feature? Who misunderstands it? Who uses it in a way we didn't anticipate? Especially valuable on public APIs and user-facing features.

11. **Regulator / auditor lens** — What would a compliance auditor flag? What questions would they ask for which we don't have a documented answer?

12. **Temporal drift** — Is what's true today going to be true in 2 years? 5 years? What temporal assumptions are we baking in?

13. **Composition** — What happens when multiple features interact? Race conditions, conflicting invariants, emergent behaviors between independently-specified artifacts.

14. **Inversion (Munger)** — What would *guarantee* failure? Identify the failure patterns, then check whether the design avoids them.

15. **Competitor framing** — How would [competitor X] solve this? What would they do differently? Often surfaces trade-offs the current design doesn't even acknowledge.

16. **Cost-scaling** — At 10× usage, is cost linear? Sublinear? Superlinear? Where are the cost nonlinearities, and are we aware of them?

### Lens selection UX

`/specflow-artifact-review` presents a checklist after scope resolution:

```
Target: ARCH-003, DDD-005, DDD-006, STORY-012..018
Apply which lenses?
  [x] devil's-advocate    [x] red/blue team      [ ] premortem
  [ ] stress-scale ×100   [x] assumption-surface [ ] dependency shock
  [ ] reversal            [ ] five-whys          [ ] outside view
  [ ] worst-case user     [ ] regulator          [ ] temporal drift
  [ ] composition         [ ] inversion          [ ] competitor
  [ ] cost-scaling

Estimated spend: $1.80 (3 lenses × 7 artifacts)
Confirm?
```

### CHL lifecycle

Each lens emits one or more CHL artifacts. Status flow:

```
open → addressed (linked to mitigation)
     ↓
     → accepted (user decision + rationale)
     ↓
     → stale (target fingerprint changed; re-review recommended)
```

Without this lifecycle, findings accumulate forever. With it, each CHL has a clear terminal state.

---

## 10. Compliance rework — BYOC

Today's claim "Bring-Your-Own-Standard" is undermined by a single demo pack whose clauses are explicit stubs. Reframe as honestly user-contributed.

### Changes

1. **Add `/specflow-pack-author` skill** ([§4](#4-featured-skill-interface-specs)). LLM-assisted pack authoring from PDF/URL/text. Lowers the effort to create a real pack from days to minutes.
2. **Relabel the ISO 26262 pack.** Rename `src/specflow/packs/iso26262/` → `src/specflow/packs/iso26262-demo/` with an honest 2-line README:
   > 5 stub clauses from ISO 26262, for framework testing only. Not a compliance pack. Use `/specflow-pack-author` to build your own.
3. **Write `docs/authoring-a-pack.md`** — manual path for users who don't want LLM assistance.
4. **Drop `/specflow-compliance` skill.** Fold into `/specflow-project-audit` as a scope choice (auto-detected from `.specflow/standards/`).
5. **Scope the BYOS principle in `docs/plan.md`** from "PDF ingestion" (the never-shipped parser) to "LLM-assisted pack authoring + manual YAML path."

### What stays

- The pack-install mechanism (`lib/scaffold.py:92-168`) — works, proven, no changes needed.
- The standards-loading code (`lib/standards.py:19-58`) — correct as-is.
- Runtime artifact-type registration (`lib/artifacts.py:148-156`) — correct as-is.

The infrastructure is right. The content was the lie.

---

## 11. Adapter framework

SpecFlow currently translates between its internal model and external systems in three places, each implemented as a hardcoded one-off:

- **CI/CD**: one hardcoded GitHub Actions template (`.github/workflows/specflow.yml`). No provider dispatch.
- **Exchange formats**: hardcoded `reqif` import/export, `if sub == "reqif"` branch style. No adapter contract.
- **Standards ingestion**: never shipped. P6 promised PDF parsing; the replacement is LLM-assisted pack authoring ([§10](#10-compliance-rework--byoc)), not a parser.

All three axes are N×M — every SpecFlow operation × every external system = one bespoke integration. This is the structural reason CI coverage is frozen at one provider and pack authoring never shipped. The earlier draft of this section proposed writing more hardcoded templates (PR bot, release gate, scheduled audit), which perpetuates the problem. Fix the architecture instead.

**Unify behind a single adapter framework.** Three axes, one shared interface, config-driven dispatch. Turns N×M into N+M.

### Config shape

```yaml
# .specflow/adapters.yaml

ci:
  provider: github-actions           # or gitlab-ci, bitbucket, jenkins, ...
  operations:                        # what to generate workflows for
    - artifact-lint
    - change-impact
    - project-audit
  release_gate:
    severity: error

exchange:
  - name: reqif
    provider: reqif                  # ships built-in
    direction: bidirectional
  # jira, linear, github-issues — not shipped; community territory

standards:
  - name: my-iso26262
    source: ./my-annotated-26262.pdf
    provider: pdf                    # adapter used internally by /specflow-pack-author
```

### Adapter interface

`lib/adapters/base.py`:

```python
class Adapter:
    name: str
    supported_operations: set[str]      # declares what this adapter does

    def generate_ci_workflow(self, ops: list[str]) -> dict[Path, str]: ...
    def import_artifacts(self, source: Path) -> list[Artifact]: ...
    def export_artifacts(self, arts: list[Artifact], dest: Path) -> None: ...
    def ingest_standard(self, source: Path) -> StandardsPack: ...
```

Each concrete adapter in `lib/adapters/<provider>.py` implements only the methods it supports; `supported_operations` declares the surface. Framework dispatches by config; no hardcoded provider branching in command code.

### CLI changes

- `specflow ci generate` — reads `.specflow/adapters.yaml`, picks adapter, writes workflow files. Replaces the hand-maintained `.github/workflows/specflow.yml` with generated output.
- `specflow import --adapter reqif path.reqif` — adapter explicit, replacing today's per-format subcommand style.
- `specflow export --adapter reqif out.reqif` — same.
- `specflow hook install` — asks the CI adapter for the appropriate hook script (Bash or PowerShell), closing the Windows shell-wrapper gap ([§1](#1-vision-vs-reality-gap)).

### Cross-cutting wins

- **Cross-platform gap** ([§1](#1-vision-vs-reality-gap)) becomes "write a PowerShell adapter" instead of "add `.ps1` in parallel with every `.sh`." Framework doesn't care about shell; each adapter picks its own.
- **Pack authoring** ([§10](#10-compliance-rework--byoc)) uses the standards-ingestion axis of the same framework rather than being a separate mechanism.
- **ReqIF positioning** changes from "flagship interchange format" to "one of several exchange adapters, shipped as the reference implementation."
- **Release-gate, PR bot, strict pre-commit hook** — the three operations from the pre-rework draft — are preserved, but they ship as output of the GitHub Actions adapter, not as hand-written templates.

### Launch minimum (ship this at public release)

- `lib/adapters/base.py` — adapter interface
- `lib/adapters/github_actions.py` — generates CI workflows for declared operations (artifact-lint, change-impact, project-audit, release-gate)
- `lib/adapters/reqif.py` — bidirectional exchange (ports existing P7 code behind the interface)
- `docs/authoring-an-adapter.md` — covers all three axes with a worked example
- `specflow ci generate` CLI
- `specflow import/export --adapter <name>` CLI

### Explicitly do NOT ship, and do NOT promise as "coming soon"

- GitLab CI / Bitbucket Pipelines / Jenkins adapters
- Jira / Linear / GitHub Issues / Azure DevOps exchange adapters
- Azure DevOps work-item / OSLC adapters
- PowerShell hook adapter for Windows
- PDF standards-ingestion adapter (replaced by LLM-assisted `/specflow-pack-author`)
- RBAC doctor / scheduled-audit / compliance-dashboard workflows

**Why no roadmap promises.** Open-source "upcoming features" lists rot; they signal abandonment and set expectations that silently go unmet. The existence of the adapter framework is the invitation for contributions. When users ask "does SpecFlow support GitLab CI?", the honest answer is: "The framework is there; one adapter ships; PRs welcome." No timeline, no roadmap.

If nobody contributes a given adapter, that's signal the coverage isn't needed. If many do, the ecosystem grows organically. Either outcome is healthier than a promised-but-unshipped roadmap.

### Positioning for public launch

Three competing spec-management tools ship hardcoded GitHub Actions workflows. None ships a pluggable adapter model. The adapter framework is the differentiator — especially for enterprise (who need GitLab / Jenkins / Bitbucket more than startups do). Public launch ships the framework + one working provider per axis; the framework is the architectural commitment, the provider is the proof point.

---

## 12. Dead-code disposition

`specflow detect dead-code` flagged 19 functions in `src/specflow/lib/`. Each was verified via grep across `src/`; the detector is **accurate** — these are all genuinely unreferenced. Disposition per symbol:

| Function | File:line | Disposition | Rationale |
|---|---|---|---|
| `get_stories_by_status` | `artifacts.py:351` | **Delete** | Specialized filter never wired up. |
| `rebuild_index` | `artifacts.py:588` | **Expose as CLI** | Legitimate recovery tool for stale `_index.yaml`. Add `specflow rebuild-index`. |
| `persist_edge_cases` | `challenge.py:21` | **Delete** | Referenced by specflow-verify SKILL.md but never actually called. challenge.py is likely dead module; delete both functions below. |
| `create_decision_artifact` | `challenge.py:65` | **Delete** | DEC creation uses `specflow create dec`. Redundant. |
| `update_execution_state` | `config.py:93` | **Delete** | Shadowed by `executor.py:load_execution_state`. |
| `read_execution_state` | `config.py:100` | **Delete** | Duplicate of above. |
| `run_dedup` | `dedup.py:241` | **Delete** | `check.py:77` has private `_run_dedup` and imports only `find_duplicates` + `write_candidates_file`. Orphaned. |
| `load_execution_state` | `executor.py:158` | **Keep; add to `__all__`** | Used internally; mark as intentional export. |
| `split_artifact` | `impact.py:347` | **Expose as CLI** | Real feature. Add `specflow split <id>`. |
| `merge_artifact` | `impact.py:416` | **Expose as CLI** | Paired with split. Add `specflow merge <id1> <id2>`. |
| `break_stale_lock` | `locks.py:94` | **Expose as CLI** | Recovery primitive. Add `specflow unlock <id>`. |
| `list_locks` | `locks.py:118` | **Expose as CLI** | Debug aid. Add `specflow locks`. |
| `check_gpg_signature` | `rbac.py:161` | **Wire into hook** | P7 RBAC feature never called. Wire into `hook pre-commit` or delete. |
| `load_schema_for_type` | `validation.py:39` (→ `lint.py:39`) | **Delete** | Thin wrapper; callers use `load_schemas()` directly. |
| `validate_status_transition` | `validation.py:133` (→ `lint.py:133`) | **Keep internal** | Rename to `_validate_status_transition` (underscore prefix). |
| `recompute_fingerprint` | `validation.py:201` (→ `lint.py:201`) | **Keep; add to `__all__`** | Used by `fingerprint-refresh` flow. Public API. |
| `load_checklist` | `validation.py:240` (→ `lint.py:240`) | **Delete; inline** | Trivial helper used once internally. |
| `discover_checklists` | `validation.py:253` (→ `lint.py:253`) | **Keep; add to `__all__`** | Public API for checklist assembly. |
| `run_automated_checklist` | `validation.py:269` (→ `lint.py:269`) | **Keep; add to `__all__`** | Zero-token checklist runner; core of review workflow. |

**Summary:** 9 deletions, 5 CLI-expose opportunities, 4 `__all__` additions, 1 wire-or-delete call (`check_gpg_signature`).

Net: ~40% reduction in flagged symbols after deletions; the rest become intentionally exported or exposed as new CLI commands.

---

## 13. Revised next-steps list

Reorganized into three milestones. The key reshuffle from the pre-rework draft: CI/CD and exchange work are merged into the adapter framework (M2) rather than shipped as more hardcoded templates; compliance rework depends on the adapter framework so it moves to M2; thin-skill wrappers and detect-folding are absorbed into the M1 rename/review work rather than standing alone.

### Milestone 1 — Clarity + Quality

1. **Audit and rewrite the four existing SKILL.md prompts** (`specflow-discover`, `specflow-plan`, `specflow-execute`, the renamed `specflow-artifact-review`). The reasoning layer has never been reviewed; this is load-bearing for everything downstream.

2. **Ship the command rename + thin-skill wrappers for all Tier 2/3 CLI commands** ([§3](#3-command-surface-rework)). Single coordinated pass: CLI, skills, Python filenames. Each thin skill is ~10–20 lines under the `/cmd [optional message]` pattern.

3. **Archive `docs/phases/` and restructure `docs/`** ([§6](#6-documentation-restructure)). New docs: `lifecycle.md`, `commands.md`, `authoring-a-pack.md`, `authoring-an-adapter.md`. Populate `README.md`. Defer `getting-started.md` tutorial until M2 lands (avoid writing a tutorial for an API still in flight).

4. **Ship `/specflow-artifact-review` with tiered depth + adversarial lens fan-out.** Four starter lenses: devil's-advocate, premortem, assumption-surfacing, red/blue team. CHL artifact type with full lifecycle (`open/addressed/accepted/stale`). Subagent-based parallel execution. Fold `/specflow-detect` into this skill (hygiene runs silently inside review; CLI remains for CI).

5. **Ship the change-audit pipeline** ([§7](#7-change-audit-pipeline)). `review_status` field on DEC/CHL/AUD schemas. `/specflow-change-impact-review` composes `document-changes` preflight + LLM review. Idempotent re-runs.

### Milestone 2 — Adapter framework + cleanup

6. **Build the unified adapter framework** ([§11](#11-adapter-framework)). Ship with GitHub Actions + ReqIF adapters. Document the adapter interface in `docs/authoring-an-adapter.md`. No "coming soon" roadmap for other providers. This is the public-launch architectural commitment.

7. **Expose recovery primitives as CLI + dead-code cleanup** ([§12](#12-dead-code-disposition)). Add `specflow unlock`, `specflow locks`, `specflow rebuild-index`, `specflow split`, `specflow merge`. Delete 9 genuinely-unused functions; add `__all__` markers to 4 intentional exports. Ordered after the rename (item 2) to avoid conflicting refactors.

8. **Compliance rework — BYOC** ([§10](#10-compliance-rework--byoc)). Ship `/specflow-pack-author` (uses the standards-ingestion axis of the adapter framework, so depends on item 6). Relabel `iso26262` → `iso26262-demo`. Write `docs/authoring-a-pack.md`.

### Milestone 3 — Depth + scale

9. **Add deterministic analytical passes to the V-model.** Conflict detection across REQs (contradictions, not just duplicates); non-functional taxonomy as a first-class REQ field; coverage-completeness check (REQ→STORY→test of all three levels); story-too-big warnings. Feeds directly into the quality/review layer.

10. **Ship `/specflow-project-audit`** ([§8](#8-project-audit-design)). Horizontal + vertical + cross-cutting chunking; conversational scope/depth; token-budget controls; fingerprint-keyed cache. Absorbs the dropped `/specflow-compliance` as a scope choice.

11. **Install UX** (public-launch prerequisite). One-line `uv tool install` path; `README.md` install section; publish package metadata; write `docs/getting-started.md` tutorial now that the API is stable.

### Deferred — explicit non-scope for public launch

No "coming soon" in public docs. These are possibilities the adapter framework enables, not commitments.

- Additional CI adapters (GitLab, Bitbucket, Jenkins) — community contribution territory.
- Additional exchange adapters (Jira, Linear, GitHub Issues, Azure DevOps, OSLC) — same.
- PowerShell hook adapter for Windows — same.
- Enterprise CI features: scheduled audit workflow, RBAC doctor, compliance dashboard HTML.
- Defect-tracker sync (from `project_post_p7_expansion_ideas.md`) — framework could host this as a new axis, not at launch.
- ReqIF `sync` (third verb alongside import/export) and DOORS/Polarion tool-specific fidelity.

### Cadence and release shape

- **M1 = SpecFlow v0.X "clarity."** Landable in a few focused passes; delivers the quality/review layer.
- **M2 = v0.Y "extensible."** Ships the adapter framework. This is the public-launch readiness milestone.
- **M3 = v1.0 "complete."** Post-launch depth. Public watches this land in master.

Public launch lands between M2 and M3. Launching earlier (without adapter framework) means shipping a tool whose only CI story is a hand-maintained GitHub Actions YAML and whose only exchange format is hardcoded. Launching later (after M3) delays hitting the market without changing the differentiator.

---

## Appendix A — old-to-new name map

One-stop reference for the rename. Use this to find-and-replace in any local checkout or tooling.

### Top-level CLI

```
specflow validate           → specflow artifact-lint
specflow check              → specflow checklist-run
specflow verify             → specflow artifact-review
specflow audit              → specflow project-audit
specflow compliance         → (removed — use specflow project-audit)
specflow impact             → specflow change-impact
specflow tweak              → specflow fingerprint-refresh
specflow sequence           → specflow renumber-drafts
```

### Skills

```
/specflow-validate          → (removed — use /specflow-artifact-review)
/specflow-check             → (removed — use /specflow-artifact-review)
/specflow-verify            → /specflow-artifact-review
/specflow-compliance        → (removed — use /specflow-project-audit)
/specflow-detect            → (removed — folded into review + audit)
```

### Python filenames

```
lib/validation.py           → lib/lint.py
commands/validate.py        → commands/artifact_lint.py
commands/verify.py          → commands/artifact_review.py
commands/check.py           → commands/checklist_run.py
commands/impact.py          → commands/change_impact.py
commands/tweak.py           → commands/fingerprint_refresh.py
commands/sequence.py        → commands/renumber_drafts.py
.claude/skills/specflow-verify/
                            → .claude/skills/specflow-artifact-review/
```

### Schema / field additions

```
DEC schema: + review_status field (unreviewed|reviewed|flagged)
New schema: CHL (challenge) artifact
New schema: AUD (audit) artifact
REQ schema: + non_functional_category field (optional, first-class)
```

---

**End of retrospective.**

This document is a snapshot at `master @ 2350afb`. Facts (file paths, dead-code list, pack contents) should be re-verified before acting on specific items, since the codebase will have moved by the time any of this is implemented.
