# SpecFlow CLI Reference

> **This is the CLI reference.** For the conversational skill interface (`/specflow-*`), see [commands.md](commands.md).

Reference for all `specflow` CLI commands. These are the deterministic backend that slash commands compose under the hood. Most users interact with SpecFlow via `/specflow-*` skills in their AI assistant -- this reference is for power users, CI pipelines, and automation.

For the slash command surface, see [commands.md](commands.md). For the lifecycle overview, see [lifecycle.md](lifecycle.md).

---

## Discover Phase

### `specflow init`

Scaffold a SpecFlow project in the current directory.

```bash
specflow init [--platform PLATFORM] [--preset PRESET] [--with-types TYPES] [--no-ci] [--domain DOMAIN] [--domain-tags TAGS] [--force]
```

| Flag | Purpose |
|------|---------|
| `--platform` | AI platform code (e.g., `claude-code`, `cursor`, `windsurf`). Defaults to the detected platform. |
| `--preset` | Comma-separated packs to install (e.g., `autoresearch`, `ops`, `tldr-communication`, `adoption` for existing codebases, `iso26262-demo`) |
| `--with-types` | Comma-separated optional artifact types to enable (e.g., `hazard,risk,control`) |
| `--no-ci` | Skip CI workflow installation (CI workflow is installed by default) |
| `--domain` | Project domain (e.g., `embedded`, `api-service`, `web-app`, `quant`, `ml`) |
| `--domain-tags` | Comma-separated domain tags (e.g., `real-time,safety-critical`) |
| `--force` | Force a clean re-initialization (backs up existing config/state/schemas first) |

`init` also writes an empty `.specflow/findings-baseline.yaml`, so new projects start with the lint ratchet on (see [`specflow findings-baseline`](#specflow-findings-baseline)).

### `specflow refresh`

Update the copied skills, agent-context block, and templates in this repo to match the installed SpecFlow version — without a full re-init. Run this after upgrading SpecFlow (`uv tool install --force git+https://github.com/Longhuiberkeley/specflow`) so new routing triggers, lifecycle fixes, and reference docs land in `.claude/skills/` (and the other platform skill dirs). It is the only way installed skills stay current after an upgrade. (SpecFlow is distributed from Git only — not on PyPI — so install and upgrade always use the Git source.)

```bash
specflow refresh [--platform <code>] [--all-platforms] [--no-skills] [--no-context] [--schemas] [--checklists] [--packs] [--force] [--dry-run]
```

| Flag | Purpose |
|------|---------|
| `--platform` | Target a specific platform's skill dir (e.g., `opencode`, `codex`). Defaults to the detected/installed platform. |
| `--all-platforms` | Refresh skills for every detected AI-host platform dir, not just one |
| `--no-skills` | Skip the skill update |
| `--no-context` | Skip the agent-context re-injection into the instruction file |
| `--schemas` | Also update base schema files. Installs missing schemas; **preserves** schemas that have drifted from shipped defaults (prints which ones). |
| `--checklists` | Also update base checklist templates (writes missing, repairs unparseable; preserves changed unless `--force`) |
| `--packs` | Also refresh assets for the configured active packs |
| `--force` | Replace drifted generated schemas, checklists, and pack skills with shipped defaults instead of preserving them (applies to `--schemas`, `--checklists`, `--packs`). |
| `--dry-run` | Show what would change (new / identical / changed) without writing anything. |

`--schemas` is safe by default: a schema you (or prior tooling) edited is never silently overwritten — it is preserved with an actionable hint (`run specflow refresh --schemas --force to replace`). `--force` explicitly restores shipped defaults for drifted schemas. `brief` surfaces the same drift signal as a health nag.

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

`brief --next` appends an unreviewed-DEC blast-radius note when one or more human-authored ADRs have no review — reporting the change-impact downstream cone as a union (an artifact downstream of several DECs counts once), computed in a single discover pass. Auto-generated change records are excluded by `dec_kind: change_record` (with tags as a backward-compatible fallback), and the Recent decisions section shows ADRs only. Quiet projects stay quiet (fires only on presence).

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
| `--status` | Initial status. Omit to use the type's natural root status (e.g. `draft` for requirements, `open` for defects). Types with no single root (e.g. `experiment`, whose statuses are outcomes) require an explicit `--status` and list the allowed values if omitted. An explicit status that is **not** a creation-entry status (e.g. `approved`) is rejected unless `--sanctioned` records why the entry state is legitimate. |
| `--sanctioned` | Justification recorded as `sanctioned_justification` in frontmatter — required to create directly in a non-entry status (the creation-status gate: approval bypasses stay recorded, never silent). |
| `--priority` | Priority level |
| `--rationale` | Rationale text |
| `--tags` | Comma-separated tags |
| `--links` | Links as JSON array of `{"target","role"}` objects or comma-separated `TARGET:ROLE` pairs |
| `--add-link` | Append one `TARGET:ROLE` link (repeatable; dedups on target+role) — append-style parity with `update --add-link` |
| `--body` | Markdown body content |
| `--force` | Skip duplicate-check prompt |
| `--nfr-category` | NFR category — frozen vocabulary enforced at the create boundary: `functional`, `performance`, `security`, `reliability`, `usability`, `maintainability`, `scalability`, `compliance` (`functional` is the sanctioned bookkeeping value for functional REQs). The generic `update --set non_functional_category=...` path stays freeform; artifact-lint's `nfr-category` check is its typo net. |

Run `specflow schema <type>` to see a type's settable fields, statuses, and transition map.

### `specflow update`

Update an artifact's frontmatter fields.

```bash
specflow update ARTIFACT_ID [--status STATUS] [--title TITLE] [--priority PRIORITY] [--tags TAGS]
specflow update ARTIFACT_ID --body 'Markdown body…'        # replaces the whole body (stdin auto-read when piped)
specflow update ARTIFACT_ID --ac 'criteria…'               # replaces/inserts only the Acceptance Criteria section
specflow update ARTIFACT_ID --add-link TARGET:ROLE [--add-link TARGET:ROLE ...]
specflow update ARTIFACT_ID --remove-link TARGET
specflow update ARTIFACT_ID --links '[{"target": "ARCH-007", "role": "implements"}]'
```

| Flag | Purpose |
|------|---------|
| `--status` / `--title` / `--priority` / `--rationale` / `--tags` | Replace the corresponding field |
| `--body` | Replace the entire Markdown body (fingerprint is recomputed). Reads stdin when piped and `--body` is omitted — but only when no other field is updated in the same call; otherwise piped data is ignored with an advisory (the body is never replaced as a side effect). |
| `--ac` | Replace (or insert) the `## Acceptance Criteria` section only; all other sections are preserved and the fingerprint recomputes. REQ and STORY artifacts only. Matching is heading-anchored and fence-aware: prose mentions and fenced examples are never touched. Fails loudly on multiple AC headings (ambiguous target) and cannot be combined with `--body` / `--set body=`. |
| `--links` | Replace the whole link list (JSON array or `TARGET:ROLE` pairs) |
| `--add-link` | Append one `TARGET:ROLE` link (repeatable; dedups on target+role). Nonexistent targets warn, never block. |
| `--remove-link` | Remove links by target (repeatable; idempotent) |
| `--output-files` | Replace declared output files (empty string removes) |
| `--thinking-techniques` | Append thinking-technique names (e.g. `premortem,devils_advocate`) |
| `--set KEY=VALUE` | Set an arbitrary frontmatter field (repeatable, JSON-aware). Dotted `KEY.subkey=` merges into a declared nested-map field. |

`--links` cannot be combined with `--add-link`/`--remove-link` (ambiguous), and `--ac`, `--body`, and `--set body=` are pairwise exclusive (they all write the body). Malformed link input fails with an error and leaves the artifact untouched. A `--status` not in the type's `allowed_status` is rejected (with a did-you-mean hint); an artifact whose current status is itself invalid can be corrected to any legal status via `--status` (repair path — it is never locked out of the CLI). A dotted `--set` key whose head is not a declared nested-map field fails loudly; an unknown flat `--set` key that is a near-miss of a known field errors with a suggestion — except keys already present in the artifact's frontmatter, which are established custom fields and always pass through. Passing `--confidence` to `create` or `update` (no such flag exists) hints at `--set risk_profile.confidence=<value>` on DEC artifacts, where `risk_profile` is declared; advisory only.

### `specflow approve`

Move every artifact of one type from one status to the next in a single call — the bulk form of `update --status`, for the moment a reviewer says "approve all the draft REQs".

```bash
specflow approve --type REQ [--status draft] [--target-status approved] [--yes]
```

| Flag | Purpose |
|------|---------|
| `--type` | ID prefix or type name to approve (e.g. `REQ`, `STORY`, `requirement`); required |
| `--status` | Only move artifacts currently in this status (default: `draft`) |
| `--target-status` | Status to move them to (default: `approved`) |
| `--yes` | Skip the confirmation prompt (CI / scripted use) |

Approval is a human act: the command prints the full ID list and asks for one confirmation; skills never auto-invoke it inside a flow, and it never reads past approvals to size or skip the batch. The agent presents the exact `approve --type …` line (as `specflow brief` does, with the draft IDs and their impact) and runs it only on the user's go-ahead. The same transition legality as `update --status` applies, so an illegal target is rejected per artifact with the legal predecessor states (`Allowed from: …`) and a `specflow transitions <ID>` hint.

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

### `specflow phase-status`

Readiness view for the current phase: which gate-checklist items pass, which block, and what to run next. Read-only — `phase-set` records moves, `phase-status` reports readiness.

```bash
specflow phase-status
```

### `specflow cascade-status`

Cascade a STORY's status to its linked ARCH/DDD (and, with `--include-req`, the REQ) when every sibling has reached the same status; writes only legal transitions and fails loudly otherwise. `--dry-run` previews the writes.

```bash
specflow cascade-status STORY-001 [--include-req] [--dry-run]
```

### `specflow reconcile`

Promote `approved` STORYs that already have implementation evidence (declared output files on disk or git commits naming the story) to `implemented`; `--no-cascade` skips the follow-on ARCH/DDD cascade, `--dry-run` previews.

```bash
specflow reconcile [--dry-run] [--no-cascade]
```

### `specflow generate-tests`

Create UT/IT/QT stub artifacts for implemented spec artifacts that lack their V-model pair; `--from ID` targets one artifact, `--dry-run` lists what would be created.

```bash
specflow generate-tests [--from ID] [--dry-run]
```

### `specflow verify`

Run an artifact's declared `verify_command` and **record** the result as verification evidence — turns the `verified` status from an assertion into machine-checkable proof. An evidence recorder, not a gate: a failing run is recorded truthfully (`verify_run_exit_code`) and **never blocks** a commit, transition, or release (accounting, not policing).

```bash
specflow verify ID
specflow verify --all
specflow verify --type TYPE
specflow verify ID --dry-run
specflow verify ID --evidence-file
specflow verify --all --seed-prev
```

| Flag | Purpose |
|------|---------|
| `ID` | Run one artifact's declared `verify_command`; records `verify_run_at`, `verify_run_exit_code`, `verify_run_out_hash` |
| `--all` | Run every declared verification contract across the project in one pass |
| `--type` | Scope to one V-model level (`unit-test`, `integration-test`, `qualification-test`, `story`) |
| `--dry-run` | Print the resolved command(s) and target artifact(s) without executing or recording |
| `--evidence-file` | Boolean flag (no path). Resolve the first file matching the artifact's `verify_evidence` glob(s) and record its hash (`verify_run_evidence_hash`) and mtime (`verify_run_evidence_mtime`). Command stdout+stderr are summarized into `verify_run_out_hash` regardless of this flag |
| `--timeout` | Per-command timeout in seconds (default: 600) |
| `--seed-prev` | Opt in to creating a PREV prevention pattern for each divergent verification result; accounting-only and never blocks |

Artifacts declare the contract via frontmatter: `verify_command` (the shell command that proves it works), `verify_exit_code` (expected pass code, default `0`), and `verify_evidence` (note on what the output proves). `specflow verify` records the run side: `verify_run_at`, `verify_run_exit_code`, `verify_run_out_hash` (and, with `--evidence-file`, `verify_run_evidence_hash` + `verify_run_evidence_mtime` for the first matched evidence file). A divergence between `verify_exit_code` and `verify_run_exit_code` surfaces as an advisory in `specflow brief --next` and an accounting warning in `specflow project-audit` — never as an error. Artifacts with no `verify_command` are unaffected. See the specflow-execute skill's `verification-contracts.md` reference for field semantics and the never-blocking invariant.

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
specflow create --type best-practice --title "..." --status approved --sanctioned "Guidance artifact, not a deliverable — surfaced in the reply for user veto/edit" --body "## Practice\n...\n## Rationale\n...\n## Verification\n..."
```

Non-entry statuses at create require `--sanctioned "<justification>"` (recorded as `sanctioned_justification` in frontmatter); see the [creation-status gate](#specflow-create).

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

### `specflow practices`

Manage the bundled best-practice (BP) seeds and their provenance: `seed` lists or creates the bundled generic/domain practices (no API key), `validate` checks BP anatomy, metadata, and supersession lineage, and `migrate` stamps provenance on legacy BP artifacts. The old `handbook generate` form is a deprecated alias for `practices seed`.

```bash
specflow practices seed [--create] [--verbose]     # title index by default; --create writes draft BPs
specflow practices validate
specflow practices migrate [--dry-run]
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

### `specflow trace`

Walk one artifact's lineage in both directions: upstream sources and standards (what it derives from, implements, or complies with) and downstream implementation and verification (what refines, implements, or verifies it), plus the chain depth. The answer to "what supersedes / implements / verifies X?" — inverse roles are queried here, never authored.

```bash
specflow trace ARTIFACT_ID
```

`specflow brief` is the project-wide digest; `trace` is the per-ID follow-up it points at. Memory recall in the agent context is built on the pair.

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

### `specflow risk-tier`

Print the computed minimum risk tier for a change set. READ-ONLY — computes the tier from the change set's intrinsic properties and prints it; **gates nothing** (accounting, not policing). The tier is a floor: escalate freely, downgrade only with a recorded justification on the DEC's `risk_profile`.

```bash
specflow risk-tier ID [ID ...]
```

The deterministic floor is Tier 2 when the change is **irreversible** (a status moving to `verified`/`released`, a `supersedes` link, a deletion, a `destructive`/`data-migration` tag, or — when run via `document-changes` — a release/baseline commit) **or** the downstream blast-radius cone is large (≥ 8 artifacts); Tier 0 only when the change is reversible, small, and touches zero downstream artifacts; otherwise Tier 1. Unclassifiable change sets default **up** to Tier 1. The command also prints a verification-evidence line aggregating the `verify_run_*` evidence across linked UT/IT/QT (`ran (N green)` | `not-run` | `unknown (no contracts declared)`). The tier, reversibility, and blast-radius count are persisted to a DEC's `risk_profile` by `document-changes`; `confidence` is left for a human to fill.

---

## Review Phase

### `specflow artifact-lint`

Run deterministic validation checks on artifacts. Zero tokens. Findings that already fire append a deterministic one-command `→ fix:` remedy where one exists (typo status → `update --status`, stale fingerprint → `fingerprint-refresh`, missing/empty AC → `update --ac`); genuinely-ambiguous findings get no hint. No new warnings, exit codes unchanged.

```bash
specflow artifact-lint [ID ...] [--type CHECK] [--fix] [--gate GATE] [--as-of YYYY-MM-DD] [--verbose]
```

| Flag | Purpose |
|------|---------|
| `--type` | Run only one check. The full list of check names is printed by the command's `--help`; a selection is described below. |
| `--fix` | Auto-fix the mechanical findings (rebuild indexes, recompute fingerprints) |
| `--gate` | Run one phase-gate checklist by name |
| `ID ...` | Positional artifact IDs, accepted for convenience: the run stays repo-wide and prints a one-line note that the IDs were ignored. Narrow with `--type`, or use `specflow artifact-review <ID>` for one artifact |
| `--as-of` | Date that time-dependent checks (SPIKE staleness) measure against (default: today, UTC). Makes a run reproducible. |
| `--verbose` | List every finding, including the ones already recorded in the findings baseline. By default a check with baselined findings prints `N known (baselined), M new` and lists only the new lines. |
| `--method` | Hidden (not in `--help`); accepted and ignored for compatibility with previously generated CI. Every check is deterministic, so `--method llm` behaves exactly like a bare run |

The authoritative list of `--type` names is the command's `--help`; the ones most often run alone:

| Check Type | What it validates |
|------------|-------------------|
| `schema` | Required fields, ID format, status values |
| `links` | Link integrity, orphan detection, V-model pairs |
| `coverage` | REQ→STORY→test completeness |
| `gate` | Phase-gate checklist validation |

Advisory checks such as `dec-risk-profile` and `ac-observable` are warn-only and never part of `--type gate`.

A full run (no `--type`) is read-only and prints an `Inputs:` line (the as-of date and the source-drift store state); its exit code depends only on the repository, that date, and the committed findings baseline below. Escalating warnings not recorded in the baseline fail the run; accounting-class checks (fingerprint-drift, bp-application, dead-oracle, conflicts, quality, ac-observable, dec-risk-profile, spike staleness) never escalate (@DEC-099).

### `specflow findings-baseline`

The lint ratchet. `.specflow/findings-baseline.yaml` is the committed list of known escalating findings; a full `artifact-lint` run fails on an escalating finding that is **not** in it, treats recorded ones as known debt, and ratchets resolved ones out. This replaced the run-count escalation (`.specflow/lint-warning-history.yaml`) in v1.17.1 (@DEC-099).

```bash
specflow findings-baseline update [--accept-new] [--as-of YYYY-MM-DD]
specflow findings-baseline diff [--as-of YYYY-MM-DD]
```

| Subcommand | Purpose |
|------------|---------|
| `update` | The only writer of the baseline (under the mutation lock). Seeds it when absent and drops resolved keys whenever it writes. New keys are written only with `--accept-new` (approval-gated: each accepted key is printed); with unaccepted new keys it writes nothing (resolved keys included) and exits 1. |
| `diff` | Read-only: lists new, known, and resolved findings against the baseline. Exit 1 when there are new findings, so CI can use it as a check. |
| `--as-of` | Both subcommands: the date time-dependent checks measure against (same meaning as `artifact-lint --as-of`), so the keys match a reproducible lint run |

`init` writes an empty baseline, so new projects start with the ratchet on. Upgrading an existing project: run `specflow findings-baseline update` once and commit the file — until then the ratchet is off and every full lint run prints a hint. After `renumber-drafts`, run `findings-baseline update --accept-new` in the same change (the keys include the renamed IDs). **Sunset (v1.18.0):** an absent baseline reads as empty, i.e. every escalating finding is new.

### `specflow checklist-run`

Run context-specific review checklists on artifacts.

```bash
specflow checklist-run [ARTIFACT_ID] [--all] [--gate GATE] [--proactive] [--dedup]
```

### `specflow artifact-review`

Compose lint, checklist review, and thinking technique prompts. The only artifact write is the `checklists_applied` stamp on each target; the checklist pass also writes a local log under `.specflow/checklist-log/`, and missing challenge/review schemas are bootstrapped on first use.

```bash
specflow artifact-review [ARTIFACT_ID] [--all] [--depth {quick,normal,deep}] [--techniques TECHNIQUES] [--gate GATE] [--proactive]
```

| Flag | Purpose |
|------|---------|
| `--all` | Review all artifacts (the checklist sweep) |
| `--depth` | `quick` (lint+checklist), `normal` (add agent-judged checks), `deep` (add thinking technique prompts) |
| `--techniques` | Comma-separated techniques for `--depth deep` (prompted for when omitted) |
| `--gate` | Phase-gate checklist |
| `--proactive` | Include proactive challenge items — shown when no blocking automated check failed; each prints with a `Hint:` line (the item's `llm_prompt`, when it has one) for the host agent to evaluate |

- **No ID and no `--all`:** runs lint only and says so. The checklist sweep stamps `checklists_applied` on every artifact it visits, so it never runs implicitly over the whole project.
- **`--depth deep`:** prints each lens as a self-contained prompt for the host agent, then the exact recording command — `specflow update <ID> --thinking-techniques <a,b>` — to run *after* the lenses have been applied. The CLI never stamps `thinking_techniques` itself; stamping before the review would silence the `unchallenged` lint for nothing.
- Findings are reported, not written back: the review pass creates no REVIEW, CHL or PREV artifacts (learned patterns come from `specflow done` and `specflow verify --seed-prev`).

### `specflow project-audit`

Full-project health review — horizontal + vertical + cross-cutting checks.

```bash
specflow project-audit [--standard STANDARD] [--baseline BASELINE] [--quick] [--sample-pct PCT]
```

| Flag | Purpose |
|------|---------|
| `--standard` | Standard name for compliance check (auto-detects if omitted) |
| `--baseline` | Drift anchor: drift compares `<baseline>` → newest release. Omitted → auto-detects the newest pair. An unknown name warns and falls back to the auto pair (never fails the audit). Anchored runs bypass the findings cache. |
| `--quick` | Skip cross-cutting analysis (horizontal + vertical only) |
| `--sample-pct` | Sample percentage for STORYs (default: 100) |

**Baseline naming policy.** Drift selection prefers semver-parseable baselines: with a mix of release names (`v1.13.4`) and freeform names (`snapshot`), the drift diff and evidence predecessor compare the two newest *releases*, falling back to the raw newest pair only when fewer than two names parse as semver. To keep that guarantee honest, `baseline create` enforces semver-shaped names (`v1.2`, `v1.2.3`, `v1.2.3-rc1`) and rejects freeform names with a loud error. **Consumer-visible breaking change:** automation that creates freeform-named baselines must switch to version-shaped names. Existing freeform baselines on disk are grandfathered — baselines are write-once and immutable, no migration runs — and still list/diff normally.

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

Names must be semver-shaped (`v1.2`, `v1.2.3`, `v1.2.3-rc1`): freeform names are rejected at create time so drift selection always has release versions to prefer (@CHL-351). Pre-existing freeform baselines are grandfathered — baselines are write-once, so nothing on disk is migrated or rejected after the fact.

### `specflow autoresearch`

Drive an installed autoresearch pack from any harness. The command reads and writes COMP/LOOP/EXPT/FIND artifacts; it does not call an external model API.

```bash
specflow autoresearch plan --competition COMP-001 --profile
specflow autoresearch run --competition COMP-001 [--no-start]
specflow autoresearch status [--competition COMP-001]
specflow autoresearch review --competition COMP-001
specflow autoresearch leaderboard [--competition COMP-001 | --all]
specflow autoresearch log --loop LOOP-001 --status kept --metric-value 0.73 --change-category features --summary "..."
specflow autoresearch log --loop LOOP-001 --status discarded --metric-value 0.71 --change-category params --summary "..." \
  --research-progress '{"evidence_ref":"commit:a1b2c3d","finding":"cutoff above 0.6 degrades recall","next_decision":"revisit"}'
specflow autoresearch suggest-finds --loop LOOP-001
```

| Subcommand | Purpose |
|------------|---------|
| `plan` | Create/update a LOOP or print the setup checklist; `--profile` includes the host-run three-sample noise probe in that checklist |
| `run` | Print the loop protocol and start a draft LOOP unless `--no-start`; refuses a second concurrent running LOOP |
| `status` | Print COMP-level closure-readiness (goals echo, confirmed FIND count, open agenda directions, LOOP census) even when every LOOP is completed/plateaued, then LOOP readiness/budget accounting when a running or draft LOOP resolves. Exit codes: `0` clear · `3` warns (missing agenda, evidence-free streak — reassess, don't rotate) · `1`/`2` fail (no git repo, concurrent running LOOPs, budget exhausted). A prioritized direction without a `progress` note is an advisory (exit stays `0`), not a warn. |
| `review` | Summarize all loops, experiments, and candidate findings for one competition |
| `leaderboard` | Rank experiments for one competition or all competitions |
| `log` | Record an experiment outcome and optional structured fields (`--set KEY=VALUE`, `--research-progress JSON`: `{evidence_ref, finding, next_decision}` with evidence_ref anchored to the EXPT) |
| `suggest-finds` | Propose one condensed FIND from a LOOP's experiment history |

### `specflow document-changes`

Generate change records (DEC artifacts) from git history. Generated records carry `dec_kind: change_record`; human architecture decisions use `dec_kind: adr`, allowing review and briefing surfaces to distinguish bookkeeping from design rationale.

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

### `specflow defect-from-monitor`

Materialize the ops MONITOR → DEF pipeline: when a human decides a breached MONITOR (ops pack) genuinely indicates an upstream requirement is no longer satisfied, freeze the MONITOR's ephemeral evidence into a DEF with full traceability (`fails_to_meet` → REQ, `exposed_by` → the MONITOR). Closing the DEF fires the existing on_closure → prevention-pattern capture path.

Accounting, not policing: if the source MONITOR was healthy at capture the command warns and still creates the DEF, and it never mutates the MONITOR.

```bash
specflow defect-from-monitor MON-NNN --req REQ-NNN [--severity LEVEL] [--title TITLE]
```

| Flag | Purpose |
|------|---------|
| `MON-NNN` | The MONITOR artifact whose breach indicates the unsatisfied REQ |
| `--req` | Upstream REQ the breach indicates is unsatisfied (required) |
| `--severity` | `low` \| `medium` \| `high` \| `critical` (default: `medium`) |
| `--title` | Override the auto-generated defect title |

The MONITOR's `observed_at` / `health` / `metrics` / `signals` / `captures` are frozen verbatim into a `## Observed at breach` body block so the ephemeral live-ops snapshot is preserved on the DEF.

---

## CI and Hooks

### `specflow ci generate`

Generate CI workflow files from `adapters.yaml` configuration.

```bash
specflow ci generate [--force] [--dry-run]
```

| Flag | Purpose |
|------|---------|
| `--force` | Overwrite a workflow file that differs from the generated content, after backing it up under `.specflow/cache/backups/<timestamp>/ci/` |
| `--dry-run` | Report what would happen (`new` / `unchanged` / `differs`, with a unified diff for a file that differs) without writing anything |

An existing file that is byte-identical to the generated content is reported `unchanged`. One that differs is preserved with a warning (hand edits are the user's) and the command prints the `--force` and `--dry-run` hints; nothing is overwritten without `--force`.

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

Install the specflow pre-commit hook into the directory git actually runs hooks from — resolved with `git rev-parse --git-path hooks`, so linked worktrees and a `core.hooksPath` override both land in the right place (a `note:` names the hooks path when one is set). `specflow init` calls the same installer.

```bash
specflow hook install [--force]
```

| Flag | Purpose |
|------|---------|
| `--force` | Replace a hook specflow does not own, or install into a global/system `core.hooksPath`; the previous hook is backed up first |

- **Ownership** is the template's header line (`# specflow pre-commit hook — installed by …`). A hook that carries it is upgraded in place (or reported `up to date` when identical); one without it belongs to someone else and is left as-is with exit 1 — the message offers `specflow hook install --force`, or keeping your own hook (pre-commit framework, lefthook, husky) and adding the line `specflow hook pre-commit` to it.
- **Backups:** any hook that is rewritten (foreign under `--force`, or an older specflow hook) is first copied to `.specflow/cache/backups/<timestamp>/hooks/pre-commit`.
- A `core.hooksPath` from the global or system git config is shared by every repository on the machine, so installing there is refused unless `--force`.
- Not a git repository, or not the top level of its working tree (a project nested inside another repository): exit 1, nothing written.

### `specflow hook pre-commit`

Run the pre-commit check (called by the git hook).

```bash
specflow hook pre-commit
```

### `specflow ci-gate`

Server-side RBAC gate for pull requests: walks every commit in `base..head` that touched an artifact and checks each consecutive status pair for schema legality, authorization of that commit's author, and that author's independence from the file's earlier authors — a PR is judged as a history, so an unauthorized intermediate approval cannot hide behind a clean net diff. With no team roles configured every check passes. Git-only, provider-agnostic.

```bash
specflow ci-gate --base origin/main --head "$GITHUB_SHA"
```

### `specflow pack-validate`

Validate a standards/compliance pack directory: `pack.yaml` manifest fields, the `SKILL.md` of every skill the pack adds, the standards and schema file layout, and the bare-`specflow` invocation rule for shipped skill scripts. The shipped `validate-pack.sh` defers to it.

```bash
specflow pack-validate .specflow/packs/<name>/
```

---

## Data Exchange

### `specflow import`

Import artifacts from external formats.

```bash
specflow import --adapter reqif FILE
```

### `specflow export`

Export artifacts to external formats, or SpecFlow skills to single-file platform formats.

```bash
specflow export --adapter reqif [--output FILE]            # artifact export
specflow export --skills --format <fmt> [--output DIR]     # skill export
```

Skill export (`--skills`) converts every shared SpecFlow skill into a
platform-specific single-file format: `cursor-rules` (.mdc), `codex-agents` (TOML agents), or `markdown` (plain rules).
Each skill's `references/**/*.md` files are inlined deterministically (sorted
by relative path) under an `## Inlined references` section, so the exported
file is self-contained and byte-stable across runs.

---

## Project Hygiene

### `specflow detect`

Project-hygiene scans.

```bash
specflow detect dead-code                                  # Report unreferenced functions/classes
specflow detect similarity                                 # Report near-identical function pairs
specflow detect orphan-code                                # Coverage % + unreferenced source files (globs honored)
specflow detect orphan-code --retro-link ARCH-003          # Link orphans into an existing artifact's output_files
specflow detect orphan-code --adopt ARCH-003                # Link the cluster and create a backfilled STORY
specflow detect orphan-code --adopt ARCH-003 --story-title "Imported worker"
specflow detect stale-docs                                 # Docs citing superseded/cancelled/deprecated artifacts (warning, never blocks)
```

`output_files` on STORY/REQ/ARCH/DDD may be literal paths or glob patterns (`**/*.java`).
The orphan meter credits all four types and expands globs through `lib.files.expand_output_files`,
the same helper reconcile and source-drift use — so a package glob in any artifact's
`output_files` is honored uniformly. The command reports **coverage %** (referenced ÷ total)
and the **biggest un-adopted cluster** (the top-level directory with the most orphan files). `--adopt` is the one-step mid-project closure: it retro-links the cluster into the target ARCH and creates a `backfilled` STORY that traces to it. `--story-title` overrides the generated story title.

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
specflow fingerprint-refresh [TARGET ...]
```

Targets are artifact IDs (preferred, like every other command) or file paths; both may be mixed and multiple targets may be given in one invocation. Each target reports its own result line; the exit code is non-zero only if *all* targets fail. With **no targets** the command is report-only: it lists stale fingerprints and exits 0 without modifying anything — a safe "what's drifted?" check that preserves the explicit-repair drift signal.

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

Merge two artifacts: links transfer to the target, the target gains a `supersedes` link to the source, and the source moves to `superseded` (or `deprecated`/`cancelled` when that is the legal terminal status from its current one).

```bash
specflow merge SOURCE_ID TARGET_ID
```
