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
| `--preset` | Industry pack preset (e.g., `iso26262-demo`) |
| `--no-ci` | Skip CI workflow installation (CI workflow is installed by default) |

### `specflow status`

Show the project dashboard — current phase, artifact counts by status, flagged issues.

```bash
specflow status
```

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
| `--type` | Artifact type (requirement, architecture, detailed-design, story, etc.) |
| `--title` | Artifact title (required unless `--from-standard`) |
| `--from-standard` | Create a draft REQ pre-populated from a standard clause ID |
| `--status` | Initial status (default: `draft`) |
| `--priority` | Priority level |
| `--rationale` | Rationale text |
| `--tags` | Comma-separated tags |
| `--links` | Links as JSON array or `target:role` pairs |
| `--body` | Markdown body content |
| `--force` | Skip duplicate-check prompt |
| `--nfr-category` | NFR category (performance, security, reliability, etc.) |

### `specflow update`

Update an artifact's frontmatter fields.

```bash
specflow update ARTIFACT_ID [--status STATUS] [--title TITLE] [--priority PRIORITY] [--tags TAGS]
```

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

### `specflow handbook`

Manage the domain best-practice cache — the project's living process booklet.

```bash
specflow handbook generate [project|PHASE] [--domain DOMAIN] [--overwrite]
specflow handbook show [project|PHASE] [--domain DOMAIN]
specflow handbook path [project|PHASE] [--domain DOMAIN]
specflow handbook list
```

| Subcommand | Purpose |
|------------|---------|
| `generate` | Synthesize BPs via LLM and cache (one-time per domain+phase) |
| `show` | Print cached BPs as YAML |
| `path` | Print cache file path |
| `list` | List all cached BP files |

Two-level cache:
- **Project-level:** one file per domain, generated after `specflow domain set`
- **Phase-level:** one file per (domain, phase), auto-synthesized on first artifact review

Files are intentionally human-editable. Use `--overwrite` to regenerate from LLM.

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

Compose lint, checklist review, and LLM judgment.

```bash
specflow artifact-review [ARTIFACT_ID] [--all] [--depth {quick,normal,deep}] [--techniques TECHNIQUES] [--gate GATE] [--fast]
```

| Flag | Purpose |
|------|---------|
| `--all` | Review all artifacts |
| `--depth` | `quick` (lint+checklist), `normal` (add LLM judgment), `deep` (add thinking techniques) |
| `--techniques` | Comma-separated techniques for `--depth deep` |
| `--gate` | Phase-gate checklist |
| `--proactive` | Include proactive challenge items |
| `--fast` | Skip BP synthesis (use cached best practices only, no LLM calls for BP generation) |

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

---

## CI and Hooks

### `specflow ci generate`

Generate CI workflow files from `adapters.yaml` configuration.

```bash
specflow ci generate
```

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
specflow detect dead-code     # Report unreferenced functions/classes
specflow detect similarity    # Report near-identical function pairs
```

### `specflow renumber-drafts`

Renumber draft IDs to sequential integers.

```bash
specflow renumber-drafts [--dry-run]
```

### `specflow fingerprint-refresh`

Update content fingerprint without triggering suspect cascade.

```bash
specflow fingerprint-refresh FILEPATH
```

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
