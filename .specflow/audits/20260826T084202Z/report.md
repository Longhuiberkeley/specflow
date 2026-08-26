# Project Audit Report

- **Timestamp**: 20260826T084202Z
- **Artifacts analyzed**: 681 (cached: 70)
- **Chain coverage**: 100% (106/106 approved STORYs fully covered by UT+IT+QT)
- **Trend vs AUD-104**: errors 0→0 (Δ0), warns 25→25 (Δ0) (escalating 0→0, accounting 25→25), info 45→45 (Δ0), chain coverage 100%→100% (Δ0 pp)
- **Baseline drift: compared v1.13.6 → v1.13.7**

## Horizontal Analysis (per artifact type)

### challenge
- [○] No challenge artifacts use tags

## Vertical Analysis (V-model threads)

No V-model thread gaps found.

## Cross-cutting Analysis

### ac-coverage
- [⚠] REQ-001: 4 linked test(s) < 28 AC item(s) (2 green) — review coverage
- [⚠] REQ-006: 3 linked test(s) < 5 AC item(s) (0 green) — review coverage
- [⚠] REQ-007: 3 linked test(s) < 5 AC item(s) (1 green) — review coverage
- [⚠] REQ-008: 3 linked test(s) < 6 AC item(s) (1 green) — review coverage
- [⚠] REQ-009: 3 linked test(s) < 6 AC item(s) (2 green) — review coverage
- [⚠] REQ-010: 4 linked test(s) < 8 AC item(s) (0 green) — review coverage
- [⚠] REQ-011: 3 linked test(s) < 5 AC item(s) (0 green) — review coverage
- [⚠] REQ-012: 4 linked test(s) < 7 AC item(s) (0 green) — review coverage
- [⚠] REQ-014: 3 linked test(s) < 5 AC item(s) (2 green) — review coverage
- [⚠] REQ-015: 4 linked test(s) < 8 AC item(s) (1 green) — review coverage
- [⚠] REQ-016: 3 linked test(s) < 7 AC item(s) (0 green) — review coverage
- [⚠] REQ-017: 3 linked test(s) < 7 AC item(s) (0 green) — review coverage
- [⚠] REQ-022: 3 linked test(s) < 6 AC item(s) (3 green) — review coverage
- [⚠] REQ-023: 3 linked test(s) < 7 AC item(s) (3 green) — review coverage
- [⚠] REQ-024: 3 linked test(s) < 6 AC item(s) (3 green) — review coverage
- [⚠] REQ-025: 3 linked test(s) < 5 AC item(s) (3 green) — review coverage
- [⚠] REQ-026: 3 linked test(s) < 5 AC item(s) (3 green) — review coverage
- [⚠] REQ-027: 3 linked test(s) < 4 AC item(s) (3 green) — review coverage
- [⚠] REQ-030: 4 linked test(s) < 5 AC item(s) (4 green) — review coverage
- [⚠] REQ-033: 3 linked test(s) < 4 AC item(s) (3 green) — review coverage
- [⚠] REQ-035: 5 linked test(s) < 17 AC item(s) (5 green) — review coverage
- [⚠] REQ-037: 3 linked test(s) < 26 AC item(s) (3 green) — review coverage
- [⚠] REQ-AUTORESE-d684: 4 linked test(s) < 9 AC item(s) (4 green) — review coverage
- [⚠] REQ-DEFERRED-5cea: 3 linked test(s) < 6 AC item(s) (3 green) — review coverage
- [⚠] REQ-TRANSCRI-24b7: 3 linked test(s) < 4 AC item(s) (3 green) — review coverage

### ac-observability
- [○] REQ-001: 3/28 observable, 2 aspirational, 23 unclassified
- [○] REQ-002: 3/5 observable, 0 aspirational, 2 unclassified
- [○] REQ-003: 4/6 observable, 0 aspirational, 2 unclassified
- [○] REQ-004: 2/5 observable, 0 aspirational, 3 unclassified
- [○] REQ-005: 2/5 observable, 0 aspirational, 3 unclassified
- [○] REQ-006: 3/5 observable, 0 aspirational, 2 unclassified
- [○] REQ-007: 3/5 observable, 0 aspirational, 2 unclassified
- [○] REQ-008: 4/6 observable, 0 aspirational, 2 unclassified
- [○] REQ-009: 0/6 observable, 0 aspirational, 6 unclassified
- [○] REQ-010: 2/8 observable, 0 aspirational, 6 unclassified
- [○] REQ-011: 2/5 observable, 0 aspirational, 3 unclassified
- [○] REQ-012: 2/7 observable, 0 aspirational, 5 unclassified
- [○] REQ-013: 0/1 observable, 0 aspirational, 1 unclassified
- [○] REQ-014: 2/5 observable, 0 aspirational, 3 unclassified
- [○] REQ-015: 1/8 observable, 0 aspirational, 7 unclassified
- [○] REQ-016: 1/7 observable, 0 aspirational, 6 unclassified
- [○] REQ-017: 2/7 observable, 0 aspirational, 5 unclassified
- [○] REQ-018: 0/1 observable, 0 aspirational, 1 unclassified
- [○] REQ-019: 0/1 observable, 0 aspirational, 1 unclassified
- [○] REQ-020: 0/1 observable, 0 aspirational, 1 unclassified
- [○] REQ-021: 0/1 observable, 0 aspirational, 1 unclassified
- [○] REQ-022: 6/6 observable, 0 aspirational, 0 unclassified
- [○] REQ-023: 7/7 observable, 0 aspirational, 0 unclassified
- [○] REQ-024: 6/6 observable, 0 aspirational, 0 unclassified
- [○] REQ-025: 5/5 observable, 0 aspirational, 0 unclassified
- [○] REQ-026: 5/5 observable, 0 aspirational, 0 unclassified
- [○] REQ-027: 4/4 observable, 0 aspirational, 0 unclassified
- [○] REQ-028: 2/5 observable, 0 aspirational, 3 unclassified
- [○] REQ-029: 0/4 observable, 0 aspirational, 4 unclassified
- [○] REQ-030: 0/5 observable, 0 aspirational, 5 unclassified
- [○] REQ-031: 0/3 observable, 0 aspirational, 3 unclassified
- [○] REQ-032: 0/4 observable, 0 aspirational, 4 unclassified
- [○] REQ-033: 2/4 observable, 0 aspirational, 2 unclassified
- [○] REQ-034: 0/3 observable, 0 aspirational, 3 unclassified
- [○] REQ-035: 3/17 observable, 0 aspirational, 14 unclassified
- [○] REQ-037: 2/26 observable, 0 aspirational, 24 unclassified
- [○] REQ-AUTORESE-d684: 2/9 observable, 1 aspirational, 6 unclassified
- [○] REQ-DEFERRED-5cea: 2/6 observable, 0 aspirational, 4 unclassified
- [○] REQ-TRANSCRI-24b7: 4/4 observable, 0 aspirational, 0 unclassified
- [○] Project: 3 aspirational AC(s) across 2 REQ(s); 37/39 REQ(s) aspirational-free (86 observable, 157 unclassified)

### docs-staleness
- [○] 15 doc(s) scanned; all citations current.

### nfr-coverage
- [○] NFR categories: functional(39)

### orphan-code
- [○] All 239 source files traced to a STORY/REQ.

### verification
- [○] 87 artifact(s) declare verify_command; all have current, green verify runs.

## AC observability detail

Per-AC rows for the ac-observability cross-cutting lens: 160 of 246 AC item(s) across 39 REQ(s) with ACs are classified unclassified or aspirational. Observable items are omitted here (they need no action); the full all-class per-AC table is in this audit snapshot's subagent-cross-cutting.md.

### REQ-001
- [unclassified] The system **shall** decompose approved requirements into architecture and stories:
- [unclassified] Read all approved requirements from the artifact registry
- [unclassified] Propose architecture components with interfaces and dependencies
- [unclassified] Decompose into `STORY-*` artifacts using vertical slicing
- [unclassified] Link all artifacts via defined link roles
- [unclassified] The system **shall** orchestrate parallel subagent execution per story wave:
- [unclassified] Assign stories to subagents with minimal context
- [aspirational] Track progress and handle filesystem locks
- [unclassified] Auto-commit per task completion
- [unclassified] The system **shall** review artifacts against context-specific criteria:
- [unclassified] Assemble criteria from artifact type + domain tags + shared checklists
- [unclassified] Run automated (zero-token) checks first
- [unclassified] Run LLM-judged checks only if automated checks pass
- [unclassified] The system **shall** facilitate phase closure:
- [aspirational] Review completed work
- [unclassified] Extract prevention patterns into learned checklists
- [unclassified] Archive the current phase
- [unclassified] The system **shall** report on suspect flag status and change history:
- [unclassified] Show all unresolved suspect flags with source artifact lineage
- [unclassified] Show change history per artifact from the impact-log
- [unclassified] Support resolving individual suspect flags
- [unclassified] The system **shall** provide a convenience wrapper for minor artifact edits:
- [unclassified] Recompute fingerprint without triggering suspect cascade
- [unclassified] `create`: snapshot all artifact statuses and fingerprints
- [unclassified] `diff`: compare two baselines and report differences

### REQ-002
- [unclassified] Given a Markdown file with valid YAML frontmatter matching its schema, `specflow validate --type schema` passes
- [unclassified] Given a REQ artifact containing implementation details, an in-process checklist flags it as a boundary violation

### REQ-003
- [unclassified] Given REQ-001 with a downstream link from ARCH-001 via `refined_by`, when REQ-001's body text changes, ARCH-001 is flagged `suspect: true`
- [unclassified] Given `update_type: minor` in frontmatter, the system updates the fingerprint without propagating suspect flags

### REQ-004
- [unclassified] Given a skill invocation, the AI agent loads only the SKILL.md initially and reads `references/` files only when instructed by the workflow
- [unclassified] Given a task requiring fingerprint computation, the AI agent invokes a script rather than computing the hash itself
- [unclassified] Given a phase transition attempt, the system runs the corresponding gate checklist and advises the user (surfacing any blocking items for resolution, with an escape-hatch override); closing the phase records the advance rather than hard-blocking

### REQ-005
- [unclassified] Given a project with `.claude/` directory, `specflow init` detects Claude Code and copies skills into `.claude/skills/` without prompting
- [unclassified] Given a project with no platform directories, `specflow init` prompts the user to select a platform
- [unclassified] Given `specflow init` run on a project with an existing AGENTS.md containing a SpecFlow section, the system prompts about overwriting

### REQ-006
- [unclassified] Given adjacent sections with overlapping clause fragments, the skill runs a dedup pass that merges duplicates
- [unclassified] Given a platform without PDF support, the skill falls back to URL or pasted-text ingestion without error

### REQ-007
- [unclassified] Given a REQ with no downstream links, `specflow trace REQ-002` shows the REQ alone with no downstream entries
- [unclassified] Given a HAZ artifact (pack-added type) linked to REQ -> ARCH -> STORY -> QT, the chain report includes it in the depth distribution

### REQ-008
- [unclassified] The `specflow ci-gate` command accepts `--base` and `--head` arguments and uses only `git diff` internally
- [unclassified] Adding ci-gate support for a new CI provider requires only a new adapter file -- no changes to `hook.py` or `rbac.py`

### REQ-009
- [unclassified] Running `uv run pytest` discovers and executes all tests in `tests/`
- [unclassified] Tests for `lib/artifacts.py` cover: parsing YAML frontmatter, computing fingerprints, finding orphans, finding missing V-model pairs
- [unclassified] Tests for `lib/rbac.py` cover: solo-dev direct path, role-based authorization, independence violation detection
- [unclassified] Tests for `lib/standards.py` cover: loading standards YAML, reporting covered vs uncovered clauses
- [unclassified] All tests pass deterministically without environment variables, network, or LLM calls
- [unclassified] `pytest` is listed as a development dependency in `pyproject.toml`

### REQ-010
- [unclassified] `normative-language.md` includes guidance on compound shall detection and passive voice avoidance
- [unclassified] `/specflow-discover` SKILL.md references the enhanced quality guidance
- [unclassified] `specflow artifact-lint --type quality` performs regex-based quality checks on REQ bodies
- [unclassified] Quality check detects at least: ambiguity words, passive voice, compound shall, missing thresholds
- [unclassified] Quality check reports warnings (non-blocking) by default
- [unclassified] All existing tests continue to pass

### REQ-011
- [unclassified] `reqif_metadata` appears in `.specflow/schema/requirement.yaml` optional_fields
- [unclassified] `specflow export --adapter reqif` exports ARCH and DDD artifacts alongside REQ
- [unclassified] All existing tests continue to pass

### REQ-012
- [unclassified] REQ coverage shows percentage of approved REQs with linked STORY
- [unclassified] STORY test coverage shows percentage of implemented stories with UT/IT/QT links
- [unclassified] Chain completeness shows percentage of approved specs with verification tests
- [unclassified] All metrics compute deterministically with zero AI tokens
- [unclassified] All existing tests continue to pass

### REQ-013
- [unclassified] Run `specflow artifact-lint --type coverage` to verify all V-model pairs exist

### REQ-014
- [unclassified] `reqif_metadata` appears in `.specflow/schema/requirement.yaml` optional_fields
- [unclassified] `specflow artifact-lint` passes with no blocking issues after cleanup
- [unclassified] All existing tests continue to pass

### REQ-015
- [unclassified] Report includes traceability matrix for all verified REQs
- [unclassified] Report includes test results summary
- [unclassified] Report includes standards compliance coverage
- [unclassified] Report is placed alongside the baseline in `.specflow/baselines/`
- [unclassified] All operations are deterministic (zero AI tokens)
- [unclassified] All existing tests continue to pass
- [unclassified] > **Note**: Target version v0.3.0. Deferred from v0.2.0 to keep scope manageable.

### REQ-016
- [unclassified] `specflow standards gaps` shows per-standard coverage score as a percentage
- [unclassified] Uncovered clauses are sorted by severity/priority
- [unclassified] Each uncovered clause includes a suggested artifact type for remediation
- [unclassified] All operations are deterministic (zero AI tokens)
- [unclassified] All existing tests continue to pass
- [unclassified] > **Note**: Target version v0.3.0. Deferred from v0.2.0 to keep scope manageable.

### REQ-017
- [unclassified] `specflow init` offers optional artifact types (HAZ, RISK, CTRL) and copies selected schemas
- [unclassified] Optional types integrate with `specflow artifact-lint` for schema validation
- [unclassified] Optional types integrate with `specflow trace` for traceability chains
- [unclassified] Running `specflow init` again does not duplicate already-installed schemas
- [unclassified] All existing tests continue to pass

### REQ-018
- [unclassified] Commands execute successfully.

### REQ-019
- [unclassified] Commands execute successfully.

### REQ-020
- [unclassified] Commands execute successfully.

### REQ-021
- [unclassified] Commands execute successfully.

### REQ-028
- [unclassified] A user can declare a competition (dataset, metric, verify command) and start an autonomous loop against it
- [unclassified] After a loop completes, FIND artifacts capture what worked, what failed, and next steps
- [unclassified] Subsequent loops on the same competition read prior FINDs before ideation

### REQ-029
- [unclassified] Every EXPT has a required `loop` field referencing a LOOP ID
- [unclassified] Every LOOP has a required `competition` field referencing a COMP ID
- [unclassified] `specflow trace COMP-NNN` walks down to LOOPs and EXPTs
- [unclassified] An EXPT's metric_value, change_category, and summary are queryable across all EXPTs in a COMP

### REQ-030
- [unclassified] FIND artifacts have what_worked, what_failed, next_steps, confidence, and applies_to fields
- [unclassified] FINDs live at the competition level (linked to COMP, not LOOP)
- [unclassified] A FIND may reference a single LOOP via source_loop, or be a cross-loop synthesis (source_loop optional)
- [unclassified] Each new LOOP records the FIND IDs it read into its knowledge_input field
- [unclassified] FIND status lifecycle: draft → confirmed → (superseded | falsified)

### REQ-031
- [unclassified] LOOP schema has a required `mode` field with enum {explore, exploit, validate}
- [unclassified] The skill's `explore-exploit-protocol.md` reference documents when each mode is applicable based on loop count and metric trend
- [unclassified] The user explicitly sets the mode at LOOP creation (no auto-selection in v1)

### REQ-032
- [unclassified] `pack.yaml` accepts an `adds_skills: [<skill-name>, ...]` field
- [unclassified] `apply_pack()` copies each named skill directory from `pack_root/skills/<name>/` to the platform-specific skills directory (resolved via `platform.get_skills_dir()`)
- [unclassified] Skill files follow the existing no-overwrite policy (user edits preserved on pack reinstall)
- [unclassified] The capability is generic — any future pack (not just autoresearch) can ship skills

### REQ-033
- [unclassified] Each schema YAML gains an optional `category:` field; missing values default to `spec`
- [unclassified] Default categories: `spec` (REQ/ARCH/DDD/UT/IT/QT), `work` (STORY/SPIKE/DEC/DEF), `review` (REVIEW/AUD/CHL), `research` (COMP/LOOP/EXPT/FIND)

### REQ-034
- [unclassified] `specflow trace COMP-NNN` shows: COMP header, list of LOOPs (with mode, iteration count, best metric, status), each LOOP's EXPT summary counts, separate FINDINGs section listing FIND artifacts for that COMP
- [unclassified] `specflow trace LOOP-NNN` shows the parent COMP, all EXPTs in that LOOP, and any FINDs derived from it
- [unclassified] `specflow trace EXPT-NNN` shows parent LOOP and COMP

### REQ-035
- [unclassified] `competition.yaml` gains `objective_type`, `success_criteria`, `domain`, `pre_check_command`, `post_check_command`, `noise_characterization`, `goals`
- [unclassified] `experiment.yaml` gains `parameters`, `model_origin`, `sweep_results`, `checks`, `baseline_note`, `diversity_metrics`, `failure_analysis`
- [unclassified] `loop.yaml` gains `goal`, `required_findings`, `termination_suggestions`
- [unclassified] `finding.yaml` gains `deployability`, `safety_assessment`, `applies_to_domain`
- [unclassified] `competition-setup-protocol.md` documents `goals`, noise characterization, unified runner pattern, and domain-specific auxiliary metric recommendations
- [unclassified] `explore-exploit-protocol.md` documents `family_of_good` mode behavior using `diversity_metrics` to prefer uncorrelated keeps
- [unclassified] `finding-generation-protocol.md` integrates `failure_analysis` from discarded EXPTs into `what_failed` synthesis
- [unclassified] `specflow autoresearch review` warns when: completed LOOP has zero FINDs, kept EXPT lacks `parameters`, domain-recommended auxiliary metrics are missing, discarded EXPT lacks `failure_analysis`
- [unclassified] `specflow autoresearch leaderboard` supports `--group-by model_origin` and `--show-family` for swarm views (flags registered in argparse)
- [unclassified] `specflow artifact-lint` gains `_check_autoresearch_logging` that warns when domain-recommended fields are missing on kept EXPTs
- [unclassified] `finding-generation-protocol.md` reframes negative results as falsified / conditional / sensitive / inconclusive rather than forcing "definitively falsified" (parameter/noise sensitivity is a robustness statement, not a verdict)
- [unclassified] Pre/post-checks are documented as derived from `goals`/`success_criteria`; the post-check validates deploy-fit, not just a re-measured metric
- [unclassified] `competition-setup-protocol.md` adds a metric-vs-intent reflection so a thin single metric is caught at setup time
- [unclassified] `tests/test_autoresearch_pack.py` covers all new schema fields, pre/post check lifecycle, lint warnings for missing domain metrics, and FIND enforcement on completed LOOPs

### REQ-037
- [unclassified] `specflow verify <ID> | --all | --type T | --dry-run | --evidence-file PATH`
- [unclassified] is a working command that executes a declared `verify_command` and writes
- [unclassified] `verify_run_at` + `verify_run_exit_code` (+ `verify_run_evidence`) onto the
- [unclassified] artifact's frontmatter.
- [unclassified] and **never blocks** a commit, a status transition, or a release — the
- [unclassified] accounting-not-policing invariant, machine-enforced.
- [unclassified] Verified artifacts carry machine-checkable `verify_run_*` evidence when a
- [unclassified] `verify_command` is declared (artifacts with no contract are unaffected and
- [unclassified] not penalized).
- [unclassified] Accounting warnings about missing/divergent verification evidence **never**
- [unclassified] structural findings do.
- [unclassified] `specflow brief --next` surfaces a verify-evidence gap as exactly one
- [unclassified] deterministic, advisory line (frontmatter query: declared `verify_command`
- [unclassified] with no `verify_run_at`, or `verify_run_exit_code` != declared
- [unclassified] `verify_exit_code`); never blocking, silent for projects that use no contracts.
- [unclassified] The `/specflow-execute` skill names `specflow verify <ID>` (or `--all`) as a
- [unclassified] deterministic step before transitioning test/story artifacts to `verified`,
- [unclassified] mirroring how it already invokes `specflow artifact-lint`.
- [unclassified] `docs/cli-reference.md`, `docs/lifecycle.md` (mermaid AND ASCII), and the
- [unclassified] README feature table each reference `specflow verify` / verification contracts
- [unclassified] consistently.
- [unclassified] The shipped skill template and its live `.claude/skills/` mirror stay in
- [unclassified] parity (a new `references/verification-contracts.md` documents field meanings,
- [unclassified] recorded run fields, and the never-blocking invariant).

### REQ-AUTORESE-d684
- [unclassified] EXPT schema accepts `auxiliary_metrics` optional field (freeform YAML dict) and artifacts with this field pass lint
- [unclassified] `competition-setup-protocol.md` documents multi-criteria competitions (primary metric + guards + auxiliary logging) with a worked quant example
- [unclassified] `competition-setup-protocol.md` documents leakage and gaming patterns (read-only eval, one-number verify, robustness-adjusted primaries) as recommendations, not mandates
- [aspirational] `specflow autoresearch plan|run|review|leaderboard` CLI subcommand works with multi-COMP repos (`--competition`, `--all`)
- [unclassified] SKILL.md references CLI backends for all subcommands instead of inlining full protocol
- [unclassified] Pack `context_snippet` is defined in pack.yaml and `inject_pack_context()` injects it into instruction files with idempotent sentinel markers
- [unclassified] `platforms.yaml` has `instruction_file` field for each platform

### REQ-DEFERRED-5cea
- [unclassified] `specflow phase-set <phase> --reason` records forward and rewind transitions in state history without gating (accounting-not-policing); execution state clears when leaving executing.
- [unclassified] REQ/ARCH/DDD support status 'superseded' (from approved/implemented/verified only) and link role 'supersedes'; docs-staleness continues to warn on superseded citations.
- [unclassified] artifact-lint flags an empty Acceptance Criteria section as a blocking error and an NFR REQ without a numeric threshold as a non-blocking scope-honest warning ('functional' category exempt).
- [unclassified] `specflow init` warns when multiple AI-host platforms are detected; `specflow refresh --all-platforms` refreshes every detected host.

## Summary

| Severity | Count |
|----------|-------|
| Error    | 0 |
| Warning  | 25 |
| Info     | 45 |
