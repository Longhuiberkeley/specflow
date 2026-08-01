# SpecFlow CLI Reference

> **This is the CLI reference.** For the conversational skill interface (`/specflow-*`), see [commands.md](commands.md).

Reference for all `specflow` CLI commands. These are the deterministic backend that slash commands compose under the hood. Most users interact with SpecFlow via `/specflow-*` skills in their AI assistant -- this reference is for power users, CI pipelines, and automation.

For the slash command surface, see [commands.md](commands.md). For the lifecycle overview, see [lifecycle.md](lifecycle.md).

---

## Discover Phase

### `specflow init`

Scaffold a SpecFlow project in the current directory.

```bash
specflow init [--preset PRESET] [--no-ci]
```

| Flag | Purpose |
|------|---------|
| `--preset` | Industry pack preset (e.g., `iso26262-demo`, `adoption` for existing codebases) |
| `--no-ci` | Skip CI workflow installation (CI workflow is installed by default) |

### `specflow refresh`

Update the copied skills, agent-context block, and templates in this repo to match the installed SpecFlow version — without a full re-init. Run this after upgrading SpecFlow (`uv tool install --force git+https://github.com/Longhuiberkeley/specflow`) so new routing triggers, lifecycle fixes, and reference docs land in `.claude/skills/` (and the other platform skill dirs). It is the only way installed skills stay current after an upgrade. (SpecFlow is distributed from Git only — not on PyPI — so install and upgrade always use the Git source.)

```bash
specflow refresh [--platform <code>]
```

| Flag | Purpose |
|------|---------|
| `--platform` | Target a specific platform's skill dir (e.g., `opencode`, `codex`). Defaults to the detected/installed platform. |
| `--all-platforms` | Refresh skills for every detected AI-host platform dir, not just one |

### `specflow status`

Show the project dashboard — current phase, artifact counts by status, flagged issues.

```bash
specflow status
```

### `specflow brief`

One-call recall digest for resuming any session: project phase, inventory by category/status, open suspect flags, the next executable wave, and recent `_specflow/` changes. Deterministic aggregation of existing data — the cheap way to reconstruct project state instead of scanning every `_index.yaml` by hand.

```bash
specflow brief [--since "7 days ago"]
```

| Flag | Purpose |
|------|---------|
| `--since` | Window for the "recent changes" git log (default: `7 days ago`) |

### `specflow standards gaps`

List uncovered standard clauses — clauses in `.specflow/standards/` with no REQ linking to them via `complies_with`.

```bash
specflow standards gaps
```

Always exits 0 (informational, not blocking).

---

## Plan Phase

### `specflow create`

Create a new artifact.

```bash
specflow create --type TYPE --title TITLE [options]
specflow create --from-standard CLAUSE_ID
```

| Flag | Purpose |
|------|---------|
| `--type` | Artifact type (requirement, architecture, detailed-design, story, etc.). Case-insensitive; common abbreviations accepted (`dec`, `req`, `ddd`, `ut`, `it`, `qt`, `def`, …). On a miss, the error lists valid types and suggests the closest match. |
| `--title` | Artifact title (required unless `--from-standard`) |
| `--from-standard` | Create a draft REQ pre-populated from a standard clause ID |
| `--status` | Initial status. Omit to use the type's natural root status (e.g. `draft` for requirements, `open` for defects). Types with no single root (e.g. `experiment`, whose statuses are outcomes) require an explicit `--status` and list the allowed values if omitted. |
| `--priority` | Priority level |
| `--rationale` | Rationale text |
| `--tags` | Comma-separated tags |
| `--links` | Links as JSON array of `{"target","role"}` objects or comma-separated `TARGET:ROLE` pairs |
| `--body` | Markdown body content |
| `--force` | Skip duplicate-check prompt |
| `--nfr-category` | NFR category (performance, security, reliability, etc.) |

Run `specflow schema <type>` to see a type's settable fields, statuses, and transition map.

### `specflow update`

Update an artifact's frontmatter fields.

```bash
specflow update ARTIFACT_ID [--status STATUS] [--title TITLE] [--priority PRIORITY] [--tags TAGS]
specflow update ARTIFACT_ID --add-link TARGET:ROLE [--add-link TARGET:ROLE ...]
specflow update ARTIFACT_ID --remove-link TARGET
specflow update ARTIFACT_ID --links '[{"target": "ARCH-007", "role": "implements"}]'
```

| Flag | Purpose |
|------|---------|
| `--status` / `--title` / `--priority` / `--rationale` / `--tags` | Replace the corresponding field |
| `--links` | Replace the whole link list (JSON array or `TARGET:ROLE` pairs) |
| `--add-link` | Append one `TARGET:ROLE` link (repeatable; dedups on target+role). Nonexistent targets warn, never block. |
| `--remove-link` | Remove links by target (repeatable; idempotent) |
| `--output-files` | Replace declared output files (empty string removes) |
| `--thinking-techniques` | Append thinking-technique names (e.g. `premortem,devils_advocate`) |
| `--set KEY=VALUE` | Set an arbitrary frontmatter field (repeatable, JSON-aware) |

`--links` cannot be combined with `--add-link`/`--remove-link` (ambiguous). Malformed link input fails with an error and leaves the artifact untouched.

---

## Execute Phase

### `specflow go`

Execute approved stories in parallel waves.

```bash
specflow go [--dry-run] [--wave WAVE] [--timeout TIMEOUT]
```

| Flag | Purpose |
|------|---------|
| `--dry-run` | Show wave plan without executing |
| `--wave` | Execute only a specific wave number |
| `--timeout` | Per-story timeout in seconds (default: 600) |

### `specflow done`

Close the current phase and extract prevention patterns.

```bash
specflow done [--auto] [--no-auto] [--no-patterns]
```

| Flag | Purpose |
|------|---------|
| `--auto` | Auto-extract prevention patterns from implemented stories (default) |
| `--no-auto` | Show pattern summary without extracting |
| `--no-patterns` | Skip pattern extraction entirely |

### `specflow phase-set`

Record a phase transition — forward, or a REWIND (e.g. "go back to requirements", "rethink the architecture"). Accounting-only: it never blocks and never validates readiness (that's `phase-status`'s job). Keeps `specflow brief --next` honest after a reverse-lifecycle move. Leaving `executing` clears in-progress execution state.

```bash
specflow phase-set PHASE [--reason TEXT]
```

| Flag | Purpose |
|------|---------|
| `PHASE` | Target phase: `idle`, `discovering`, `specifying`, `planning`, `executing`, `verifying`, `complete` |
| `--reason` | Why the phase is being set (recorded in history) |

---

## Domain and Best Practices

### `specflow domain`

Get or set the project's domain (drives domain-aware checklists and review synthesis).

```bash
specflow domain set NAME [--tag TAG]...
specflow domain show
```

| Flag | Purpose |
|------|---------|
| `--tag` | Domain qualifier (repeatable, e.g., `--tag real-time --tag safety-critical`) |

### Best Practice Artifacts (BP)

Best practices are first-class SpecFlow artifacts (`BP-NNN`) stored in `_specflow/specs/best-practices/`. The agent generates them during discovery and planning — no external API calls needed.

```bash
specflow create --type best-practice --title "..." --status approved --body "## Practice\n...\n## Rationale\n...\n## Verification\n..."
```

BPs are traceable: `derives_from` → standards, `applies_to` → REQ/ARCH/DDD/STORY, `supersedes` → older BPs. See `approval-presentation.md` for how BPs integrate with the review workflow.

### `specflow patterns`

Inspect learned prevention patterns — rules extracted from artifact reviews with blocking/warning findings.

```bash
specflow patterns list
specflow patterns show PATTERN_ID
```

| Subcommand | Purpose |
|------------|---------|
| `list` | List all learned patterns with ID, severity, source, and check preview |
| `show` | Print a specific pattern's full YAML (e.g., `specflow patterns show PREV-001`) |

Patterns accumulate automatically during `artifact-review`. Configure learning via `config.yaml`:

```yaml
learning:
  max_patterns_per_session: 3          # max patterns created per review
  learnable_techniques:                 # which technique findings feed into learning
    - checklist-run
    - devils_advocate
    - premortem
```

---

## Introspection

Read-only commands for discovering what the engine knows — cheaper than re-reading `--help` or parsing `_index.yaml` by hand. Every command that rejects a bad token (subcommand, flag, type, status) also suggests the closest valid one.

### `specflow transitions`

Show the legal next statuses for an artifact — status transitions are type-specific, so never guess them.

```bash
specflow transitions ARTIFACT_ID
```

Prints the artifact's current type/status, its legal next states, and the full transition table for the type. The same hint is printed whenever `update --status` is rejected.

### `specflow list`

Query artifacts without hand-parsing `_index.yaml`.

```bash
specflow list [--type TYPE] [--status STATUS] [--tags TAGS] [--json]
```

| Flag | Purpose |
|------|---------|
| `--type` | Filter by artifact type (abbreviations accepted; unknown types error with the valid list) |
| `--status` | Filter by status |
| `--tags` | Comma-separated tags (any-overlap match) |
| `--json` | Machine-readable output: `[{id, type, status, title, path}, ...]` |

### `specflow schema`

Show a type's schema — the settable fields, the status transition map, and allowed link roles. Run this instead of probing `--set` keys by trial and error.

```bash
specflow schema TYPE
```

---

## Review Phase

### `specflow artifact-lint`

Run deterministic validation checks on artifacts. Zero tokens.

```bash
specflow artifact-lint [--type CHECK] [--fix] [--gate GATE] [--method {programmatic,llm}]
```

| Check Type | What it validates |
|------------|-------------------|
| `schema` | Required fields, ID format, status values |
| `links` | Link integrity, orphan detection, V-model pairs |
| `status` | Status lifecycle consistency |
| `ids` | ID uniqueness, format, dot-notation depth |
| `fingerprints` | Content fingerprint staleness |
| `acceptance` | REQs have acceptance criteria |
| `conflicts` | Cross-REQ constraint contradictions |
| `coverage` | REQ→STORY→test completeness |
| `story-size` | Story decomposition heuristics |
| `gate` | Phase-gate checklist validation |

### `specflow checklist-run`

Run context-specific review checklists on artifacts.

```bash
specflow checklist-run [ARTIFACT_ID] [--all] [--gate GATE] [--proactive] [--dedup]
```

### `specflow artifact-review`

Compose lint, checklist review, and thinking technique prompts.

```bash
specflow artifact-review [ARTIFACT_ID] [--all] [--depth {quick,normal,deep}] [--techniques TECHNIQUES] [--gate GATE]
```

| Flag | Purpose |
|------|---------|
| `--all` | Review all artifacts |
| `--depth` | `quick` (lint+checklist), `normal` (add agent-judged checks), `deep` (add thinking technique prompts) |
| `--techniques` | Comma-separated techniques for `--depth deep` |
| `--gate` | Phase-gate checklist |
| `--proactive` | Include proactive challenge items |

### `specflow project-audit`

Full-project health review — horizontal + vertical + cross-cutting checks.

```bash
specflow project-audit [--standard STANDARD] [--baseline BASELINE] [--quick] [--sample-pct PCT]
```

| Flag | Purpose |
|------|---------|
| `--standard` | Standard name for compliance check (auto-detects if omitted) |
| `--baseline` | Baseline for drift comparison (auto-detects latest if omitted) |
| `--quick` | Skip cross-cutting analysis (horizontal + vertical only) |
| `--sample-pct` | Sample percentage for STORYs (default: 100) |

### `specflow rtm`

Bidirectional requirements-traceability matrix: one row per REQ, with columns for linked ARCH, STORY, and verifying tests (UT/IT/QT). Gap markers flag empty columns per row; a footer lists orphan tests (tests with no REQ lineage).

```bash
specflow rtm [--req ID] [--format table|markdown|csv] [--gaps]
```

| Flag | Purpose |
|------|---------|
| `--req` | Filter to a single REQ ID |
| `--format` | `table` (default), `markdown`, or `csv` |
| `--gaps` | Only show rows with at least one empty column |

---

## Release Phase

### `specflow baseline`

Create and compare immutable baseline snapshots.

```bash
specflow baseline create TAG
specflow baseline diff BASELINE_A BASELINE_B
```

### `specflow document-changes`

Generate change records (DEC artifacts) from git history.

```bash
specflow document-changes --since GIT_REF
```

### `specflow change-impact`

Report and resolve suspect flags from change propagation.

```bash
specflow change-impact [ARTIFACT_ID] [--resolve ARTIFACT_ID]
```

### `specflow defect-from-suspect`

Materialize the suspect → DEF pipeline: when a suspect-flagged artifact genuinely no longer satisfies its upstream requirement, create a DEF with full traceability (`fails_to_meet` → REQ, `exposed_by` → the suspect artifact), registered in the index. Pair with `change-impact --resolve` once addressed.

```bash
specflow defect-from-suspect SUSPECT_ID --req REQ_ID [--severity LEVEL] [--impact-event PATH] [--title TITLE]
```

| Flag | Purpose |
|------|---------|
| `SUSPECT_ID` | The suspect-flagged artifact (e.g., `ARCH-001`) |
| `--req` | Upstream REQ whose change caused the suspect flag (required) |
| `--severity` | `low` \| `medium` \| `high` \| `critical` (default: `medium`) |
| `--impact-event` | Path to the impact-log YAML event (recorded in the DEF body) |
| `--title` | Override the auto-generated defect title |

---

## CI and Hooks

### `specflow ci generate`

Generate CI workflow files from `adapters.yaml` configuration.

```bash
specflow ci generate
```

### `specflow rbac check`

Resolve the current git author's team roles (from `.specflow/config.yaml`), and optionally check whether a status transition is authorized for those roles. Prints "RBAC not active (single-user mode)" when no team config exists. Nested under `rbac` so a future `rbac doctor` can share the namespace.

```bash
specflow rbac check [--email EMAIL] [--type TYPE --to-status STATUS]
```

| Flag | Purpose |
|------|---------|
| `--email` | Author email to resolve (default: git config `user.email`) |
| `--type` | Artifact type/ID to check (used with `--to-status`) |
| `--to-status` | Target status to check authorization for (used with `--type`) |

### `specflow hook install`

Install `.git/hooks/pre-commit` for pre-commit validation.

```bash
specflow hook install
```

### `specflow hook pre-commit`

Run the pre-commit check (called by the git hook).

```bash
specflow hook pre-commit
```

---

## Data Exchange

### `specflow import`

Import artifacts from external formats.

```bash
specflow import --adapter reqif FILE
```

### `specflow export`

Export artifacts to external formats.

```bash
specflow export --adapter reqif [--output FILE]
```

---

## Project Hygiene

### `specflow detect`

Project-hygiene scans.

```bash
specflow detect dead-code                                  # Report unreferenced functions/classes
specflow detect similarity                                 # Report near-identical function pairs
specflow detect orphan-code                                # Coverage % + unreferenced source files (globs honored)
specflow detect orphan-code --retro-link ARCH-003          # Adopt orphans into an ARCH's output_files (STORY/ARCH/DDD/REQ)
specflow detect stale-docs                                 # Docs citing superseded/cancelled/deprecated artifacts (warning, never blocks)
```

`output_files` on STORY/REQ/ARCH/DDD may be literal paths or glob patterns (`**/*.java`).
The orphan meter credits all four types and expands globs through `lib.files.expand_output_files`,
the same helper reconcile and source-drift use — so a package glob in any artifact's
`output_files` is honored uniformly. The command reports **coverage %** (referenced ÷ total)
and the **biggest un-adopted cluster** (the top-level directory with the most orphan files).

Orphan-code is also surfaced as a lens in `specflow project-audit` (full mode, not `--quick`): it distinguishes "source↔spec tracking not yet adopted" (info) from "files slipped through partial tracking" (warn).

### `specflow adopt status`

Adoption completeness, **derived from the graph** (no state file). Available with the `adoption` pack (`/specflow-init --preset adoption`).

```bash
specflow adopt status                # Project + per-boundary dashboard
specflow adopt status REQ-007         # Per-artifact completeness report
specflow adopt status ARCH-003
```

The **project view** shows coverage %, backfilled count by type, inference debt (artifacts whose rationale flags "inferred / not confirmed"), and a per-ARCH boundary dashboard (file count, depth skeleton/full, drift flag, parent REQ). The biggest un-adopted cluster is flagged.

The **per-artifact view** shows realization neighbors (arch realizes a REQ, DDD details an ARCH), acceptance-criteria count (for REQs), linked tests, provenance parsed from `tags` + `rationale`, depth, gaps (files under an ARCH's glob not covered by any child DDD; realizing ARCHs with no DDD), and post-adoption drift (from `.specflow/source-fingerprints.yaml`).

For large repos, the default strategy is **skeleton-first**: one ARCH per component across the whole project, then deepen (REQ/DDD/tests) for components `adopt status` flags as high-churn, thin, or unverified. See `src/specflow/packs/adoption/skills/specflow-adopt/` for the full protocol.

### `specflow renumber-drafts`

Renumber draft IDs to sequential integers.

```bash
specflow renumber-drafts [--dry-run]
```

### `specflow fingerprint-refresh`

Update content fingerprint without triggering suspect cascade.

```bash
specflow fingerprint-refresh TARGET [TARGET ...]
```

Targets are artifact IDs (preferred, like every other command) or file paths; both may be mixed and multiple targets may be given in one invocation. Each target reports its own result line; the exit code is non-zero only if *all* targets fail.

---

## Recovery

### `specflow unlock`

Break a stale lock on an artifact.

```bash
specflow unlock ARTIFACT_ID
```

### `specflow locks`

List all active artifact locks.

```bash
specflow locks
```

### `specflow rebuild-index`

Regenerate stale `_index.yaml` files.

```bash
specflow rebuild-index [--type TYPE]
```

### `specflow split`

Split an artifact into two.

```bash
specflow split SOURCE_ID NEW_ID [--reassign LINK_OWNER_ID]
```

### `specflow merge`

Merge two artifacts (source status becomes `merged_into`, links transfer to target).

```bash
specflow merge SOURCE_ID TARGET_ID
```
