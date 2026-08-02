# Changelog

All notable changes to SpecFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.12.6] - 2026-08-03

### Fixed

- **RC1 cry-wolf kill (foundational-doctrine provenance).** The horizontal analysis no longer emits "N/N best-practice (or decision) artifacts have no links/provenance": BP/DEC are foundational doctrine, upstream-less by design (other artifacts derive from them), so absent `links[]` is not orphan-provenance. `has_provenance` now exempts `best-practice` and `decision` the same way it already exempted the autoresearch competition root. Genuine orphan-provenance detection for every other type stays intact. Drops the `specflow-release-gate` audit from 17 to 16 escalating structural warns.

### Added

- **`specflow project-audit --dry-run`.** Prints the full findings/report with the identical exit code (errors→3, escalating warns→2, else 0) but skips all four write side-effects: the `.specflow/audits/<ts>/` snapshot directory, the AUD artifact, the CHL artifacts, and the `.specflow/audits/.cache` + index mutations. Enables local pre-push verification of the gate's exit code without dirtying the tree.

### Verification

- 825 tests passing (baseline 820; +5, no regressions).
- `specflow project-audit --dry-run` exits 2 with 16 escalating warns, tree stays clean.

## [1.12.5] - 2026-08-02

### Added

- **Deterministic autoresearch status.** `specflow autoresearch status` reports LOOP readiness, budget, prior knowledge, EDA/agenda completeness, repeated-category exploration, and stuck streaks with exact next actions. Research-quality findings remain advisory; conflicting running LOOPs and exhausted budgets stop continuation as structural hazards.
- **Active-pack refresh.** `specflow refresh --packs` previews and refreshes schemas, checklists, skills, and context for configured packs. Existing differing files are preserved unless `--force` is explicit, and `_specflow/` artifacts are never refresh targets.
- **Protocol-state schemas.** LOOP and EXPT schemas now document the EDA, agenda, coverage, condensation, hypothesis, lesson, and failure-stage fields used by the autoresearch protocol.

### Fixed

- Pre-check failures now use the existing terminal outcome `discarded` plus `failure_stage: pre_check`, preserving the four-status EXPT contract.
- ML handbook practices use the unambiguous `ML-01`…`ML-22` namespace instead of colliding with SpecFlow `BP-NNN` artifacts.
- Centralized link parsing/validation across `create`, `update`, and `--set links`; malformed entries fail loudly and no-op link mutations no longer rewrite artifacts.
- Commit-hook advisory checks now surface warning-only findings while remaining non-blocking.
- Schema/transition rendering tolerates a scalar predecessor in hand-authored pack schemas; CLI help now includes previously hidden commands.
- Clarified BP-006: accounting warnings stay advisory while structural audit findings may block the release gate.

### Verification

- 820 tests passing (baseline 813; +7, no regressions).
- Artifact schema lint passes for all 489 artifacts.
- Quick project audit: 0 errors; remaining warnings are pre-existing traceability/accounting debt plus release-added verification links now resolved for STORY-076/STORY-083.

## [1.12.4] - 2026-08-02

This release was designed by mining ~2,300 real agent CLI invocations from
conversation transcripts across five dogfood projects. The dominant friction
classes — unlearnable status transitions (~500 errors, agents brute-forcing
with for-loops), hand-edited frontmatter (697 events), rejected type
abbreviations (80+), and repeated `--help` re-reads (174) — drove every item
below. No new blocking gates (accounting-not-policing); the deterministic
core is unchanged.

### Added

- **Self-explaining CLI.** A central did-you-mean hook: every misspelled
  subcommand and unrecognized flag now suggests the closest valid one
  (scoped per-subcommand so unrelated flags never leak into suggestions).
  Exit codes and usage output are unchanged.
- **`specflow transitions <ID>`** — read-only legal-next-states for an
  artifact, plus the full type-specific transition table. Both status
  rejection messages ("Cannot transition", "Invalid status") now hint at it.
- **`specflow list [--type] [--status] [--tags] [--json]`** — first-class
  artifact query, replacing hand-parsed `_index.yaml`. Unknown types error
  with the valid list instead of silently listing everything.
- **`specflow schema <type>`** — prints a type's required/optional fields
  (the valid `--set` keys), its status transition map, and allowed link
  roles, so keys are discoverable without trial and error.
- **Link management on `update`** — `--links` (replace), `--add-link
  TARGET:ROLE` (repeatable, dedups), `--remove-link TARGET` (idempotent).
  Closes the gap that drove agents to hand-edit frontmatter; the
  specflow-discover skill now teaches `--add-link` instead of a flag that
  never existed.
- **Type abbreviations everywhere** — `create`/`list`/`schema` accept
  case-insensitive canonical abbreviations (`dec`, `req`, `qt`, `ut`, `it`,
  `ddd`, `def`, …) via one `normalize_type()` resolver; unknown types get the
  valid list plus a closest-match suggestion.
- **Per-type initial status on `create`** — omitting `--status` now uses the
  type's natural root status (`open` for defects, `draft` for specs). Fixes
  a real bug: `specflow create --type defect` failed outright on the
  hardcoded `draft` default. Multi-root types (e.g. `experiment`) require an
  explicit `--status` and list the allowed values.
- **`fingerprint-refresh` accepts artifact IDs and multiple targets** (file
  paths still work); per-target result lines, non-zero exit only when every
  target fails.
- **Repo dogfoods its own gates** — this repo's CI now runs the `ci-gate`
  (RBAC, PR-only) and `release-gate` (tag-only) jobs the generator emits for
  consumers; the pre-commit hook additionally reports status-cascade and
  story-linkage issues as non-blocking advisory warnings (CI Pass 1 remains
  the authoritative blocker).
- **Opt-in `lint.autoresearch_logging_strict`** — escalates the warn-only
  autoresearch-logging findings (missing hypothesis/failure_analysis on kept
  EXPTs) to blocking errors, mirroring `compliance_evidence_strict`. Default
  off.

### Fixed

- **Link inputs fail loudly, never silently.** `_parse_links` no longer
  drops unparseable input on the floor: a JSON object (vs. array), malformed
  JSON, or a bare target without a role is an explicit error that leaves the
  artifact untouched — previously these could write garbage links, wipe the
  whole link list with a success message, or crash with a traceback.
- **Audit exit-code truthfulness** — accounting lenses (docs-staleness) are
  printed but excluded from the warn count that drives `project-audit`'s
  exit code 2, matching the documented "surfaced, never enforced" doctrine;
  structural warns still escalate.
- **Skill/context guidance accuracy** — the agent-context cheat-sheet now
  lists exactly the real core types (drops schemaless `prevention`, moves
  ops-pack `run`/`monitor` to the pack parenthetical, adds the missing test
  types); `.specflow/` (config — never edit) vs. `_specflow/` (artifacts —
  use `specflow update`) is now distinguished; the linear "draft → approved
  → implemented → verified" arrow is replaced with type-specific transition
  guidance.
- **Link-target warnings no longer fire on standards-clause-shaped targets**
  (`ISO-14971`) — only tokens whose prefix is a registered artifact prefix
  warn.

### Changed

- **Autoresearch enforcement claims are now honest** — the pack's
  SKILL/protocol/handbook docs describe the Category Diversity Gate, Stuck
  Detector, etc. as "protocol gates enforced by the agent" instead of
  "structural gates (not advisory)" — they always had zero code backing.
  Protocol substance unchanged. (A warn-only deterministic diversity lint
  was prototyped and dropped after false-positiving on legitimate
  single-category exploration in the cs2-bet corpus — cry-wolf, per BP-005.)
- **ROADMAP** — the SPIKE-lifecycle detector moved from Deferred to
  Delivered (it shipped; `artifact-lint --type spike-lifecycle`).
- **Docs** — `docs/cli-reference.md` documents the full new surface
  (transitions/list/schema, update link flags, fingerprint-refresh targets,
  type abbreviations, did-you-mean).

**Verification:** 807 tests passing (baseline 723; +84), artifact-lint PASS,
installed↔shipped skill parity confirmed, and the mined failure corpus
replayed as regression tests (`tests/test_v124_ergonomics.py`).

## [1.12.3] - 2026-07-30

### Highlights

- **The existing BP/PREV learning loops are now visible and actually consumed.**
  `specflow brief` reports BP, PREV, FIND, and CHL health even when every surface
  is empty, so a dormant learning system no longer fails silently. Matching active
  or approved BP artifacts now join the local `checklist-run` pipeline alongside
  learned PREV patterns.

### Fixes

- Centralized BP selection in one canonical matcher shared by CI context and local
  checklist assembly, using tag overlap or explicit `applies_to` links.
- Prevented normal artifact review from injecting the same BP both as prose context
  and as a checklist item; each applicable practice is judged once.
- Reused `brief`'s parsed artifact inventory when computing executable stories,
  eliminating a second repository scan and YAML parse pass.
- Corrected checklist assembly documentation to describe all seven ordered sources.
- Added dogfood BP-003..007 and PREV-001..002 examples, generated-agent guidance,
  STORY/REQ traceability, and focused regression coverage.
- Reviewed the implementation with independent Sonnet and Opus passes; fixed all
  verified findings.

**Verification:** 723 tests passing (baseline 718; +5 tests, 0 regressions).

## [1.12.2] - 2026-07-21

### Fixes

- **Generated CI now bootstraps SpecFlow from its Git source.** The GitHub
  Actions workflow `specflow init` / `specflow ci generate` writes for consuming
  projects ran `uv sync` then `uv run specflow …`, but consuming projects don't
  declare specflow as a dependency and specflow is not on PyPI (the `specflow`
  name there is an unrelated JSON-Schema library) — so the blocking
  `specflow-pass-1` job failed with "command not found" on every consuming
  project out of the box. SpecFlow-only jobs now run
  `uvx --from git+https://github.com/Longhuiberkeley/specflow@v<ver> specflow …`,
  pinned to the generating version for reproducible CI. SpecFlow's own repo was
  unaffected (there specflow is the project itself). The `pytest` job still uses
  `uv sync`, since it needs the consuming project's own dependencies.
- **`change-impact` CI job no longer passes a non-existent `--all` flag.** The
  generated step ran `specflow change-impact --all`, but the CLI defines no
  `--all`; argparse exited 2 and was silently swallowed by `|| true`, so the job
  was a no-op. It now uses bare `specflow change-impact` (matching SpecFlow's own
  dogfood workflow).
- **`specflow init` no longer offers "GitLab CI" as a provider.** No GitLab
  adapter is registered (only `github-actions` ships), so selecting it made
  `specflow ci generate` fail. Non-GitHub CI remains build-it-yourself via
  `docs/authoring-an-adapter.md`.
- **Install/upgrade instructions point at the Git source.** The init skill and
  `docs/cli-reference.md` said `uv tool upgrade specflow` (bare), which resolves
  the unrelated PyPI package. Replaced with
  `uv tool install --force git+https://github.com/Longhuiberkeley/specflow`.
- **Removed the orphaned, divergent `templates/ci/github-actions.yml`.** Nothing
  referenced it; the runtime generator (`lib/adapters/github_actions.py`) is the
  source of truth for shipped workflows.
- **Added test coverage for CI workflow generation** (`tests/test_ci_generation.py`),
  which is why the bootstrap and `--all` bugs went undetected.
- **The bootstrap fix is now applied everywhere, not just generated CI.** The
  `uvx --from git+…` fix only covered CI workflows; the identical `uv run specflow`
  bootstrap (which fails in consuming projects for the same reason) survived in
  every sibling surface that runs in a consuming project. All now invoke bare
  `specflow` (on PATH via the documented `uv tool install git+…`):
  - the **pre-commit hook** (`specflow init` auto-installs it) — previously blocked
    every commit in a consuming project. The three divergent copies of the hook
    script (the adapter default, `specflow hook install`'s fallback, and `specflow
    init`'s inline copy) are consolidated into one source of truth
    (`_DEFAULT_HOOK_SCRIPT`), and its subprocess checks no longer shell out through
    `uv run`;
  - the **8 shipped checklist templates** whose `script:` items ran
    `uv run specflow artifact-lint …` via `bash -c` (phase-gates, readiness,
    in-process, domain);
  - the **~12 skill-doc templates** and **7 user-facing CLI hints** that told the
    consumer's AI / the user to run `uv run specflow …`.
  Clean CI runners are the one exception and keep `uvx --from git+…@v<ver>`.
- **The release-gate CI job now actually runs.** Its `if: startsWith(github.ref,
  'refs/tags/')` guard was unreachable because the workflow trigger had no `tags:`
  filter — tag pushes never started the workflow. Added `tags: ['v*']` to the
  `push:` trigger. (Consumers that push version tags will now see the release-gate
  job run, which is its intent.)

## [1.12.1] - 2026-07-21

### Highlights

- **Deterministic signals stop crying wolf.** A read-only retrospective of three
  real projects found `artifact-lint`/`status`/`audit`/docs-citation burying real
  issues under hundreds-to-thousands of false positives, training users to ignore
  them. This release makes those load-bearing signals *truthful* and *pack-aware* —
  no new blocking gates, no new link-role vocabulary (D-18 stays frozen).

### Features

- **`autoresearch leaderboard --group-by loop`.** Slices a multi-loop competition
  by `EXPT.loop` so per-loop-ordinal EXPT IDs (reused every loop) are told apart;
  new `iteration` optional field on `experiment.yaml` records the per-loop ordinal
  machine-readably. Also revives the previously-dead `--group-by change_category`
  and `strategy_family` paths.
- **`brief` health nags.** A compact Health block surfaces one-time-setup and
  subsystem-decay that otherwise fail silently: unset `domain` (disables
  domain-aware checklists/review), stale fingerprints, and an adoption handshake
  that never cut a baseline. Zero noise on a healthy project.
- **`brief --next` is backlog-aware.** After a strategic rewind to
  specifying/planning, an advisory notes implemented/verified stories left in the
  backlog (and routes an all-verified backlog to `/specflow-artifact-review`), so
  the phase-based primary line no longer looks like it forgot the backlog.
- **`project-audit` batches findings into actionable CHLs.** Findings group by
  axis/category into ONE table-bodied CHL per group (stable, count-free title so
  dedup suppresses repeats) instead of one empty-body one-liner per finding — a
  run that once spewed ~75 unactioned CHLs now produces ~3–8 engagable ones.

### Fixes

- **Docs citation recognizes draft/coded-family IDs (A1).** The D-22 "docs as
  knowledge surface" scanner only matched numeric IDs, so every modern project
  (draft IDs like `STORY-VPSPROB-0a17`) reported "0 cite an artifact" — the feature
  was silently dead. The regex now accepts both shapes (with a trailing boundary so
  a longer token can't match a truncated ID).
- **Acceptance-criteria counter matches bullets/checkboxes (A2).** The STORY-size
  check counted only numbered ACs, so bulleted / `- [x]` / Given-When-Then sections
  read "0 acceptance criteria". It now reuses the canonical counter shared with REQ.
- **Link-role validation de-noised (A3).** A role canonical on *some* type but
  absent from *this* type's whitelist (e.g. `derives_from` on a CHL/REVIEW/AUD) is
  accepted as legitimate cross-type usage — never mislabeled "Unknown". Recognized
  near-misses still read "Non-canonical" with a hint; genuine typos still warn;
  repeated same-role warnings collapse to one summary line per role.
- **Coverage honors STORY→REQ `derives_from` (A4).** `check_coverage`, `rtm`,
  `status`, and the status-cascade nudge all count `derives_from` alongside
  `implements`, so legacy-story projects no longer read falsely uncovered.
- **Orphan-code heuristic matches inline backtick paths (A5).** The body scan only
  matched a backtick-quoted path at the *start* of a line, missing the dominant
  inline style `Code: \`src/…\`` and marking genuinely-traced files as orphans.
- **Accounting is autoresearch-pack-aware (B1).** EXPT/LOOP/FIND/COMP carry
  provenance in frontmatter (`loop`, `competition`, `source_loop`, `knowledge_input`),
  not `links[]`; orphan and "no links" counts now recognize it, so headline numbers
  on research-heavy projects are no longer ~90% noise.
- **Autoresearch structured-field nudges (B4).** `artifact-lint` warns on a
  non-draft EXPT missing `hypothesis` (and a kept one missing `hypothesis_outcome`)
  so FIND→REQ promotion can fire; the SKILL.md promotion recipe now reads
  `best_metric` from the parent LOOP (where `autoresearch log` writes it).
- **Baseline recomputes the fingerprint from the body (C1).** Baselines snapshotted
  the *stored* frontmatter fingerprint, which a stale index can leave empty —
  recording the empty-string hash and making drift detection useless. They now
  derive it from the body (identical when the stored value was already correct).

### Decisions / Docs

- **D-18 held.** The frozen relationship vocabulary is *not* expanded — canonical
  roles are de-noised (recognized cross-type), never blessed as new per-type roles;
  no blocking status gates, no `doctor` command, no audit exit-code escalation.
- Autoresearch `SKILL.md`: EXPT titling guidance steered away from collision-prone
  per-loop ordinals toward descriptive titles (+ `iteration`); FIND-promotion
  recipe corrected to source `best_metric` from the LOOP.

### Tests

- +19 tests: canonical-role-union (A3), `derives_from` coverage across rtm/status/
  cascade (A4), audit CHL grouping + dedup-stable titles (B2), leaderboard
  loop/category grouping + `iteration` round-trip (B3), backlog advisory (D1), and
  the adoption-handshake health nag (D2). Total: 701 tests passing.

## [1.12.0] - 2026-07-10

### Features

- **`specflow phase-set <phase> [--reason TEXT]`.** Records a phase transition, forward or a REWIND (e.g. "go back to requirements"); accounting-only — never blocks — and keeps `brief --next` honest after reverse-lifecycle moves. Clears execution state when leaving `executing`. `/specflow-discover`, `/specflow-plan`, and `/specflow-execute` now call it automatically on a detected rewind.
- **`specflow rtm [--req ID] [--format table|markdown|csv] [--gaps]`.** Bidirectional requirements-traceability matrix: REQ → ARCH → STORY → verifying tests per row, gap markers per column, orphan-tests footer.
- **`specflow rbac check [--email E] [--type T --to-status S]`.** Resolves the current git author's team roles and optionally checks a status-transition authorization; reports "RBAC not active (single-user mode)" when no team config exists. Nested under `rbac` so a future `rbac doctor` can share the namespace.
- **Supersession for REQ/ARCH/DDD.** New `superseded` status (allowed from `approved`/`implemented`/`verified`, not `draft`) plus a `supersedes` link role, closing the D-18 gap where only DEC/BP had a supersession path. Docs-staleness checks already warn on citations of superseded artifacts.
- **Quality gates in `artifact-lint`'s acceptance check.** An empty `## Acceptance Criteria` section (header only, no content) is now a blocking error. An NFR-tagged REQ (`non_functional_category` set to a value other than `functional`) whose acceptance criteria contain no numeric threshold gets a scope-honest warning (never blocking, cites `CKL-REV-REQ-02`) — functional-category REQs are exempt from this check.
- **Multi-host awareness.** `specflow init` warns when multiple AI-host platform dirs are detected (skills installed to one host only); `specflow refresh --all-platforms` refreshes every detected host in one pass.

### Fixes

- `specflow refresh`'s agent-context injection crashed for platforms whose instruction file lives in a nested directory that didn't exist yet — the parent directory is now created (`mkdir -p`-equivalent) before injection.

## [1.11.2] - 2026-07-10

### Features

- **Phase machine.** `close_phase` now advances `state.current` along `PHASE_ORDER`; `phase_status` wires all 6 advisory gates; REQ-004 §6/AC5 softened to advisory.
- **Intent-first routing.** AGENTS.md / `agent-context.md` updated with plain-language trigger support; expanded skill trigger utterances; `/specflow-start` added to the command reference.
- **Autoresearch: FIND→REQ promotion bridge.** Deployable findings promote to core REQs with `derives_from` links; quick/smoke tier skip-rules added for LOOP budget ≤ 5.

### Fixes

- `specflow brief --next` now routes execute → `/specflow-artifact-review` → ship instead of jumping straight to ship when all stories are implemented but no review or V-model tests (UT/IT/QT) exist; `/specflow-start` router example updated to match.
- `specflow autoresearch plan` printed a `specflow create` hint with flags that don't exist (`--competition`/`--mode`/`--budget`); now prints the real `--set KEY=VALUE` form.
- `specflow create --set links='[…]'` crashed with a `TypeError` (duplicate keyword); `--set links` now merges into `--links`, and other reserved keys (`--set status=…` etc.) get a clear error pointing at the dedicated flag. Repo docs normalized to `--links`; a new doc-example lint test guards documented commands against argparse rot.
- Stale-command cleanup: removed phantom `approve --batch` references, dead `validate`/`tweak`/`new` command aliases; added a `--version` flag; V-model two-metric docstrings and `role_normalize` docstring correction.
- Ops pack: "check LIVE health" trigger disambiguated from full project audit.
- Artifact-lint conflict message made scope-honest (numeric-range only), pointing at `CKL-REV-REQ-03`.

### Docs

- Docs pruning: deleted the completed `docs/autoresearch-fork-adaptation.md`; archived `docs/plan.md` and `docs/plan-autoresearch-integration.md` to `docs/.archive/`.
- `specflow refresh` documented in `docs/cli-reference.md`.
- `/specflow-execute`: trivial-change lean path (Step 1L) that backfills a STORY for typo/dep-bump/rename fixes; honest rewording of the vacuous pre-code RBAC check.
- `/specflow-init`: brownfield detection routes to the adoption preset; post-upgrade `specflow refresh` reminder.
- `/specflow-ship`: release tag derived from `git describe` with a single confirm instead of two open questions.
- AGENTS.md / agent-context: recall leads with `specflow brief`; orient-first routing rule; research/spike/autoresearch routing disambiguation.

## [1.11.1] - 2026-07-04

### Docs

- Synced the docs-surface (D-22) entry points that v1.11.0 skipped: README (`/specflow-doc` added to the slash-command table + a new "Docs — the knowledge surface" section, install pin bumped to `v1.11.0`), the `docs/lifecycle.md` flowchart and Tier-1 table (docs-surface node + `/specflow-doc` row), and the router/audit/init/change-impact skills now reference the docs surface and `specflow detect stale-docs`. Qualified the pack-only `/specflow-autoresearch` references in `specflow-doc` and `specflow-execute` so they read as "if installed".

## [1.11.0] - 2026-07-01

### Highlights

- **Docs as a knowledge surface (D-22).** `docs/` + root markdown (README, AGENTS, CHANGELOG, …) is now a recognized **knowledge surface** — indexed, citable, and staleness-checked — but **never** a lifecycle artifact (no `DOC` prefix, no status, no `_index.yaml` entry, no DEC on edit; git stays the change log). Docs cite spec artifacts with inline `@ID` markers (`@ARCH-007`, `@DEC-018.2`); `specflow brief` shows a Docs surface block; `specflow detect stale-docs` and `project-audit` warn (never block) when a doc cites a superseded/cancelled/deprecated artifact. New `/specflow-doc` skill is the authoring/citing/syncing UX.
- **Coverage-metric fix: markdown is no longer counted as orphan code.** `.md`/`.mdc` were in `SOURCE_EXTENSIONS`, so `docs/*.md`, root markdown, *and* nested prose (skill files, per-package READMEs) were silently counted as uncovered source — deflating coverage. Markdown is prose, never code: the orphan-code denominator now excludes it everywhere (this repo's dogfood scan drops 271→189).

### Features

- `lib/docs.py` — discovers the surface (reusing `compute_fingerprint`), extracts `@ID` citations (schema-driven prefixes so pack types count; code-fence/inline/indented stripping to avoid example false-positives), builds the artifact→doc reverse index, and checks citation staleness (warn-only).
- `lib/files.py:docs_surface_paths` — the configurable surface (a `docs:` block in `config.yaml`: `roots` default `docs/`, root-level `*.md` always recognized, `extra_files`, `exclude`); `scan_source_files` subtracts it.
- `specflow detect stale-docs` — new informational subcommand (exit 0; never blocks).
- `docs:` config block, `doc_refs` optional frontmatter field on REQ/ARCH/DDD/DEC (author-facing metadata, not a link role), Docs surface in `brief` / `adopt status`, a non-blocking `docs-staleness` audit concern, and a derived `_specflow/docs-index.yaml` reverse-index cache materialized by `rebuild-index`.
- `/specflow-doc` skill (SKILL.md + 4 reference files), mirrored ship ↔ live.

### Fixes

- Markdown removed from `SOURCE_EXTENSIONS` so no prose is ever miscounted as orphan code (the headline D-22 miscount, now fixed for nested docs too, not just root + `docs/`).
- Citation stripping now handles double-backtick spans and indented code blocks, eliminating phantom `@ID` citations from syntax examples.
- Staleness messages show the cited token (`@DEC-018.2`), not just the resolved parent.
- `describe_source_scope` and `docs_surface_paths` now treat an explicit `docs.roots: []` consistently; docstring corrections in `lib/docs.py` / `lib/files.py`.
- Release-process docs (`AGENTS.md`): bump both `pyproject.toml` and `src/specflow/__init__.py`; CHANGELOG-format example corrected to Keep a Changelog.

### Decisions / Docs

- **D-22** (docs as a recognized-but-non-artifact knowledge surface; accounting-not-policing extended to prose). Runtime guidance lives in the `/specflow-doc` SKILL + references; `docs/decisions.md` holds the design rationale only, consistent with D-18/D-20/D-21.

### Tests

- +27 tests: `test_docs.py` (citation extraction incl. backtick/fenced/indented guards, surface enumeration, the markdown-not-orphan regression guard, discovery, reverse index, staleness, derived cache, config robustness). Total: **580 passing**.

## [1.10.0] - 2026-06-26

### Highlights

- **Ops pack (RUN/MONITOR) — a 5th "deployed-and-observed" memory class** (alongside spec/work/review/research). **RUN** freezes a deployment at deploy-time (what's deployed, where, when, satisfying which REQ); **MONITOR** is an append-only timestamped observation/metric journal (drift, latency, sensor values, ephemeral-data captures). Closes two regimes with no prior home: live/ephemeral data capture and MLOps (deploy / drift / retrain). Domain-neutral by design — see D-21. **Complements, not replaces, your MLOps/GitOps stack:** it's a governance ledger over MLflow / W&B / ArgoCD (`deployed_ref` points at them), not a metrics store or a reconciler.
- **Auto-adaptive artifact guidance.** Per-domain **concept→artifact maps** are surfaced in discover/plan; packs contribute their own rows (autoresearch→COMP/EXPT, ops→RUN/MONITOR), so a project's full "which artifact fits this concept?" mapping assembles from domain + installed packs. `specflow domain suggest` detects a domain from dependency manifests (quant/ml seeded, extensible), and `brief --next` is pack-state-aware (a running LOOP, a breached/stale MONITOR). The framework adapts to the use-case instead of requiring the user to know artifact-type boundaries.
- **Communication pack enriched.** `tldr-communication` distilled from a 2-line stub into a concise action-first directive (reader-model + cognitive constraints + rules + pre-send check), adapted from `github.com/ayghri/i-have-adhd`. Behaviourally framed (no diagnosis claim); opt-in only; baseline `agent-context.md` untouched.
- **Quant/ML domain surfacing.** New `quant.md` + `ml.md` domain checklists (each opening with a concept→artifact map); `quant`/`ml`/`data-science` added to `domain set` help.

### Features

- `src/specflow/packs/ops/` — new pack: `pack.yaml`, `schemas/run.yaml` + `monitor.yaml` (`category: ops`, domain-neutral fields), `specflow-ops` skill (deploy + observe workflows, link via `derives_from`/`belongs_to`/`informs`).
- `lib/domain_detect.py` + `specflow domain suggest` — extensible signal→domain table; pure read, never silently sets.
- `commands/brief.py` — `_CATEGORY_ORDER` gains `ops`; `_next_skill_recommendation` accepts `active_packs` and appends an optional second advisory line for actionable subsystem states (running LOOP / breached or unobserved MONITOR).
- discover + plan skills surface the concept→artifact map for the set domain; discover lists `quant`/`ml`/`data-science` and offers `domain suggest`.
- Review-skill trigger tightening: leading `SCOPE =` discriminator on `specflow-audit` / `-artifact-review` / `-change-impact-review` so "review X" routes correctly.
- Flowchart + discoverability: `docs/lifecycle.md` flowchart (mermaid + ASCII) now shows the optional autoresearch/ops extensions and the EXPT→RUN→MONITOR→retrain loop; README gains an Ops section; `ops` added to `init --preset` help.

### Decisions / Docs

- **D-21** (ops pack as a deployed-and-observed memory class; domain-neutral core with auto-adaptive concept→artifact maps). Runtime guidance stays native (pack `context_snippet`, `SKILL.md`, `references/`); `docs/decisions.md` holds the design rationale only, consistent with D-18/D-20. Extended with a **positioning** note (complement-not-replacement: governance ledger above MLflow/W&B/ArgoCD) and the known limits tracked as deferred roadmap items (ops ingestion adapter, multi-component `deployed_ref`, rollback link role).

### Tests

- +32 tests: `test_ops_pack.py` (schema lifecycle, pack install, domain-neutrality, link roles, pack-state routing), `test_tldr_pack.py` (injection idempotency + conciseness cap), `test_domain_detect.py` (quant/ml detection, word boundaries, extensibility). Skill templates synced (live ↔ ship parity confirmed). Total: **553 passing**.

## [1.9.6] - 2026-06-24

### Highlights

- **Functional briefing, multi-agent framing, routing, and batch approval.** Shipped in commit `94f0413`; this entry backfills the gap between the tagged `v1.9.6` release and the CHANGELOG, which previously topped out at 1.9.5.

## [1.9.5] - 2026-06-19

### Highlights

- **Source-scope engine** — `scan_source_files` now respects `.gitignore` inside git repos (via `ls-files`), with an opt-in `source_scope` config block (`include` allowlist that bypasses the extension heuristic, `exclude` denylist, additive `extensions`). The orphan-meter denominator is clamped to the scanned scope so coverage stays ≤100%. Folded in: v1.9.4's schema sync, verification-gate ordering, and discover thinking-technique recording.

### Features

- **`source_scope` config block** (`source_scope.include`, `exclude`, `extensions`) — declarative control over what SpecFlow treats as "source code" for coverage, orphan, and drift scans. `include` is an authoritative allowlist; `exclude` is a denylist subtracted last; `extensions` additively extends the built-in code-extension heuristic.
- **Git-aware source scanning** — `scan_source_files` uses `git ls-files` (tracked ∪ untracked-not-ignored) inside work trees, automatically respecting `.gitignore`; falls back to `rglob` + `EXCLUDE_DIRS` pruning otherwise.
- **`adopt status` scope line** — `specflow adopt status` now surfaces how "source" was scoped (include/exclude/extensions + `.gitignore` respected) so the denominator is never silently capped.
- **`go --wave`** — `specflow go --wave <N>` filters execution to a specific wave, with range validation.
- **Skill best-practices steps** — added a "Load Best Practices" step to artifact-review, audit, change-impact-review, and ship skills. Ship skill adds thinking-technique lenses (temporal-drift, regulator, premortem).

### Fixes

- **`create` stdin-hang guard** — `sys.stdin.read()` now guarded with `select.select(..., 0.0)` so a non-tty-but-idle stdin no longer blocks.
- **`create` duplicate-warning crash fix** — the blocking-duplicate path referenced `YELLOW` without importing it (`NameError`); added to imports.
- **`detect orphan-code` exit-code contract** — changed `return 1` to `return 0` when orphans found without `--retro-link`, matching the documented contract ("All return exit code 0 regardless of findings").
- **`status` single discovery** — `discover_artifacts(root)` moved from four separate helper calls to a single call in `run()`, passed to all helpers (5× → 1× scan).
- **Config defaults cleanup** — added missing keys (`learning.learnable_techniques`, `learning.max_patterns_per_session`, `lint.compliance_evidence_strict`, `source_scope`); removed unused keys (`impact_analysis.auto_flag`, `auto_resolve`, `remind_after`).
- **Variable shadow in `config.py`** — renamed `specflow = root / ".specflow"` to `specflow_dir` to avoid shadowing the module import.
- **`learning.py` public API** — `_LEARNABLE_SEVERITIES`, `_DEFAULT_LEARNABLE_TECHNIQUES`, `_learnable_techniques()`, `_max_patterns_per_session()` made public (removed underscore prefix). Updated all consumers (artifact_review, done, tests).
- **ANSI escape standardization** — replaced raw escape sequences in `go.py`, `detect.py`, `done.py`, `baseline.py`, `checklist_run.py`, `document_changes.py`, `fingerprint_refresh.py`, `trace.py` with `specflow.lib.display` constants.
- **`execute` trigger narrowing** — description changed from "DEFAULT implementation path for ANY code change" to "Implementation path for planned stories"; trigger keywords narrowed to "implement stories," "execute the plan," "start building," or "run the wave".
- **Platform repositioning** — README and docs updated to position as first-class Claude Code + OpenCode support; OpenCode marked `preferred: true` in `platforms.yaml`.
- **Domain constants deduplicated** — new `lib/domain_constants.py` (was duplicated in `autoresearch.py` and `artifact_lint.py`).
- **`--no-auto` help fix** — changed from "Show pattern summary without extracting" to "Skip auto-extraction; show implemented stories only".

### Internal

- Schema sync: regenerated `.specflow/schema/` from templates so `id_format` is `\d{3,5}` project-wide.
- Verification-gate step ordering: execute skill Step 6 (Validation) now runs the verification-gate delta before the exit/handoff message.
- Discover skill: records thinking techniques actually applied to each REQ via `update --thinking-techniques`.
- 11 new tests for source-scope engine (`test_source_scope.py`): gitignore respect, include allowlist, exclude denylist, extensions, orphan denominator clamping.
- 1 new test for duplicate-warning crash regression (`test_blocking_duplicate_renders_warning`).
- Skill templates synced to prevent drift (live ↔ ship parity confirmed for all 5 changed skills).
- Total: **521 tests passing**.

## [1.9.3] - 2026-06-14

### Highlights

- **Adoption rewritten around the component (D-20).** Brownfield code is now linked to specs via **ARCH/DDD `output_files` globs** — one ARCH per component, a package glob covering hundreds of files in a single entry. **STORY is reserved for forward action** and is no longer backfilled, eliminating the zombie-story problem on large repos. The default huge-repo strategy is **skeleton-first**: one ARCH per component across the whole project, then `specflow adopt status` flags which components deserve REQ/DDD deepening.

### Features

- **`specflow adopt status`** — adoption completeness, derived from the graph (no state file). Project/boundary dashboard (coverage %, per-ARCH depth + drift) and per-artifact view (realization, acceptance criteria, verification, provenance, gaps, drift). Available with the `adoption` pack.
- **`output_files` globs are now a core feature** (`lib.files.expand_output_files`). Literal paths and `**` patterns both work; the orphan meter, `reconcile`, and the source-drift lint check all expand globs through one shared helper, so a package glob in any artifact is honored uniformly.
- **Orphan meter credits ARCH/DDD** in addition to STORY/REQ (D-20 code-linking model). Lean (ARCH-only) adoption now moves the coverage meter.
- **`specflow brief` Adoption section** — gated on `backfilled` tags; shows coverage %, backfilled counts by type, biggest un-adopted cluster, and a pointer to `adopt status`. Greenfield projects pay zero cost (the section is omitted).
- **`specflow detect orphan-code` enhancements** — coverage % display, biggest un-adopted cluster hint, `--retro-link` now accepts any artifact ID (STORY/ARCH/DDD/REQ).
- **`retro-link` accepts any artifact type** (was hardcoded to STORY) — the usual target is now the adopting ARCH.

### Fixes

- **Globs no longer silently skipped** by `reconcile`, the source-drift lint, and the output-files existence check. Before this, a package glob in `output_files` was invisible to all three — adopted ARCHs with globs were never drift-checked, never credited as reconcile evidence, and globs matching nothing were never surfaced.
- **Skill/concept drift fix in the adoption pack**: the old Phase-5 reference to `specflow reconcile` for "confirming backfilled STORY statuses match reality" was incorrect — `reconcile` only promotes approved STORYs and ignores backfilled ones. Replaced with `specflow adopt status` (the completeness view), which is a real adoption signal.
- **V-level-aware depth in `adopt status`** — REQ no longer shows "missing parent spec" (it IS the top of the V); DDD no longer asks for a child DDD.

### Documentation

- New decision **D-20** (adoption links code via ARCH/DDD; STORY reserved for forward action; `output_files` globs are core; completeness is derived from the graph).
- `docs/architecture.md`: new "Code Realization (D-20)" section + updated `detect orphan-code` row + `adopt status` row in the commands table.
- `docs/cli-reference.md`: new `specflow adopt status` section + `detect orphan-code` notes on glob support and coverage %.
- `docs/getting-started.md` brownfield section: updated for ARCH-per-component code-linking + skeleton-first.
- Adoption pack `pack.yaml` 0.1.0 → 0.2.0; `SKILL.md` and 4 references rewritten for D-20; pack `context_snippet` updated.

## [1.9.1] - 2026-06-09

### Highlights

- **Disciplined relationships.** The link-role vocabulary stays deliberately frozen and behavior-paired (D-18); instead of adding roles, drift now gets *named and corrected*. Unknown link roles lint to a direction-aware suggestion, lifecycle gets real terminal statuses, and `specflow trace` is the documented answer to "what points at X?" — no inverse roles, no dead vocabulary.

### Features

- **Role normalizer** (`lib/role_normalize.py`) — `artifact-lint` enriches the "Unknown link role" warning with a canonical suggestion: synonyms (`validates`→`validated_by`, `extends`→`refined_by`), inverse roles (`superseded_by`→author `supersedes`, or query `specflow trace`), and lifecycle "roles" that are really statuses (`cancels`→`status: cancelled`). Still a warning, never a blocker.
- **Terminal lifecycle statuses** — `cancelled` (terminated, no replacement) and `deprecated` (discouraged) added to requirement/architecture/detailed-design/story schemas; `cancelled` added to decision alongside the existing `superseded`. Lifecycle is modeled as status, not as link roles.

### Fixes

- **Terminal-status hierarchy guard** — `validate_status_hierarchy` no longer lets a `cancelled`/`deprecated`/`superseded` child block its parent from `verified`, and skips ordering comparisons against a retired parent. Without this, cancelling one child story would permanently block the parent from being marked verified.
- **Dashboard status distribution** — `specflow status` now surfaces `superseded`/`deprecated`/`cancelled` counts instead of silently omitting them.

### Documentation

- New decision **D-18** (frozen, behavior-paired link-role vocabulary); link-role and architecture docs document "inverses are queries, lifecycle is status"; resolved the `mitigates`/`satisfies` doc-vs-schema mismatch (noted as pack-contributed). Status-lifecycle reference now covers `superseded`/`cancelled`/`deprecated`.

### Tests

- 18 new role-normalizer tests (synonym/inverse/lifecycle + enriched-lint integration) and 4 status-hierarchy regression tests for terminal states. Total: 434 passing.

### Known limitations

- ReqIF export still coerces `cancelled`/`deprecated` to `draft` (ReqIF has no equivalent state); round-trip fidelity for terminal statuses is unchanged.

## [1.8.1] - 2026-06-07

### Highlights

- **`specflow refresh`** — Update skills, agent-context, schemas, and checklists without full re-init. Supports `--dry-run` preview, selective skips (`--no-skills`, `--no-context`), and `--force` schema overwrite.
- **Two new artifact-lint checks** — `spike-lifecycle` (stale/zombie/repeated-topic detection for SPIKEs) and `source-drift` (fingerprint-based output-file change detection with auto-seeding on first run).

### Features

- `specflow refresh` command — idempotent skill/context/schema/checklist updates; properly guarded `--dry-run` that never writes or deletes; legacy directory cleanup only on live run
- `artifact-lint --type spike-lifecycle` — detects stale SPIKEs past their timebox, zombie SPIKEs with substantive findings but no downstream links, and repeated-topic patterns (3+ SPIKEs sharing a tag); ISO 8601 datetime parsing with timezone awareness
- `artifact-lint --type source-drift` — stores SHA256 fingerprints of declared `output_files` in `.specflow/source-fingerprints.yaml`; auto-seeds on first run; warns on drift unless artifact is already suspect-flagged; skips glob patterns and missing files

### Fixes

- SPIKE `created` field parsing now tries `datetime.fromisoformat` first (handles `2024-01-01T00:00:00Z` and `+00:00` offsets) before falling back to `%Y-%m-%d` — previously ISO timestamps caused a silent skip
- Removed dead `config_lib` import and unused `_hash_file` helper from refresh.py
- Legacy-directory `rmtree` now guarded behind `dry_run` check in `_install_skills`
- Source-drift docstring corrected (removed misleading `--fix` re-seed claim; users should delete `.specflow/source-fingerprints.yaml` to re-seed)

### Tests

- 11 new tests: 3 refresh (dry-run, --no-skills, schemas), 5 spike-lifecycle (stale, ISO timestamp, zombie, healthy, repeated-tag), 3 source-drift (seed, drift detection, suspect exemption)
- 7 new CLI hardening tests: `autoresearch log --set`, JSON number parsing, malformed `--set` error, nonexistent loop error, plan/run/review via `cli.main`
- Total: 445 tests passing

## [1.8.0] - 2026-06-07

### Highlights

- **SpecFlow as memory, made real.** New `specflow brief` gives a one-call deterministic recall digest (phase, inventory by category/status, open suspects, next wave, recent changes) so a fresh agent reconstructs project state in one command instead of a six-command ritual. The four-axis memory model (semantic/episodic/temporal/relational) is documented in the always-loaded context.
- **Suspect → DEF pipeline, end to end.** New `specflow defect-from-suspect <ID> --req <REQ>` creates a defect with full traceability (`fails_to_meet` → REQ, `exposed_by` → the suspect artifact), registered in the index. The helper now routes through `create_artifact` (indexed, fingerprinted, schema-validated) instead of a hand-rolled writer.
- **Approval gates that let the human be lazy *safely*.** The approval-presentation format now requires a per-change Risk Profile — reversibility, blast radius (via `specflow change-impact`), and an AI confidence signal — plus risk-proportional tiers (0 light / 1 normal / 2 stop) derived from intrinsic change properties (never from approval history). "No self-approval" is enforced and scoped to the agent.
- **Two ways to drive, one engine.** SpecFlow is positioned as a single engine: AI-first (the default) and a standalone ALM (CLI/CI, no API key). New two-lane lifecycle flowchart (Mermaid + ASCII).

### Features

- `specflow brief` — one-call recall digest (`--since` window for recent changes)
- `specflow defect-from-suspect` — suspect → DEF with auto-linked traceability
- `story-linkage` lint check — every STORY must link to a REQ/ARCH/DDD (draft = warning, beyond draft = blocking); SPIKEs exempt as standalone research
- Risk-proportional approval gates and per-change Risk Profile in `specflow-references/references/approval-presentation.md`; wired into plan/execute/ship/artifact-review and discover
- Four-axis memory model + recall-first guidance in `agent-context.md`

### Fixes

- `create_defect_from_suspect` now uses `create_artifact` — previously hand-rolled, so suspect-derived DEFs were not registered in `_index.yaml` and had a mismatched link role
- `approval-presentation.md` reference path corrected across 4 skills (moved into `specflow-references/references/`)
- discover: lean path no longer silently auto-approves — it now presents a Tier 0 summary and approves only on confirmation; Step 6.5 uses the approval-presentation format (reconciles the new no-self-approval rule)
- `__version__` corrected `1.6.4` → `1.8.0` (it is stamped into scaffolded project configs as the framework version)
- `artifact-lint --type` choices aligned with the runner (`thinking-techniques`, `autoresearch-logging`)

### Documentation

- "Two ways to drive, one engine" framing in `README.md` and `docs/getting-started.md`
- `docs/lifecycle.md`: two-lane flowchart (Mermaid primary + ASCII fallback); fixed the 10-vs-9 command-table mismatch (added `/specflow-adapter`)
- `docs/cli-reference.md`: cataloged `brief` and `defect-from-suspect`

### Notes

- **Behavior change:** the status-cascade "STORY beyond draft linked to a draft spec" condition is now **blocking** (was advisory) and is enforced in the planning-to-executing gate. Upgrading projects with pre-existing drift will see this surface — remedy: approve/implement the upstream specs (or convert the work to a SPIKE).
- **Known limitation:** there is no lightweight command yet to refresh `agent-context.md`/skills in an existing project after upgrading the framework; re-run `specflow init` to re-sync. Tracked as a follow-up.

## [1.7.3] - 2026-06-02

### Highlights

- **Autoresearch methodology depth (22 BPs)** — expanded `methodology-handbook.md` with four new groups: validation integrity (split-first preprocessing, adversarial validation, out-of-fold meta-steps), statistical traps (multiple comparisons, dimensionality as a modeling concern, distribution shift, Simpson's paradox), optimize-the-real-objective (eval-metric post-processing, calibration, multi-output decomposition), and finishing moves (diverse ensembling, seed averaging, pseudo-labeling). Added a Kaggle transfer filter and a bias catalog. Wired into EDA checks and Phase-2 ideation so BPs are consulted live.
- **Escalation / Permanence Test** — new heuristic in the always-loaded context so the agent recognizes when throwaway SPIKE/STORY work has become durable and should be promoted to REQ/ARCH/DDD (or a research COMP). Uses situational trigger wording ("when work outgrows a one-off answer"). New `escalation-and-promotion.md` recipe with worked examples and `derives_from` lineage. Cross-linked from execute Step 1 and discover readiness check.
- **Skill template freshness sync** — synced shipping templates from the live dogfood layer, fixing drift across all 10 core skills. Relocated `adversarial-lenses.md` to shared `specflow-references/` directory. Added `ddd-selection.md` to plan references.

### Features

- `methodology-handbook.md`: 22 best practices (BP-01 mandatory, BP-02–22 advisory) with anti-patterns, domain fit gates, and bias catalog
- `escalation-and-promotion.md`: SPIKE→spec promotion recipe with `derives_from` lineage tracking
- `agent-context.md`: Permanence Test with situational trigger ("when work outgrows a one-off answer")
- `specflow-references/references/adversarial-lenses.md`: shared 16-lens catalog used by discover, plan, execute, artifact-review, audit, and change-impact-review

## [1.7.2] - 2026-05-31

### Highlights

- **Post-review fixes** — 9 fixes from adversarial review: missing gate block in change-impact-review, orphan exclude dirs, escape hatch wording consistency, guard wording standardization, step numbering, agent-context escape hatch, orphan exit code, Phase 0.6/BP-01 cross-references, reference description consistency.

### Fixes

- Missing gate block in `specflow-change-impact-review` SKILL.md
- Orphan code detection: exclude dirs not being respected
- Escape hatch wording standardized across all skills
- Guard wording consistency in autoresearch loop protocol
- Step numbering consistency in execute and discover
- Phase 0.6 / BP-01 cross-reference clarity in loop protocol

## [1.7.1] - 2026-05-31

### Highlights

- **Cross-platform skill export** — `specflow export --skills --format <fmt> --output <dir>` converts all 10 SpecFlow skills to platform-specific formats: `cursor-rules` (.mdc for Cursor), `gemini-toml` (TOML commands for Gemini CLI), `codex-agents` (TOML agents for Codex), `markdown` (plain rules for Windsurf, Cline, Roo, and others).
- **Dogfooding** — DEC-052, DEC-053, DEC-054 created retroactively for v1.6.6, v1.6.7, and v1.7.0 changes. The SpecFlow framework now traces its own evolution.

### Features

- `src/specflow/lib/skill_export.py` — `export_skills()` supports 4 target formats with per-format converters
- `specflow export --skills --format cursor-rules|gemini-toml|codex-agents|markdown` — CLI interface
- `specflow export` now shows both artifact and skill export options in help

### Changes

- `export_cmd.py`: added skill export path alongside existing artifact export path
- DEC artifacts: DEC-052 (v1.6.6 context/routing), DEC-053 (v1.6.7 protocol hardening), DEC-054 (v1.7.0 multi-agent/orphan detection) — all with review_status: reviewed, linked to parent AUD artifact

## [1.7.0] - 2026-05-31

### Highlights

- **Multi-agent patterns in core skills** — artifact-review gets parallel adversarial lens fan-out for deep reviews; plan gets parallel ARCH candidate generation (3 decomposition seeds); audit lens fan-out now scales with error count (2-5 subagents); change-impact-review fans out per artifact type group for large impact cones (6+ artifacts). All patterns have conditional guards and sequential fallbacks.
- **Orphan code detection** — `specflow detect orphan-code` scans all source files and reports which are not referenced by any STORY/REQ's `output_files`. `--retro-link STORY-NNN` retroactively links all orphan files to an existing story.
- **Pre-commit hook hardened** — now blocks on link integrity failures and schema validation errors (in addition to existing RBAC checks). Suspect flag warnings on commit.
- **RBAC pre-check in execute gate** — execute Step 1 now checks team authorization before implementation, surfacing RBAC failures as warnings.
- **Protocol integrations reference** — new `protocol-integrations.md` maps all producer-consumer relationships: COMP→LOOP, LOOP→EXPT, EXPT→FIND, cross-loop feedback, skill-to-protocol mapping, and cross-cutting concerns.

### Features

- `specflow-artifact-review`: Step 5b — Deep Review with Parallel Lenses (triggered by safety/security/compliance tags, high-priority REQs, or user request)
- `specflow-plan`: Step 2.5 — Parallel Architecture Candidate Generation (domain-driven, technical-layers, risk-first decomposition seeds)
- `specflow-audit`: Step 2 — error-driven lens fan-out (standard 2 agents, elevated 3-4, critical 4-5 + synthesis agent)
- `specflow-change-impact-review`: Step 3 — blast-radius fan-out (standard sequential, elevated per-type groups, critical per-artifact + synthesis)
- `specflow detect orphan-code` — scans source files for SpecFlow traceability. `--retro-link` flag for batch retroactive linking.
- `src/specflow/lib/orphans.py` — `find_orphan_code()` and `retro_link()` functions
- `references/protocol-integrations.md` — comprehensive producer-consumer map across all autoresearch protocols and core skills

### Changes

- Pre-commit hook (`hook.py`): added link integrity check (blocking), schema validation (blocking), suspect flag warnings
- Execute gate: added RBAC pre-check (Step 1 item 6)
- Autoresearch SKILL.md: added protocol-integrations.md to references

### Deferred to v1.7.1

- Skill chaining via artifact state machine
- Protocol compliance checks in audit
- Cross-platform skill export (`specflow export --format`)
- Execute wave parallelism (requires file-level dependency analysis)

## [1.6.7] - 2026-05-31

### Highlights

- **Mandatory initial EDA** — new Phase 0.6 in autonomous-loop-protocol runs once at LOOP start: 4 universal data-quality checks + domain-specific checks. Fatal problems cause hard stop. Skip rule if prior LOOP's EDA covers same COMP with unchanged data.
- **Prior-LOOP review** — new Step 0b reads the last LOOP's full state (EXPTs, failure clusters, condensation briefs, trajectory) before formulating the first iteration. Cross-references FINDs against raw LOOP evidence.
- **LOOP post-mortem** — `lessons_learned` and `looplevel_findings` fields capture process knowledge (ranked categories, persistent dead ends, sensitivity discoveries, noise floor) before FIND authoring.
- **EXPT design quality rubric** — Phase 6.6 rates every EXPT 1-4 (Invalid→Definitive) and extracts a lesson regardless of outcome. Auxiliary signal check catches buried metrics (primary flat, secondary moving).
- **Cross-EXPT pattern detection** — finding-generation-protocol now detects synergistic/antagonistic category pairs, progression shapes, negative-space analysis, and design quality trends.
- **Auxiliary metric synthesis** — systematic analysis of auxiliary metrics: correlation with primary, trend detection, breakpoint detection. Mandatory cross-loop synthesis triggers (2+ LOOPs, 3+ LOOPs, stale low-confidence FINDs).
- **Graded post-check consequences** — minor/moderate/severe tiers replace binary pass/fail. Severe post-check failures flag `deployability: not_deployable`.
- **Supporting protocol hardening** — noise-handling gets EXPT validity gate (4 checks before strategy selection), crash-recovery gets pre-recovery telemetry extraction, methodology BP-01 elevated from advisory to mandatory.

### Changes

- `autonomous-loop-protocol.md`: 8 additions — Step 0b (prior-LOOP review), Phase 0.6 (mandatory EDA), Phase 2d strengthened to structured 3-item gate, Phase 6.5 graded post-check consequences, Phase 6.6 (EXPT postmortem + design quality rubric), LOOP post-mortem before FIND authoring, condensation briefs persisted on LOOP, tracking fields (eda_completed, eda_summary, condensation_brief_N).
- `finding-generation-protocol.md`: 3 additions — Cross-EXPT Pattern Detection (interaction detection, progression shapes, negative-space analysis, design quality trends), Auxiliary Metric Synthesis (correlation, trend, breakpoint), Mandatory Cross-Loop Synthesis Triggers (5 trigger conditions).
- `noise-handling-protocol.md`: EXPT Validity Gate inserted before strategy selection (4 checks: execution integrity, parameter validity, data integrity, baseline comparability).
- `crash-recovery-protocol.md`: Pre-Recovery Telemetry Extraction inserted (5 steps: identify successful steps, capture crash signature, log partial results, record crash_telemetry, then apply recovery).
- `methodology-handbook.md`: Header changed from "Advisory only" to "BP-01 is mandatory." BP-01 tagged `[MANDATORY]` with enforcement reference.

## [1.6.6] - 2026-05-31

### Highlights

- **Injected context rebalanced** — `agent-context.md` rewritten with 4:1 core-to-pack ratio (was 0.6:1), routing section, and "Stop. This is a SpecFlow project." priming. Autoresearch `context_snippet` reduced from 30 lines to 6-line routing stub with anti-triggers.
- **Graduated skill trigger strength** — all 10 skill descriptions rewritten with feature-request bridging, anti-triggers, and graduated obligation levels. Execute is now DEFAULT for all code changes; discover bridges natural language ("add X," "build Y").
- **Standardized gate vocabulary** — `blocking`/`warning`/`info` severity language and articulated escape hatches added to all 6 operational skills and AGENTS.md.
- **Multi-agent platform safety** — 5 subagent spawn locations in autoresearch now guarded with "if your platform supports it" + sequential fallback paths.

### Changes

- `agent-context.md`: rewritten from 24 lines to 28 lines with routing section, pack anti-triggers, graduated obligation. Ratio shifted from 0.6:1 to ~4:1 core:pack.
- `autoresearch/pack.yaml`: `context_snippet` reduced from 30 lines to 6-line routing stub — defers operational detail to on-demand SKILL.md.
- All 10 skill descriptions: graduated strength (DEFAULT → Obligation → Standard → Specialized), anti-triggers on 8 skills, feature-request bridging on discover.
- All 6 operational SKILL.md files: gate severity vocabulary + articulated escape hatch ("Proceeding past [item]. Risk: [risk]. Noted.").
- `specflow-execute` Step 1: binary "never skip" replaced with graduated obligation table (5 change types with minimum bars), suspect-flag sweep made `blocking`.
- `specflow-plan` Step 1: "Optionally" removed — gate runs by default.
- `AGENTS.md` L108: silent skip → articulated skip with risk statement.
- `specflow-init` Step 4: updated to reflect CLI auto-injection (was stale).
- `specflow-autoresearch/SKILL.md`: 5 subagent spawn locations now guarded + sequential fallback paths.

### Fixes

- **Routing gap**: feature requests ("add a login page") now route to discover instead of straight to code.
- **Review collision**: audit/artifact-review/change-impact-review now have mutual anti-triggers.
- **Silent bypass**: escape hatches preserved but now produce an accounting record.
- **Platform fragility**: unconditional subagent spawn instructions in autoresearch now have fallbacks for Windsurf and Junie.

## [1.6.5] - 2026-05-30

### Highlights

- **CLI-driven instruction injection** — `specflow init` now deterministically injects the base SpecFlow context block into the platform's instruction file (AGENTS.md, CLAUDE.md, etc.) using idempotent HTML-comment sentinels. No more manual copy-paste by the agent.
- **Multi-preset support** — `--preset` accepts comma-separated packs (e.g., `--preset autoresearch,tldr-communication`). Each pack's context snippet is injected as an independent sentinel block.
- **Condensed base context** — `agent-context.md` reduced from ~90 lines to 24 lines while retaining all functional rules (V-Model, status lifecycle, traceability, cascading).

### Features

- `scaffold.inject_base_context()` — new function that reads `agent-context.md` and appends it to the instruction file with `<!-- SpecFlow section -->` sentinel markers. Handles create, append, update, and idempotent no-op.
- `scaffold._get_target_instruction_file()` — shared helper resolving the correct instruction file per platform, with CLAUDE.md/GEMINI.md fallback.
- `--preset` flag in `specflow init` now splits on commas and applies each pack sequentially.
- `inject_pack_context()` accepts `explicit_platform` parameter, fixing a timing bug on fresh repos where platform detection returned `None`.

### Changes

- `agent-context.md` trimmed from ~90 lines to 24 lines (removed redundant tables, tutorial text, docs links).
- `specflow-init` SKILL.md step 4 (manual injection) removed — the CLI now handles this deterministically.
- Base context is always injected before pack context, ensuring consistent ordering in the instruction file.

## [1.6.4] - 2026-05-29

### Highlights

- **Status cascade automation** — new `specflow cascade-status` and `specflow reconcile` commands automate the previously manual process of propagating STORY status to linked ARCH/DDD/REQ artifacts and detecting stories with implementation evidence.
- **Status-cascade lint check** — `artifact-lint` now warns when a STORY is `implemented`/`verified` but linked ARCH/DDD still sits at `approved`, catching status drift before it compounds.

### Features

- `specflow cascade-status STORY-NNN` — one-liner to propagate `implemented`/`verified` status to linked ARCH (via `guided_by`), DDD (via `specified_by`), and optionally REQ (via `--include-req`). Dry-run support with `--dry-run`.
- `specflow reconcile` — auto-detects approved stories with implementation evidence (output files on disk or git commits referencing the story ID), promotes to `implemented`, and optionally cascades. Dry-run support with `--dry-run`, cascade control with `--no-cascade`.
- `status-cascade` lint check in `artifact-lint` — warns when STORY is `implemented`/`verified` but linked ARCH/DDD is still `approved`, or when STORY is `verified` but linked REQ is still `approved`. Non-blocking (warnings only). Actionable message suggests `specflow cascade-status`.
- Both new commands registered in CLI dispatch table and help epilog (`Execute` phase).

### Fixes

- `executor.py` no longer prematurely calls `update_artifact(status="implemented")` during wave execution. Wave commit messages now say "wave N prepared" instead of claiming implementation.
- `specflow-execute` SKILL.md (both `.claude/skills/` and `templates/skills/`) Step 4 now uses `cascade-status` instead of manual per-artifact updates.
- `agent-context.md` strengthened with explicit 2-step status update instruction (update + cascade-status) for both `/specflow-execute` and ad-hoc sessions.

### Changes

- Autoresearch SKILL.md: Post-Loop section clarified that delegate-review subagent creates FINDs (not the main agent). Added lifecycle flow diagram. Updated rules.
- `docs/plan-autoresearch-integration.md`: learning flow diagram updated to reflect delegate-review subagent pattern.
- `_HELP_EPILOG` in `cli.py` updated to list `cascade-status` and `reconcile` under Execute phase.

## [1.6.0] - 2026-05-16

### Highlights

- **Autoresearch pack v0.2.0** — autonomous research loops are now harness-agnostic. Any LLM harness (Claude Code, Cursor, scripted CI) can drive the iteration loop through a single `specflow autoresearch` CLI subcommand instead of platform-specific skills.
- **Multi-criteria competitions** — competitions now support a primary metric for ranking, binary guards for hard floors, and freeform auxiliary metrics for post-hoc analysis. Documented patterns for leakage prevention and anti-gaming as recommendations, not mandates.
- **Pack context injection** — installed packs now write a sentinel-bracketed context block into the project's platform instruction file (e.g. `AGENTS.md`) on `specflow init --preset <pack>`, giving the host agent the right vocabulary without requiring per-platform skill variants.

### Features

- `specflow autoresearch plan|run|review|leaderboard` CLI subcommand (`src/specflow/commands/autoresearch.py`)
  - `plan`: prints setup-gate checklist for a competition, optional `--profile` for 3x noise variance probe
  - `run`: prints the 8-phase iteration protocol with current LOOP progress (harness drives the loop; this command does not embed a model client)
  - `review`: shows FINDs, top kept EXPTs with auxiliary metrics, and loop history
  - `leaderboard`: ranks kept EXPTs by primary metric, supports `--all` for cross-COMP view
  - Multi-COMP repos: auto-detects single active COMP, prompts when ambiguous, `--competition COMP-NNN` to disambiguate
- `auxiliary_metrics` optional field on EXPT artifacts — freeform YAML dict for post-hoc enrichment (max_drawdown, total_trades, win_rate, runtime_seconds, etc.) that does not affect the kept/discarded decision
- `inject_pack_context()` library function and `context_snippet` field in `pack.yaml` — packs declare a markdown snippet that gets injected into the platform's instruction file with idempotent sentinel markers (`<!-- pack:<name> context ... -->`)
- `instruction_file` field on all 14 platforms in `templates/platforms.yaml` — points pack context injection at the right file per harness (AGENTS.md, .cursor/rules/specflow.md, .github/copilot-instructions.md, etc.)
- "Multi-criteria competitions" section in `competition-setup-protocol.md` explains primary metric / guards / auxiliary metrics with a worked quant example and a strictness ladder
- "Leakage and Gaming" section documents read-only eval data patterns, one-number verify output, and robustness-adjusted primaries as recommendations
- Anti-gaming pointer in `autonomous-loop-protocol.md` Phase 5 + auxiliary metrics logging guidance in Phase 7 with domain-specific examples (quant, ML, NLP, systems)
- `specflow init --preset autoresearch` now writes a `<!-- pack:autoresearch context -->` block into the detected platform's instruction file
- 12 new tests in `tests/test_autoresearch_pack.py`: 7 CLI subcommand tests (`TestAutoresearchCLI`), 3 context-injection tests (`TestPackContextInjection`), 2 auxiliary-metrics schema tests

### Fixes

- `inject_pack_context()` is now actually called from `_apply_preset` in `init.py` — previously the function existed but no production code invoked it, leaving pack context injection as dead code
- `specflow autoresearch leaderboard --all --competition COMP-X` now errors out instead of silently letting `--all` win
- `src/specflow/__init__.py` `__version__` bumped from stale `1.2.0` to `1.6.0` to match `pyproject.toml`

### Documentation

- `SKILL.md` for the autoresearch skill thinned to reference CLI backends instead of inlining full protocol; safety posture, anti-patterns, principles, and rules sections preserved
- Subcommands table maps each `/specflow-autoresearch:*` skill invocation to its `specflow autoresearch <sub>` CLI backend
- Phase 7 logging examples in `autonomous-loop-protocol.md` now demonstrate `--auxiliary-metrics` JSON dict invocation

## [1.6.3] - 2026-05-25

### Highlights

- **Goal-driven research ladder** — autoresearch now treats experiments as evidence under a tiered hierarchy of Goals → Theses → Research Questions → Hypothesis → EXPT → Parameters. The ladder is walked once at LOOP creation; per-iteration the agent stays goal-mindful via a 3-question self-assessment that prevents parameter-wandering and sunk-cost on the wrong axis.
- **Protocol split** — `autonomous-loop-protocol.md` trimmed (839 → 758 lines) by extracting `noise-handling-protocol.md` (Phase 5.1 strategies) and `crash-recovery-protocol.md` (verify-failure and session-crash rules) into dedicated reference files, reducing per-iteration context tax.
- **Pre/post-EXPT mindfulness** — consolidated Phase 2d (premise check before running the EXPT) and Phase 2e (no blind parameter sweeps; collapse sweeps into one EXPT with a local script) into cleaner, less redundant rules. Dynamic post-check guidance for deep failure analysis on strongly-reasoned-but-failed EXPTs.
- **Constraints as a first-class field** — `COMP.constraints` captures forbidden data/techniques (e.g. "no pre-trained weights", "no transformers library") so the agent doesn't propose solutions that violate the user's implicit rules.

### Features

- `COMP.theses` (list of strings) — durable, cross-loop research agenda
- `LOOP.active_research_questions` (list of strings) — loop-scoped operationalization of theses
- `COMP.constraints` (string) — rules of engagement (forbidden data, libraries, techniques)
- `EXPT.research_question` (string) — links the EXPT back to the active RQ it serves
- `references/noise-handling-protocol.md` — strategy menu for volatile metrics (multi-run, confirmation, env pinning, min-delta)
- `references/crash-recovery-protocol.md` — recovery rules for verify failures and session crashes
- `competition-setup-protocol.md` Step 6.6 (constraints) and Step 6.7 (theses elicitation)
- FIND authoring template asks for the `COMP.theses` entry each finding supports, refutes, or refines — closes the evidence loop across LOOPs
- Proactive enforcement loops in `specflow-plan`, `specflow-execute`, `specflow-discover` skills — BPs are now actively audited against, not passively read; decomposition + sanity checks suggested before monolithic implementation; anti-requirements elicited during discovery

### Changes

- Phase 2a rewritten as a goal-mindfulness check (3 quick questions) rather than a full ladder rewalk per iteration — the heavy lift lives in Setup Gate
- Phase 5.1 (noise handling) and Crash Recovery sections in the main protocol replaced with one-line pointers to their dedicated reference files



### Highlights

- **7 new research thinking lenses** — `leakage_audit`, `overfitting_multiple_comparisons`, `baseline_sanity`, `distribution_shift`, `ablation_attribution`, `metric_validity`, and `reproducibility` added to the adversarial catalog. Research artifacts (COMP, LOOP, EXPT, FIND) get per-level default lens sets selected automatically by `artifact-review --depth deep`.
- **Concise prompts** — ~800 tokens saved across the 23-lens catalog by extracting repeated JSON/boilerplate into a single `_GENERIC_LENS_SUFFIX` injected at runtime.
- **Atomic EXPT logging** — `specflow autoresearch log` creates an EXPT artifact and auto-updates LOOP counters (`iteration_count`, `kept_count`, `discarded_count`, `best_metric`) in one CLI call, replacing the error-prone two-step `create` + `update` sequence.
- **Deterministic FIND drafting** — `specflow autoresearch suggest-finds` groups EXPTs by `change_category`, synthesizes `what_worked` / `what_failed` / `next_steps`, and either prints a draft or writes a FIND artifact with `--write`. Zero LLM tokens.
- **Subagent guidance in SKILL.md** — explicit instructions for spawning parallel subagents per `change_category` during FIND synthesis, and per-strategy-family in `family_of_good` competitions, to keep context windows small.

### Features

- `LENS_CATEGORIES` three-way taxonomy (`software`, `research`, `both`) with `ARTIFACT_LEVEL_DEFAULT_LENSES` mapping artifact types to appropriate lens sets
- `_prompt_for_techniques()` now detects mixed research+software artifact reviews and falls back to `both`-category lenses only, preventing `leakage_audit` from running on user stories
- `autoresearch log` CLI subcommand with `--loop`, `--status`, `--metric-value`, `--change-category`, `--summary`, `--title`, `--set KEY=VALUE`, and `--no-update-loop` flags
- `autoresearch suggest-finds` CLI subcommand with `--loop` and `--write` flags
- Passive-CLI banner on `autoresearch run` — prints a one-line reminder that the AI agent drives the loop, not the CLI
- "Coexisting with External ML Trackers" section in `competition-setup-protocol.md` — documents integration pattern with MLflow, Weights & Biases, Neptune, MLRun, etc.
- Updated `pack.yaml` `context_snippet` to advertise `log` and `suggest-finds` commands
- 13 new tests in `tests/test_autoresearch_pack.py`: 4 mixed-review / conciseness tests (`TestResearchThinkingLenses`), 4 smoke tests for `log` and `suggest-finds` (`TestAutoresearchLogAndSuggestFinds`)

### Fixes

- Mixed-artifact review bug where `artifact-review --all --depth deep` on a project with both software and research artifacts could apply research lenses to software artifacts

## [1.6.1] - 2026-05-20

### Highlights

- **Goal-driven, richer autoresearch** — experiments now carry `hypothesis` / `hypothesis_outcome`, `pre_check_command` / `post_check_command`, `objective_type` (`single_best` / `family_of_good` / `pareto_front`), and `domain`-aware auxiliary metric linting.

### Features

- Generic `--set KEY=VALUE` flag on `specflow create` and `specflow update` — JSON-aware, repeatable, enables arbitrary frontmatter fields (EXPT `metric_value`, COMP `goals`, LOOP `termination_suggestions`, etc.) without hardcoding CLI flags
- `hypothesis` and `hypothesis_outcome` (`supported` / `not_supported` / `inconclusive`) fields on `experiment.yaml`
- `pre_check_command` and `post_check_command` on `competition.yaml` with `checks` array on EXPT recording pre/verify/post pipeline results
- `objective_type` (`single_best`, `family_of_good`, `pareto_front`) and `goals` on COMP; `termination_suggestions` on LOOP for dynamic, goal-aware stopping
- `domain` field (`quant`, `ml`, `nlp`, `systems`, `safety_critical`) on COMP drives `artifact-lint` warnings when domain-recommended auxiliary metrics are missing from kept EXPTs
- `noise_characterization` on COMP stores variance-probe results
- `deployability` and `safety_assessment` fields on FIND
- `specflow autoresearch review` warns when completed LOOPs have zero FINDs or when discarded EXPTs lack `failure_analysis`
- `specflow autoresearch leaderboard --group-by model_origin` and `--show-family` for swarm/ensemble views
- `parameters`, `model_origin`, `sweep_results`, `diversity_metrics`, and `failure_analysis` fields on `experiment.yaml`

### Fixes

- `src/specflow/__init__.py` `__version__` bumped from `1.6.0` to `1.6.1` to match `pyproject.toml`

## [1.5.0] - 2026-05-07

### Highlights

- **Unified 16-lens adversarial catalog** — all 16 thinking technique lenses are now available in every lifecycle phase (discover, plan, execute, review, audit) via a shared reference catalog at `.claude/skills/specflow-references/`.
- **Thinking technique records on artifacts** — new `thinking_techniques` optional field on all 13 artifact types tracks which lenses were applied. New `--thinking-techniques` flag on `specflow update` appends techniques to any artifact.
- **Technique-to-BP feedback loop** — best-practice staleness checks now include challenge (CHL) artifacts; BP synthesis prompts inject recent adversarial findings so regenerated BPs learn from what lenses actually caught.
- **Audit technique granularity** — audit CHLs now carry per-axis technique names (`audit-horizontal`, `audit-vertical`, `audit-cross-cutting`) instead of the monolithic `project-audit`.
- **Generic lens fallback** — the 12 lenses without dedicated Python modules now run as generic LLM prompts using the shared lens catalog, making all 16 lenses runnable from the CLI.

### Features

- Shared 16-lens adversarial catalog with per-phase default sets and trigger-for-expansion guidance (`.claude/skills/specflow-references/references/adversarial-lenses.md`)
- `specflow update <ID> --thinking-techniques <comma-separated>` flag for recording techniques on artifacts (appends, deduplicates)
- New `thinking-techniques` lint check: warns on approved REQ/ARCH/DDD artifacts with no `thinking_techniques` recorded
- `_is_stale_against_evidence()` replaces `_is_stale_against_decisions()` — checks both DEC and CHL artifact mtimes against BP cache
- `_recent_chl_summaries()` injected into phase-level BP synthesis prompts so LLM can incorporate "what keeps getting caught"
- Per-skill `references/thinking-techniques.md` files replaced with pointers to shared catalog
- Technique recording instructions added to discover, plan, execute, and audit SKILL.md files
- `_DEFAULT_LEARNABLE_TECHNIQUES` expanded from 5 to 17 entries (all 16 lenses + checklist-run)
- `LENS_CATALOG` dict in `techniques/__init__.py` provides system prompts for all 16 lenses
- `ALL_LENS_NAMES` exported set for external validation of technique names

- Dedicated technique modules (devil's advocate, premortem, red/blue team, assumption surfacing) import system prompts from `LENS_CATALOG` instead of duplicating inline strings
- `_run_generic_lens()` fallback in `execute_technique()` runs catalog lenses without dedicated Python modules
- `run_subagents()` concurrency capped at `min(techniques × artifacts, 8)` to prevent thread pool explosion
- `_recent_chl_summaries()` rewritten: sorts by severity weight then recency, excludes accepted/stale/resolved CHLs, includes first 200 chars of rationale, defaults to 10 items
- `compose_review_prefix()` accepts `existing_techniques` parameter to render "Previously applied thinking techniques" section in review prompts
- `artifact_review.py` extracts `thinking_techniques` from target artifact and passes to `compose_review_prefix()`
- `build_phase_synthesis_prompt()` accepts `learned_patterns` parameter for learned PREV-*.yaml injection
- `_learned_patterns_text()` reads prevention patterns from `.specflow/checklists/learned/` and formats for BP synthesis
- `synthesize_and_cache()` now calls `_learned_patterns_text()` and passes results to phase synthesis prompt
- `update.py` validates technique names against `ALL_LENS_NAMES` (warns on unknown, still records)
- `specflow-discover` lean path records `lean_assessment` sentinel on auto-approved REQs to avoid lint warnings
- `specflow-change-impact-review` fixed wrong adversarial-lenses catalog path and added technique recording step
- All 13 artifact schemas updated with `thinking_techniques` as optional field
- `thinking_techniques` added to `known_meta` in lint validation whitelist

### Fixes

- Audit CHL artifacts now carry specific technique names (`audit-horizontal`, `audit-vertical`, `audit-cross-cutting`) instead of generic `project-audit`
- Fixed `_learned_patterns_text()` reading wrong field names from PREV-*.yaml patterns — uses `name`/`discovered_from` instead of `title`/`trigger`
- Added `lean_assessment` to `_SENTINEL_NAMES` in `update.py` to suppress spurious "Unknown technique" warning on lean-path REQs
- `ci.py` and `handbook.py` now forward `existing_techniques` to `compose_review_prefix()`, preventing duplicate findings on review passes through those code paths

### Tests

- 14 new tests in `test_best_practices.py` covering `_learned_patterns_text`, `_recent_chl_summaries`, and `compose_review_prefix` with `existing_techniques`
- 10 new tests in `test_artifact_lint.py` for thinking-techniques lint check (status filtering, type filtering, lean_assessment sentinel, implemented/verified statuses)
- 1 new test in `test_technique_fallback.py` for `run_subagents` concurrency cap
- 6 new tests in `test_challenges.py` for shared CHL creation module
- 7 new tests in `test_standards_get_clause.py` for `get_clause_by_id`
- 14 new tests in `test_reverse_impact.py` for glob matching, query/flag split, recursive propagation

## [1.4.1] - 2026-05-06

### Highlights

- **Read-only `change-impact` by default** — `specflow change-impact` no longer silently flags artifacts as suspect when displaying source-file matches; use `--flag` to opt into suspect flagging.
- **Recursive downstream propagation** — suspect flagging now propagates transitively through the full dependency chain (ARCH → DDD → UT), not just one level.
- **`**` recursive glob support** — `output_files` patterns with `**` (e.g., `src/**/*.py`) now correctly match files in nested subdirectories.
- **Converged CHL creation** — duplicated `_create_chl_artifacts` logic in `project_audit.py` and `artifact_review.py` replaced with a single shared module (`specflow/lib/challenges.py`).
- **Per-suspect resolution** — `resolve_suspect` now tracks resolution per individual suspect within an event, rather than resolving the entire event when one artifact is resolved.

### Fixes

- `reverse_impact` split into `query_reverse_impact` (pure query, no file mutation) and `flag_suspects_from_matches` (mutation only); `reverse_impact` kept as backward-compatible wrapper
- `_find_all_downstream_recursive` added for transitive suspect propagation via BFS
- `_glob_match` replaces raw `fnmatch` calls, supporting `**` recursive glob patterns with proper regex conversion including trailing/standalone `**`
- `resolve_suspect` tracks `resolved_suspects` list per impact-log event; event only resolves when all suspects are individually resolved
- Stale pseudocode in DDD-005.md ("Challenge Deduplication") updated to reflect converged implementation
- DDD-019.md updated to document `query_reverse_impact`, `flag_suspects_from_matches`, `_glob_match`, and `--flag` CLI option
- ROADMAP.md "v1.x (Future)" section cleaned — removed "Review workflow artifacts" and "Compliance evidence quality" (both shipped in v1.4.0)
- Raw ANSI escape sequences in `change_impact.py`, `project_audit.py`, and `artifact_review.py` replaced with `specflow.lib.display` constants

### Internal

- New `specflow/lib/challenges.py` — shared `create_chl_artifacts()` accepting `TechniqueFinding` objects with configurable `link_role`, `dedup`, `review_id`, and `technique_override`
- `project_audit.py` converts its `list[dict]` findings to `TechniqueFinding` and calls shared module with `link_role="refers_to"`, `dedup=True`
- `artifact_review.py` delegates to shared module with `link_role="challenges"`, `dedup=False`
- `cli.py` adds `--flag` argument to `change-impact` subcommand
- 30 new tests: 9 for glob matching (including trailing/standalone `**`), 3 for query/flag split, 2 for recursive propagation, 6 for shared challenges module, 7 for `get_clause_by_id`, 1 for zero-keyword clause edge case, 2 for trailing `**` fix

## [1.4.0] - 2026-05-05

### Highlights

- **Compliance evidence quality** — `complies_with` links now require substantive backing content. New `compliance-evidence` lint check warns when artifacts claim conformance but have a thin body or fail to reference clause keywords. Strict mode (`lint.compliance_evidence_strict: true` in config) escalates warnings to blocking errors.
- **REVIEW artifact type** — `artifact-review` now emits a `REVIEW-NNN` artifact summarizing each review pass over a target artifact. Spawned CHL findings link back to the REVIEW via `refers_to`, and the REVIEW carries the finding summary, depth, reviewers, and consensus fields. CHLs remain the per-finding record; REVIEW captures the pass.

### Features

- New `_check_compliance_evidence()` lint check in `artifact_lint.py` with `_COMPLIANCE_MIN_WORDS=50` threshold; pulls clause keywords from `standards_lib.get_clause_by_id()` and verifies at least one keyword appears in the artifact body
- New `templates/schemas/review.yaml` registering REVIEW type with statuses (open/closed), reviewer/consensus/findings/depth fields, and `review_of`/`refers_to` link roles
- `review` registered in `TYPE_TO_DIR`/`PREFIX_TO_TYPE` (`artifacts.py`); `specs/reviews/` added to scaffold `SPEC_DIRS` so `specflow init` provisions it for new projects
- `artifact-review` exposes `emit_review_pass(root, target, findings, depth)` as a public helper; legacy CHL-only path replaced with REVIEW + linked CHLs whenever there are actionable findings
- `_bootstrap_review_schema()` ensures repos that pre-date v1.4.0 get the `review.yaml` schema and `_specflow/specs/reviews/` directory copied in on first run of `artifact-review`
- `specflow status` now displays a `Reviews:` line counting REVIEW + AUD + CHL artifacts when any are present

### Internal

- 6 new unit tests in `test_artifact_lint.py` (TestCheckComplianceEvidence) covering thin-body warning, missing-keyword warning, substantive-content pass, strict-mode blocking, unresolved-clause fallback, and no-link short-circuit
- 4 new tests in `test_review_artifact.py` covering REVIEW emission, CHL backlinks, status counting, and type registration
- `CHECK_NAMES` and CLI `--type` choices both updated to include `compliance-evidence`

## [1.3.1] - 2026-05-05

### Highlights

- **Verification gap closed** — generated UT/IT/QT triplets for REQ-022..027 / ARCH-016..021 / DDD-017..021, lifting STORY test coverage from 76% to 100% (63/63) and chain coverage from 75% to 100% (69/69)
- **Decision housekeeping** — promoted all 42 draft DEC artifacts to `approved`, eliminating the long-tail housekeeping flag from project-audit

### Internal

- 17 new test artifacts: QT-023..028, IT-018..023, UT-023..027 (linked to verifying REQs/ARCHs/DDDs and to all 15 stories STORY-049..063)
- `specflow project-audit --quick` now reports 0 vertical findings on this repo's specs
- Promoted REQ-022..027 from `approved` to `implemented` (prerequisite for test-stub generation)

## [1.3.0] - 2026-05-05

### Highlights

- **Reverse impact analysis** — source code changes now map back to spec artifacts via `output_files`, closing the bidirectional traceability loop from code to specification
- **Decomposition completeness guidance** — SPIDR dimension coverage and dependency cycle detection in `artifact-lint`, plus generic best-practice fallback for offline handbook generation

### Features

- **Reverse impact engine** — `build_output_file_index()` and `reverse_impact()` in `impact.py` map changed source files to governing artifacts via literal and glob pattern matching
- **Source File Impact section** — `specflow change-impact` now includes a "Source File Impact" section listing source file changes and their associated spec artifacts
- **SPIDR coverage lint check** — `spidr-coverage` check reports when SPIDR dimensions have no stories, ensuring decomposition coverage across all five sources
- **Wave cycle detection lint check** — `wave-cycles` check detects circular dependencies between stories and flags stories with excessive dependencies (>=4)
- **DDD selection decision tree** — new reference document `references/ddd-selection.md` with a 6-question decision checklist for determining which ARCH components need DDD artifacts
- **Generic BP fallback** — bundled generic best-practice YAML templates for `plan-arc`, `plan-ddd`, and `plan-story` phases; `specflow handbook generate` now falls back to these when no LLM API key is configured instead of failing
- **Discovery challenge persistence** — discover skill Step 5 now creates DEC artifacts for dropped requirements, surfaced assumptions, and identified risks
- **Inter-REQ dependency prompting** — discover skill Step 4 explicitly asks about inter-REQ dependencies and records them as `derives_from` links
- **Domain context pass-through** — plan skill Step 2 reads domain classification and decision artifacts from discovery
- **Improved discover-to-plan handoff** — discover skill exit message explicitly lists draft REQ IDs needing approval with the exact command to run

### Documentation

- New reference: `.claude/skills/specflow-plan/references/ddd-selection.md`
- Updated: `.claude/skills/specflow-discover/SKILL.md` Steps 4, 5, 7
- Updated: `.claude/skills/specflow-plan/SKILL.md` Steps 2, 4

## [1.2.0] - 2026-05-05

### Highlights

- **Init upgrade safety** — re-running `specflow init` on an existing project now preserves config and state via merge mode; `--force` enables clean re-init with timestamped backup
- **Specification body quality enforcement** — `artifact-lint` now validates ARCH and DDD artifacts for substantive content (word counts, structural headers), REQ-to-ARCH coverage, and minimum acceptance criteria
- **Output file traceability** — new `output_files` field on ARCH/DDD/STORY schemas with filesystem existence verification and glob pattern support

### Features

- **`specflow init` merge mode** — re-initialization preserves existing config.yaml, state.yaml, and schemas; merges new defaults with user values; reports version deltas
- **`specflow init --force`** — clean re-init with timestamped backup of config, state, and schemas to `.specflow/cache/backups/`
- **Config version stamping** — `config.yaml` now includes a `version` field tracking the SpecFlow release that wrote it
- **`spec-body` lint check** — validates ARCH artifacts for 50+ words and structural headers; DDD artifacts for 100+ words and design headers
- **`output-files` lint check** — verifies that paths declared in `output_files` frontmatter exist on the filesystem; skips glob patterns
- **Extended coverage check** — `coverage` check now also verifies approved REQs have at least one ARCH linking via `derives_from`
- **Story minimum AC check** — `story-size` check warns when stories have fewer than 2 acceptance criteria
- **`output_files` field** — optional field on architecture, detailed-design, and story schemas for bidirectional file traceability
- **`specflow update --output-files`** — set, replace, or remove `output_files` on any artifact (empty string removes the field)

### Fixes

- `specflow init --force` now correctly overwrites schemas with fresh copies (previously incremental copy left stale schemas in place)
- `specflow update` error message now mentions `--output-files` as an available flag

## [1.1.0] - 2026-05-03

### Highlights

- **Domain intelligence and learning feedback** — SpecFlow now generates domain-specific best practices via LLM, learns prevention patterns from review findings, and gives users visibility into accumulated knowledge.

### Features

- **Domain best-practice synthesis** — `specflow handbook generate` creates project-level and phase-level BP guides via LLM, cached as human-editable YAML in `.specflow/cache/best-practices/`
- **Knowledge accumulation lifecycle** — blocking/warning findings from artifact reviews are automatically converted into `PREV-*.yaml` prevention patterns in `.specflow/checklists/learned/`
- **`specflow patterns` command** — inspect learned prevention patterns (`list`, `show`)
- **Per-item checklist scoping** — `applies_to.types` on individual checklist items overrides top-level filter
- **Configurable learning** — `learnable_techniques` and `max_patterns_per_session` in `config.yaml`
- **Expanded learnable techniques** — adversarial findings (devil's advocate, premortem, assumption surfacing, red/blue team) now feed into learning by default
- **`--fast` flag on `artifact-review`** — skip BP synthesis for CI, use cached best practices only
- **Auto-backup on `--overwrite`** — previous BP files are backed up before regeneration
- **`specflow done` auto-extraction** — `--auto` is now the default, extracts prevention patterns from implemented stories
- **Dual few-shot examples** — phase BP prompts include both embedded and API-service examples for quality anchoring

### Fixes

- `_learnable_techniques` is now configurable (was hardcoded to `checklist-run` only)
- `specflow done` no longer shows a dead-end "requires interactive prompts" message
- Stale version in `src/specflow/__init__.py` (was `0.1.0`, now tracks release)
- Phase prompt few-shot now shows two domain examples instead of one

### Documentation

- Added `specflow patterns` and `specflow handbook` to CLI reference
- Added `--fast` flag and `--no-auto` flag documentation
- Updated install pin in README to `v1.1.0`
- Updated ROADMAP with v1.1.0 section and v1.0.1 entries
- Updated `docs/plan.md` release table

## [1.0.1] - 2026-04-23

### Fixed

- AGENTS.md template now lists all 10 skills (was missing `/specflow-adapter`)
- AGENTS.md template now includes V-model explanation, invocation routing rules, CLI-only command references, and doc pointers for deeper context
- ROADMAP no longer lists Jira/Azure DevOps sync in both v1.x and Out of Scope
- `docs/plan.md` release table updated to reflect shipped versions

### Changed

- `/specflow-init` completion message now suggests `/specflow-adapter` for CI-first teams

## [1.0.0] - 2026-04-22

### Highlights

- First stable release. Everything since v0.2.0 plus polish, stability, and adoptability improvements.

### Features

- **Unified CLI framework** — streamlined installation path, unified adapter framework, and command renaming
- **Skill ecosystem restructuring** — collapsed 22 skills into 10 core Tier 1 conversational skills
- **Shared thinking techniques** — adversarial lenses extracted into stage-specific reference catalogs for discover, plan, and execute skills, enabling "build it right the first time" rather than post-review fixes
- **Freeform skill input** — all 10 skills accept natural language context (e.g., `/specflow-audit I'm worried about REQ coverage`) for scoped, directed workflows
- **Compliance evidence reports** (`specflow baseline create --evidence`) — generates a Markdown report with traceability matrix, test results summary, baseline diff, and per-standard coverage scores
- **Enhanced standards gap analysis** (`specflow standards gaps`) — coverage scoring (0–100%), severity-sorted gap list, rule-based remediation suggestions, `--json` flag
- **Optional artifact type schemas** (`specflow init --with-types hazard,risk,control`) — installable hazard, risk, and control artifact types
- **Compliance summary in status** — `specflow status` shows per-pack compliance scores when standards are installed
- **Continuous auditing** — project audits support conversational scope and chunked fan-out
- **Convention enforcement** — project convention checklists scaffold and enforce project structure

### Documentation

- **README rewrite** — clearer visual hierarchy, concise feature table, disambiguation section for similarly-named projects
- **AGENTS.md release process** — documented CHANGELOG, git tagging, and GitHub Release workflow
- **ROADMAP updated** — v1.0.0 reflects polish focus; deferred items and out-of-scope limits documented explicitly

### Changed

- Thinking techniques (adversarial lenses) are now woven into `/specflow-discover` and `/specflow-plan` as creation-time challenges, not limited to `/specflow-artifact-review`
- `/specflow-discover` Step 5 now challenges requirements before finalizing artifacts
- `/specflow-plan` Step 4.5 now stress-tests architecture before creating artifacts
- `/specflow-execute` now includes quick thinking checks during implementation
- Skill instruction templates rewritten and unified across all 14 AI platforms
- Documentation completely overhauled to focus on the 10-command skill surface

### Fixed

- `check_compliance()` now reports `total_clauses` consistent with the score denominator
- Project audit correctly detects ARCH and DDD refinements linked via `derives_from`
- Resolved schema and traceability gaps in self-specification artifacts

## [0.2.0] - 2025-04-21

### Added

**Slash Commands**
- `/specflow-init` — Bootstrap project with auto-detected platform, skills, and optional CI
- `/specflow-discover` — Progressive disclosure conversation for requirement capture
- `/specflow-plan` — Architecture proposal, DDD creation, SPIDR story decomposition
- `/specflow-execute` — Wave-based story implementation with status updates
- `/specflow-artifact-review` — Lint + checklists + LLM judgment + adversarial lenses
- `/specflow-change-impact-review` — Blast-radius review of unreviewed change records
- `/specflow-audit` — Full-project health review with deterministic core + adversarial wings
- `/specflow-ship` — Baseline creation, DEC trail, quick audit, advisory gate
- `/specflow-pack-author` — Standards compliance pack authoring from PDF/URL/text
- `/specflow-adapter` — CI setup, exchange (ReqIF), standards ingestion, team RBAC

**CLI Commands (30 subcommands)**
- Discover: `init`, `status`, `standards gaps`
- Plan: `create`, `update`
- Execute: `go`, `done`, `generate-tests`
- Review: `artifact-lint`, `checklist-run`, `artifact-review`, `project-audit`, `trace`
- Release: `baseline create`, `baseline diff`, `document-changes`, `change-impact`, `fingerprint-refresh`
- CI: `hook install`, `hook pre-commit`, `ci generate`, `ci-gate`
- Data: `import`, `export`
- Hygiene: `detect dead-code`, `detect similarity`, `renumber-drafts`
- Recovery: `unlock`, `locks`, `rebuild-index`, `split`, `merge`

**Validation Engine**
- Zero-token deterministic validation: schema, links, status, IDs, fingerprints, acceptance, conflicts, coverage, chain depth, quality
- Requirements quality scoring with INCOSE/EARS-based checks (ambiguity, passive voice, missing measurability, compound requirements)
- Artifact lint with `--method programmatic` (CI) and `--method llm` (AI-judged)
- Gate validation for phase transitions

**Traceability**
- V-model traceability: REQ → ARCH → DDD → UT/IT/QT
- Impact analysis with suspect flags and fingerprint-based change detection
- Enhanced trace command with chain depth reporting
- Coverage metrics: REQ coverage, story test coverage, chain completeness

**Compliance**
- Standards pack architecture with gap analysis
- ReqIF 1.2 import/export for supply-chain interchange (deterministic UUIDs)
- Immutable baselines with diff comparison
- LLM-assisted pack authoring from PDF, URL, or pasted text

**Team & Enterprise**
- Git-based RBAC with CODEOWNERS integration
- Pre-commit hooks for status transition validation
- CI gate for server-side RBAC checks
- Defect lifecycle with prevention pattern extraction
- Draft ID renumbering with cross-repo reference rewriting
- GitHub Actions CI workflow generation

**Intelligence**
- 3-tier deduplication: tag Jaccard + TF-IDF + LLM similarity
- Dead-code detection (AST-based) and similarity detection (token-based)
- Adversarial review techniques: devil's advocate, premortem, assumption surfacing, red/blue team
- V-model test stub generation with acceptance criteria extraction
- Artifact split and merge operations
- Phase closure with learned pattern extraction

**Platform Support**
- 14 AI coding platforms: Claude Code, Cursor, Windsurf, Cline, Gemini CLI, OpenCode, GitHub Copilot, Roo Code, QwenCoder, Kiro, KiloCoder, Codex, Trae, Junie
- Platform auto-detection during init
- Progressive disclosure skill architecture (SKILL.md + references/ + scripts/)

**Documentation**
- Getting started guide, lifecycle overview, command reference, CLI reference
- Architecture design reference, design decisions log
- Team setup guide, pack authoring guide, adapter authoring guide
- Skill standards document

### Changed
- Removed 8 deprecated CLI aliases in favor of unified subcommand structure
- Unified skill templates across all platforms
- Rewrote documentation for public-readiness

[1.6.4]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.6.4
[1.5.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.5.0
[1.4.1]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.4.1
[1.4.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.4.0
[1.3.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.3.0
[1.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.2.0
[1.1.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.1.0
[1.0.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v1.0.0
[0.2.0]: https://github.com/Longhuiberkeley/specflow/releases/tag/v0.2.0
