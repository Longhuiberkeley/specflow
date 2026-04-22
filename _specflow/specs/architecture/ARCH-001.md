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
fingerprint: sha256:9796f65acf40
links:
- target: REQ-001
  role: derives_from
created: 2026-04-10
checklists_applied:
- checklist: check-ARCH-001
  timestamp: '2026-04-11T13:45:48Z'
- checklist: check-ARCH-001
  timestamp: '2026-04-14T17:03:22Z'
modified: '2026-04-21'
version: 1
---

# CLI Core

The `specflow` CLI is implemented as a Python package with argparse-based command dispatch.

## Package Structure

```
src/specflow/
├── __init__.py
├── cli.py                  # Entry point: argparse, subcommand dispatch
├── commands/               # Individual command implementations (one module per command)
│   ├── __init__.py
│   ├── init.py             # specflow init
│   ├── status.py           # specflow status
│   ├── create.py           # specflow create
│   ├── update.py           # specflow update
│   ├── artifact_lint.py    # specflow artifact-lint
│   ├── artifact_review.py  # specflow artifact-review
│   ├── project_audit.py    # specflow project-audit
│   ├── trace.py            # specflow trace
│   ├── generate_tests.py   # specflow generate-tests
│   ├── baseline.py         # specflow baseline create|diff
│   ├── document_changes.py # specflow document-changes
│   ├── change_impact.py    # specflow change-impact
│   ├── fingerprint_refresh.py  # specflow fingerprint-refresh
│   ├── ci.py               # specflow ci generate|ci-gate
│   ├── hook.py             # specflow hook install|pre-commit
│   ├── import_cmd.py       # specflow import
│   ├── export_cmd.py       # specflow export
│   ├── detect.py           # specflow detect dead-code|similarity
│   ├── standards.py        # specflow standards (with subcommands: gaps, ...)
│   ├── checklist_run.py    # specflow checklist-run
│   ├── go.py               # specflow go (execute orchestration)
│   ├── done.py             # specflow done (phase closure)
│   ├── split.py            # specflow split
│   ├── merge.py            # specflow merge
│   ├── unlock.py           # specflow unlock
│   ├── locks.py            # specflow locks
│   ├── rebuild_index.py    # specflow rebuild-index
│   ├── renumber_drafts.py  # specflow renumber-drafts
│   └── ...                 # Additional recovery/hygiene commands
├── lib/                    # Shared library modules (24 modules + techniques/ subpackage)
│   ├── __init__.py
│   ├── artifacts.py        # Artifact discovery, parsing, fingerprinting
│   ├── baselines.py        # Baseline creation, immutability, diff
│   ├── checklists.py       # Checklist assembly and execution
│   ├── ci.py               # CI adapter generation and gate logic
│   ├── config.py           # Config and state management
│   ├── dedup.py            # Three-tier deduplication (Jaccard, TF-IDF, LLM)
│   ├── display.py          # Terminal color constants
│   ├── executor.py         # Subagent execution orchestration
│   ├── git_utils.py        # Git diff, blame, history queries
│   ├── impact.py           # Suspect propagation and impact-log
│   ├── lint.py             # Schema validation, status hierarchy
│   ├── locks.py            # Filesystem locks
│   ├── platform.py         # Platform detection (14 platforms)
│   ├── rbac.py             # Role-based access control
│   ├── reqif.py            # ReqIF 1.2 import/export
│   ├── scaffold.py         # Directory and file creation
│   ├── standards.py        # Standards loading and gap analysis
│   ├── waves.py            # Wave-based dependency grouping
│   ├── analysis.py         # Audit analysis (horizontal, vertical, cross-cutting)
│   ├── challenge.py        # Challenge artifact creation
│   ├── learning.py         # Prevention pattern extraction
│   ├── defects.py          # Defect lifecycle tracking
│   ├── draft_ids.py        # Draft ID management and renumbering
│   └── techniques/         # Adversarial review techniques
│       ├── __init__.py
│       ├── devils_advocate.py
│       ├── premortem.py
│       ├── assumption_surfacing.py
│       └── red_blue_team.py
└── templates/              # Template files copied during init
    ├── config.yaml
    ├── state.yaml
    ├── agents-section.md
    ├── skills/             # Platform-specific skill facades
    │   └── shared/         # Unified skill templates (10 Tier-1 skills)
    └── schemas/            # Artifact type schemas
```

## Entry Point (`cli.py`)

The main entry point uses `argparse` with subparsers. 29 top-level subcommands are registered in `cli.py` via a dispatch dict with lazy imports:

```python
def cmd_<name>(args: argparse.Namespace) -> int:
    from specflow.commands import <module> as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))
```

The `main()` function:
1. Parses arguments
2. Dispatches to the appropriate command module
3. Returns exit code (0 success, 1 failure, 2+ for specific errors)

## Command Taxonomy

### Discover
- `specflow init` — Scaffold project, detect platform, install skills
- `specflow status` — Project dashboard with coverage metrics
- `specflow standards gaps` — Compliance gap analysis (subcommand of `specflow standards`)

### Plan
- `specflow create` — Create artifact with auto-assigned ID
- `specflow update` — Update artifact frontmatter

### Execute
- `specflow go` — Wave-based story execution orchestration
- `specflow done` — Phase closure with pattern extraction
- `specflow generate-tests` — Deterministic test stub generation

### Review
- `specflow artifact-lint` — Zero-token validation (schema, links, status, IDs, fingerprints, coverage, quality)
- `specflow checklist-run` — Context-specific review criteria execution
- `specflow artifact-review` — LLM-judged artifact review with adversarial lenses
- `specflow project-audit` — Full-project health review (deterministic core)
- `specflow trace` — Traceability chain visualization

### Release
- `specflow baseline create` — Immutable project state snapshot
- `specflow baseline diff` — Compare two baselines
- `specflow document-changes` — Retroactive change records from git
- `specflow change-impact` — Blast-radius review of unreviewed changes
- `specflow fingerprint-refresh` — Recompute fingerprints without cascade

### CI
- `specflow hook install` — Git pre-commit hooks for RBAC
- `specflow hook pre-commit` — Pre-commit hook entry point
- `specflow ci generate` — CI workflow generation (GitHub Actions)
- `specflow ci-gate` — Provider-agnostic RBAC gate

### Data
- `specflow import` — ReqIF and other format import
- `specflow export` — ReqIF and other format export

### Hygiene
- `specflow detect dead-code` — AST-based dead code detection
- `specflow detect similarity` — Token-based code similarity
- `specflow renumber-drafts` — Draft ID renumbering with cross-ref rewriting

### Recovery
- `specflow unlock` — Break stale filesystem locks
- `specflow locks` — List active locks
- `specflow rebuild-index` — Rebuild `_index.yaml` registries
- `specflow split` — Split artifact into two
- `specflow merge` — Merge artifact into another

## Shared Library (`lib/`)

### `artifacts.py`
- `Artifact` dataclass: path, frontmatter, body, links
- `discover_artifacts(root)` — Walk `_specflow/` tree, parse all artifacts
- `build_id_index(artifacts)` — Map ID → Artifact for O(1) lookups
- `create_artifact(root, type, title, ...)` — Create new artifact with next sequential ID
- `update_artifact(root, id, ...)` — Update frontmatter fields
- `compute_fingerprint(body)` — SHA256 of normative content
- `find_orphans()`, `find_missing_v_pairs()`, `trace_chain()` — Link health

### `baselines.py`
- `create_baseline(root, name)` — Snapshot all artifact statuses and fingerprints
- `load_baseline(root, name)` — Load baseline YAML
- `diff_baselines(b1, b2)` — Added, removed, modified artifacts

### `impact.py`
- Suspect propagation: recompute fingerprint, flag downstream artifacts
- Impact-log event creation: `<ARTIFACT-ID>_<timestamp>.yaml`
- 3-tier typo cascade defense: explicit intent, convenience command, magnitude heuristic

### `lint.py`
- Schema validation: required fields, allowed values, ID format regex
- Status transition validation: allowed predecessor statuses
- Link validation: target existence, role validity
- Coverage validation: V-model pair completeness
- Quality validation: EARS patterns, ambiguity words, passive voice, compound shall

### `rbac.py`
- `authorize_status_transition()` — Role-based approval for status changes
- `check_independence()` — Verify reviewer did not also implement
- `render_codeowners()` — Generate CODEOWNERS from role assignments

### `standards.py`
- `list_installed_standards()` — Find standards in `.specflow/standards/`
- `load_standard()` — Parse standard YAML (clauses, severity, description)
- `gap_analysis()` — Map artifacts to clauses, report uncovered

### `reqif.py`
- `import_reqif()` — Parse ReqIF 1.2 archive → REQ/ARCH/DDD artifacts
- `export_reqif()` — Generate ReqIF 1.2 XML from artifacts (SpecFlow ID used
  directly as `SPEC-OBJECT` IDENTIFIER)
- Deterministic internal IDs via `_new_id(prefix, seed) = sha256(prefix:seed)[:10]`
  for type defs, attribute defs, and spec hierarchies (see DDD-004)

### `display.py`
- Terminal color constants: `RED`, `GREEN`, `YELLOW`, `CYAN`, `BOLD`, `NC`
- Extracted from 20+ command files for consistency
