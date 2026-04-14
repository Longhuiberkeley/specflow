# SpecFlow Command Reference

Interface spec for each Tier 1 skill. Source of record: [`retrospective.md`](../retrospective.md) §4.

> **Status note:** Some commands documented here (`/specflow-init`, `/specflow-project-audit`, `/specflow-document-changes`, `/specflow-change-impact-review`, `/specflow-release`, `/specflow-pack-author`) are documented-but-not-yet-shipped; they come from retrospective §4 as the target surface. See `_specflow/work/stories/` for delivery stories. The current CLI ships a subset (see `specflow --help`).

For a lifecycle overview and tier breakdown, see [lifecycle.md](lifecycle.md).

---

## /specflow-init

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

## /specflow-discover

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

## /specflow-plan

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

## /specflow-execute

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

## /specflow-artifact-review

**One-line:** LLM-driven quality review of one or more artifacts.

**Composes:** `artifact-lint` (deterministic) → `checklist-run` → LLM judgment → optional adversarial lenses.

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

## /specflow-project-audit

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

## /specflow-document-changes

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

## /specflow-change-impact-review

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

## /specflow-release

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

## /specflow-pack-author

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
