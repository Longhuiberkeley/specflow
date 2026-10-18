---
id: ARCH-027
title: "Autoresearch pack \u2014 schema-driven capability surface"
type: architecture
status: implemented
priority: high
rationale: 'Refines REQ-062 and REQ-035: both requirements refine the same opt-in
  autoresearch pack architecture (schema-as-contract, CLI subcommands, harness-agnostic
  context injection, generic frontmatter writer + domain-aware lint). Retroactive
  design record of shipped capability; no new work authorized.'
tags:
- autoresearch
- architecture
- pack
- multi-criteria
- domain-aware
suspect: false
links:
- target: REQ-062
  role: derives_from
- target: REQ-035
  role: derives_from
- target: ARCH-022
  role: derives_from
- target: ARCH-023
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:f4857c69172a
thinking_techniques:
- assumption_surfacing
modified: '2026-10-08'
version: 3
---

# Autoresearch pack — schema-driven capability surface

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-109); earlier text described a four-subcommand tree (plan|run|review|leaderboard), a `--with-pack` install flag and `goals` on loop.yaml.

Refines REQ-062 (pack v0.2.0: multi-criteria, CLI subcommand,
harness-agnosticism) and REQ-035 (enhanced logging, objectives, domain-aware
checks). Both requirements refine the SAME pack architecture, so one ARCH
records it. This is a retroactive design record of capability already shipped
across the v0.2.0 and enhanced-logging cycles (the pack manifest is now at
version 0.4.0); it does not authorize new work.

## Context

The autoresearch pack (`src/specflow/packs/autoresearch/`) is an opt-in
capability applied via `specflow init --preset autoresearch`
(`scaffold.apply_pack`). Its architecture rests on four pillars, each
addressed by both REQs:

1. **Schema-as-contract.** Four YAML schemas (`competition.yaml`,
   `loop.yaml`, `experiment.yaml`, `finding.yaml`) declare the structured
   fields. v0.2.0 added `auxiliary_metrics` (multi-criteria logging); the
   enhanced-logging cycle added COMP `objective_type`, `success_criteria`,
   `noise_characterization`, `goals`; EXPT `parameters`, `model_origin`,
   `sweep_results`, `checks`, `hypothesis`/`hypothesis_outcome`, etc. The
   schema is the single source of truth — the CLI, lint, and protocols all
   read from it.

2. **CLI subcommands as the deterministic backend.** `specflow autoresearch
   plan|run|status|frontier|review|leaderboard|log|suggest-finds`
   (`commands/autoresearch.py`, parser in `cli.py:_add_autoresearch_parser`)
   is the deterministic mutation/query surface: `plan` creates or updates a
   LOOP, `run` prints the loop protocol (starting a draft LOOP), `log` writes
   an EXPT and updates LOOP counters, `suggest-finds` drafts FINDs from a
   completed LOOP, and `status` (readiness and closure accounting, see
   ARCH-031), `frontier` (research-frontier ledger), `review` and
   `leaderboard` are read-only. The SKILL references these backends rather
   than inlining protocol prose, so behavior is reproducible without the AI
   layer.

3. **Harness-agnostic context injection.** `pack.yaml` `context_snippet` is
   injected into per-platform instruction files by
   `inject_pack_context(root, pack_name, context_snippet, explicit_platform=None)`
   (`lib/scaffold.py`) with idempotent sentinel markers; the
   `instruction_file` key in `src/specflow/templates/platforms.yaml` names
   each host's instruction path. The same pack installs identically across
   Claude/Codex/OpenCode/… host conventions.

4. **Generic frontmatter write + domain-aware lint.** The `--set KEY=VALUE`
   flag on `create`/`update` (and on `autoresearch log`) writes arbitrary
   schema-validated frontmatter — this is the mechanism the protocols use to
   populate the structured fields from the CLI (without it the documented loop
   cannot run). `_check_autoresearch_logging` (artifact_lint) reads the schema
   back and warns when a kept EXPT under a domain-tagged COMP is missing
   domain-recommended auxiliary metrics, when a discarded or crashed EXPT
   lacks `failure_analysis`, when a kept model/params EXPT lacks `parameters`,
   or when a non-draft EXPT lacks a falsifiable `hypothesis` (and, if kept, its
   `hypothesis_outcome`). `lint.autoresearch_logging_strict: true` in config
   escalates these to blocking.

## Architecture

```
pack.yaml (manifest: adds_artifact_types, adds_directories, adds_skills, context_snippet)
  ├── schemas/  ──┐  (single source of truth for fields)
  ├── skills/    │
  │   └── specflow-autoresearch/SKILL.md + references/*.md (protocols)
  └── templates/platforms.yaml instruction_file  ── harness-agnostic install target
        │
        ▼  scaffold.inject_pack_context() [idempotent sentinels]
  per-host instruction file
        │
core CLI: specflow autoresearch plan|run|status|frontier|review|leaderboard|log|suggest-finds
        │  uses --set KEY=VALUE to write schema fields
        ▼
  COMP / LOOP / EXPT / FIND artifacts (four-tier hierarchy, ARCH-023)
        │
        ▼  read-back
  artifact-lint._check_autoresearch_logging (domain-aware warnings)
```

The multi-objective model lives in the schema and protocols, not the engine:
COMP `objective_type` (single | family_of_good | pareto) + EXPT
`diversity_metrics` lets `explore-exploit-protocol` prefer uncorrelated keeps
without a separate code path; the leaderboard's `--group-by`
(model_origin | change_category | strategy_family | loop) and `--show-family`
(groups by `model_origin`) are read-only views over the same fields.
Goal-driven termination reads COMP `goals` and LOOP `termination_suggestions`;
COMP pre/post-checks (`pre_check_command`/`post_check_command`) are documented
in `competition-setup-protocol.md` as derived from the goals.

## Responsibility

- **Pack manifest + context injection** satisfy REQ-062 ACs 6–8
  (SKILL references CLI backends; `context_snippet` + idempotent injection;
  `platforms.yaml` `instruction_file`).
- **CLI subcommand tree** satisfies AC 5 (plan|run|review|leaderboard, multi-COMP
  via `--competition`/`--all`); `status`, `frontier`, `log` and
  `suggest-finds` extend the same tree.
- **Schema extensibility + `--set` writer + domain-aware lint** satisfy REQ-035
  (schema extensions, protocol updates, CLI enforcement, goal-driven quality).
- **`auxiliary_metrics` + multi-criteria docs** satisfy REQ-062 ACs 1–4.

## Options considered

- **Core plugin, not a pack.** Rejected — would change the default experience
  for non-research projects and forgo the harness-agnostic install path
  (ARCH-022 establishes the pack-as-boundary decision).
- **Protocol inlined in the SKILL.** Rejected — non-reproducible across hosts;
  the CLI backend keeps behavior deterministic and testable (REQ-062 AC 6).

## Verification

- `tests/test_autoresearch_pack.py` covers schema fields and transition maps,
  pack install (`apply_pack`, including the returned `context_snippet`), the
  CLI subcommand tree, the research trace views, and the logging lint
  warnings; `tests/test_autoresearch_cli.py`, `tests/test_autoresearch_schema.py`
  and `tests/test_autoresearch_skill_text.py` cover the CLI, schema and skill
  text further.
- `_check_autoresearch_logging` is exercised via
  `specflow artifact-lint --type autoresearch-logging`.
