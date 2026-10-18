---
id: ARCH-001
title: CLI Core
type: architecture
status: implemented
priority: high
rationale: The CLI core is the programmatic entry point that dispatches commands and
  coordinates all SpecFlow operations
tags:
- cli
- python
- core
suspect: false
fingerprint: sha256:3a39b7a46b71
thinking_techniques:
- assumption_surfacing
- devils_advocate
links:
- target: REQ-001
  role: derives_from
created: 2026-04-10
checklists_applied:
- checklist: check-ARCH-001
  timestamp: '2026-04-11T13:45:48Z'
- checklist: check-ARCH-001
  timestamp: '2026-04-14T17:03:22Z'
modified: '2026-10-08'
version: 3
---

# CLI Core

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-101, R1-027); earlier text described the 29-command, 24-module v0.2-era package with commands/standards.py, `gap_analysis()` and 10 shipped skills.

The `specflow` CLI is implemented as a Python package with argparse-based command dispatch.

## Package Structure

```
src/specflow/
├── __init__.py             # __version__
├── __main__.py             # python -m specflow
├── cli.py                  # Entry point: build_parser() (argparse) + dispatch dict in main()
├── commands/               # One module per command (51 modules), e.g.:
│   ├── init.py, refresh.py, status.py, brief.py
│   ├── create.py, update.py, approve.py, list_cmd.py, schema_cmd.py, transitions.py
│   ├── go.py, done.py, phase_status.py, phase_set.py, cascade_status.py, reconcile.py
│   ├── generate_tests.py, verify.py
│   ├── artifact_lint.py, checklist_run.py, artifact_review.py, project_audit.py
│   ├── trace.py, rtm.py, risk_tier.py
│   ├── baseline.py, findings_baseline.py, document_changes.py, change_impact.py
│   ├── fingerprint_refresh.py, defect_from_suspect.py, defect_from_monitor.py
│   ├── hook.py             # specflow hook install|pre-commit AND run_ci_gate (specflow ci-gate)
│   ├── ci.py               # specflow ci generate
│   ├── rbac_check.py, import_cmd.py, export_cmd.py, detect.py, adopt.py
│   ├── standards_gaps.py   # specflow standards gaps
│   ├── patterns.py, handbook.py, practices.py, pack_validate.py, autoresearch.py
│   └── unlock.py, locks.py, rebuild_index.py, split.py, merge.py, renumber_drafts.py
├── core/                   # Pure semantic core (ARCH-039)
│   ├── findings.py         # Typed finding records
│   ├── findings_baseline.py
│   └── policy.py           # Exit-code policy over typed findings
├── lib/                    # Shared library: 45 modules + techniques/ and adapters/ subpackages, e.g.:
│   ├── artifacts.py        # Artifact discovery, parsing, fingerprinting, link walks, create/update
│   ├── lint.py             # Schema validation, status hierarchy, fingerprint and AC helpers
│   ├── impact.py           # Suspect propagation, impact log, reverse impact, split/merge
│   ├── baselines.py        # Baseline creation, immutability, diff
│   ├── checklists.py       # Checklist assembly
│   ├── challenges.py       # CHL creation (shared by artifact-review and project-audit)
│   ├── challenge.py        # Proactive challenge items from assembled checklists
│   ├── ci.py               # Artifact context loading for deterministic review
│   ├── config.py           # Config/state reading and writing, format-version helpers
│   ├── dedup.py            # Duplicate candidates (tag Jaccard, TF-IDF); host agent confirms
│   ├── display.py          # Terminal colour constants
│   ├── executor.py         # Wave orchestrator for `specflow go`: context assembly, never execution
│   ├── git_utils.py        # Git subprocess helpers (commits, changed files, file history, hooks path)
│   ├── analysis.py         # Python AST analysis for project hygiene (detect)
│   ├── locks.py            # Repo-wide mutation lock and per-artifact locks
│   ├── platform.py         # Platform registry and detection (13 platforms)
│   ├── rbac.py             # Role-based access control for status transitions
│   ├── reqif.py            # ReqIF 1.2 import/export
│   ├── scaffold.py         # Init scaffolding, pack application, context injection
│   ├── standards.py        # Standards loading and compliance gap analysis
│   ├── practices.py, practices_seed.py   # Best-practice anatomy and bundled seed catalogue
│   ├── waves.py, learning.py, defects.py, draft_ids.py, evidence.py, verification.py, risk.py, ...
│   ├── adapters/           # base.py, github_actions.py, reqif.py
│   └── techniques/         # Thinking-technique prompt generators
│       ├── devils_advocate.py
│       ├── premortem.py
│       ├── assumption_surfacing.py
│       └── red_blue_team.py
├── packs/                  # Bundled packs: adoption, autoresearch, iso26262-demo, ops, tldr-communication
└── templates/              # Files copied during init/refresh
    ├── adapters.yaml
    ├── agent-context.md
    ├── platforms.yaml      # Platform registry
    ├── checklists/
    ├── skills/
    │   └── shared/         # Unified skill templates: 12 skills + specflow-references (13 dirs)
    └── schemas/            # Artifact type schemas (+ optional/)
```

## Entry Point (`cli.py`)

The main entry point uses `argparse` with subparsers. `build_parser()` registers 53 top-level subcommands (the list `specflow --help` prints), and `main()` maps each command name to a `cmd_<name>` handler in a dispatch dict. Handlers import their command module lazily:

```python
def cmd_<name>(args: argparse.Namespace) -> int:
    from specflow.commands import <module> as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))
```

`_find_project_root()` walks up from the current directory to the nearest ancestor holding `.specflow/`; only `init` always uses the current directory.

The `main()` function:
1. Parses arguments
2. Calls `warn_format_version_once()` (except for `hook pre-commit`, which refuses on its own), then dispatches to the handler for the command
3. Returns exit code (0 success, 1 failure, 2+ for command-specific results, e.g. `project-audit` returns 2 for escalating warnings and 3 for errors)

## Command Taxonomy

### Discover
- `specflow init` — Scaffold project, detect platform, install skills
- `specflow refresh` — Update skills, agent-context and templates without full re-init
- `specflow status` — Project dashboard with coverage metrics
- `specflow brief` — One-call recall digest (phase, inventory, suspects, next wave, recent changes)
- `specflow standards gaps` — Compliance gap analysis (subcommand of `specflow standards`)
- `specflow domain set|show|suggest` — Project domain for domain-aware checklists
- `specflow patterns list|show|update|retire` — Learned prevention patterns
- `specflow practices seed|validate|migrate` — Best-practice artifacts
- `specflow handbook generate` — Deprecated alias for `practices seed`

### Plan
- `specflow create` — Create artifact with auto-assigned ID
- `specflow update` — Update artifact frontmatter
- `specflow approve` — Batch-approve artifacts by type/status (one explicit human act)

### Execute
- `specflow go` — Plan approved stories into dependency waves and assemble each story's context
- `specflow done` — Phase closure with pattern extraction
- `specflow phase-status` — Advisory phase-readiness check
- `specflow phase-set` — Record a phase transition (forward or rewind)
- `specflow cascade-status` — Cascade STORY status to linked ARCH/DDD/REQ
- `specflow reconcile` — Move approved STORYs to implemented when their work is detected
- `specflow generate-tests` — Deterministic test stub generation
- `specflow verify` — Run verification contracts and record evidence

### Review
- `specflow artifact-lint` — Zero-token validation (schema, links, status, IDs, fingerprints, coverage, quality and more)
- `specflow checklist-run` — Context-specific review criteria execution
- `specflow artifact-review` — Lint + checklist pass, then agent-judged and thinking-technique prompts for the host agent
- `specflow project-audit` — Full-project health review (deterministic core)
- `specflow trace` — Traceability chain visualization
- `specflow rtm` — Requirements traceability matrix
- `specflow transitions` — Legal next statuses for an artifact
- `specflow list` — List artifacts with filters
- `specflow schema` — Fields and transition map for a type
- `specflow risk-tier` — Computed risk tier for a change set

### Release
- `specflow baseline create` — Immutable project state snapshot
- `specflow baseline diff` — Compare two baselines
- `specflow findings-baseline update|diff` — Committed findings baseline (known lint debt)
- `specflow document-changes` — Retroactive change records from git
- `specflow change-impact` — Blast-radius review of unreviewed changes
- `specflow defect-from-suspect` — DEF from a suspect-flagged artifact
- `specflow defect-from-monitor` — DEF from a breached MONITOR (ops pack)
- `specflow fingerprint-refresh` — Recompute fingerprints without cascade

### CI
- `specflow hook install` — Git pre-commit hooks for RBAC
- `specflow hook pre-commit` — Pre-commit hook entry point
- `specflow rbac check` — Resolved roles and transition authorization
- `specflow ci generate` — CI workflow generation (GitHub Actions)
- `specflow ci-gate` — Provider-agnostic RBAC gate (a top-level command, implemented by `commands/hook.py:run_ci_gate`)

### Data
- `specflow import` — ReqIF and other format import
- `specflow export` — ReqIF and other format export, or skill export (`--skills --format`)

### Hygiene
- `specflow detect dead-code|similarity|orphan-code|stale-docs` — Project-hygiene scans
- `specflow renumber-drafts` — Draft ID renumbering with cross-ref rewriting
- `specflow adopt status` — Brownfield adoption status (adoption pack)

### Recovery
- `specflow unlock` — Break stale filesystem locks
- `specflow locks` — List active locks
- `specflow rebuild-index` — Rebuild `_index.yaml` registries
- `specflow split` — Split artifact into two
- `specflow merge` — Merge artifact into another

### Research and Packs
- `specflow autoresearch plan|run|status|frontier|review|leaderboard|log|suggest-finds` — Autoresearch competition loop
- `specflow pack-validate` — Validate a pack

## Shared Library (`lib/`)

### `artifacts.py`
- `Artifact` dataclass: path, frontmatter, body, links
- `discover_artifacts(root, artifact_type=None)` — Walk `_specflow/` tree, parse all artifacts
- `build_id_index(artifacts)` — Map ID → Artifact for O(1) lookups
- `create_artifact(root, artifact_type, title, ...)` — Create new artifact with next sequential ID
- `update_artifact(root, artifact_id, **updates)` — Update frontmatter fields
- `compute_fingerprint(body)` — SHA256 of the stripped body, truncated to 12 hex chars (`sha256:<12>`)
- `find_orphans()`, `find_missing_v_pairs()`, `trace_chain()`, `compute_chain_depth()` — Link health

### `baselines.py`
- `create_baseline(root, name)` — Snapshot all artifact statuses and fingerprints
- `load_baseline(root, name)` — Load baseline YAML
- `diff_baselines(root, name_a, name_b)` — Added, removed, modified artifacts

### `impact.py`
- Suspect propagation (`propagate_suspects`): recompute fingerprint, flag downstream artifacts
- Impact-log event creation: `.specflow/impact-log/<timestamp>_<ARTIFACT-ID>.yaml` (`-2`, `-3`… suffix on a same-second collision)
- 3-tier typo cascade defense: explicit `update_type: minor`, convenience command (`fingerprint-refresh` passes `force_minor`), magnitude heuristic (`classify_change_magnitude`)
- Reverse impact from source files: `build_output_file_index`, `query_reverse_impact`, `flag_suspects_from_matches`

### `lint.py`
- Schema validation: required fields, allowed values, ID format regex (`validate_artifact_schema`)
- Status hierarchy validation (`validate_status_hierarchy`)
- Fingerprint validation and recompute
- Acceptance-criteria helpers (count, text, presence)
- The link, coverage and quality (EARS, ambiguity words, passive voice, compound shall) checks live in `commands/artifact_lint.py`

### `rbac.py`
- `authorize_status_transition()` — Role-based approval for status changes
- `check_independence()` — Verify reviewer did not also implement
- `render_codeowners()` — Generate CODEOWNERS from role assignments

### `standards.py`
- `list_installed_standards()` — Find standards in `.specflow/standards/`
- `load_standard()` / `load_standards()` — Parse standard YAML (clauses, severity, category)
- `check_compliance()` — Map artifacts to clauses via `complies_with`, report covered/uncovered and a score

### `reqif.py`
- `import_reqif()` — Parse a ReqIF 1.2 XML file → REQ artifacts (requirement type only)
- `export_reqif()` — Generate ReqIF 1.2 XML from REQ/ARCH/DDD artifacts (SpecFlow ID used
  directly as `SPEC-OBJECT` IDENTIFIER)
- Deterministic internal IDs via `_new_id(prefix, seed) = sha256(prefix:seed)[:10]`
  for type defs, attribute defs, and spec hierarchies (see DDD-004)

### `display.py`
- Terminal color constants: `RED`, `GREEN`, `YELLOW`, `YELLOW_DIM`, `CYAN`, `BOLD`, `DIM`, `NC` (empty when colour is disabled)
- Shared by the command modules for consistency
