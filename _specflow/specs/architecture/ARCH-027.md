---
id: ARCH-027
title: "Autoresearch pack \u2014 schema-driven capability surface"
type: architecture
status: implemented
priority: high
rationale: 'Refines REQ-AUTORESE-d684 and REQ-035: both requirements refine the same
  opt-in autoresearch pack architecture (schema-as-contract, CLI subcommands, harness-agnostic
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
- target: REQ-AUTORESE-d684
  role: derives_from
- target: REQ-035
  role: derives_from
- target: ARCH-022
  role: derives_from
- target: ARCH-023
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:a4cf4564638d
---

# Autoresearch pack — schema-driven capability surface

Refines REQ-AUTORESE-d684 (pack v0.2.0: multi-criteria, CLI subcommand,
harness-agnosticism) and REQ-035 (enhanced logging, objectives, domain-aware
checks). Both requirements refine the SAME pack architecture, so one ARCH
records it. This is a retroactive design record of capability already shipped
across the v0.2.0 and enhanced-logging cycles; it does not authorize new work.

## Context

The autoresearch pack (`src/specflow/packs/autoresearch/`) is an opt-in
capability applied via `specflow init --with-pack autoresearch`. Its
architecture rests on four pillars, each addressed by both REQs:

1. **Schema-as-contract.** Four YAML schemas (`competition.yaml`,
   `loop.yaml`, `experiment.yaml`, `finding.yaml`) declare the structured
   fields. v0.2.0 added `auxiliary_metrics` (multi-criteria logging); the
   enhanced-logging cycle added `objective_type`, `success_criteria`,
   `parameters`, `model_origin`, `sweep_results`, `checks`, `noise_characterization`,
   `goals`, `hypothesis`/`hypothesis_outcome`, etc. The schema is the single
   source of truth — the CLI, lint, and protocols all read from it.

2. **CLI subcommands as the deterministic backend.** `specflow autoresearch
   plan|run|review|leaderboard` (commands/autoresearch.py) are the deterministic
   mutation/query surface. The SKILL references these backends rather than
   inlining protocol prose, so behavior is reproducible without the AI layer.

3. **Harness-agnostic context injection.** `pack.yaml.context_snippet` is
   injected into per-platform instruction files by `inject_pack_context()` with
   idempotent sentinel markers; `platforms.yaml.instruction_file` names each
   host's instruction path. The same pack installs identically across
   Claude/Codex/OpenCode/… host conventions.

4. **Generic frontmatter write + domain-aware lint.** The `--set KEY=VALUE`
   flag on `create`/`update` writes arbitrary schema-validated frontmatter —
   this is the mechanism the protocols use to populate the structured fields
   from the CLI (without it the documented loop cannot run). `_check_autoresearch_logging`
   (artifact_lint) reads the schema back and warns when a kept EXPT under a
   domain-tagged COMP is missing domain-recommended auxiliary metrics, or when
   a discarded EXPT lacks `failure_analysis`.

## Architecture

```
pack.yaml (manifest: adds_artifact_types, adds_skills, context_snippet)
  ├── schemas/  ──┐  (single source of truth for fields)
  ├── skills/    │
  │   └── specflow-autoresearch/SKILL.md + references/*.md (protocols)
  └── platforms.yaml.instruction_file  ── harness-agnostic install target
        │
        ▼  inject_pack_context() [idempotent sentinels]
  per-host instruction file
        │
core CLI: specflow autoresearch plan|run|review|leaderboard
        │  uses --set KEY=VALUE to write schema fields
        ▼
  COMP / LOOP / EXPT / FIND artifacts (four-tier hierarchy, ARCH-023)
        │
        ▼  read-back
  artifact-lint._check_autoresearch_logging (domain-aware warnings)
```

The multi-objective model lives in the schema, not the engine: `objective_type`
(single | family_of_good | pareto) + `diversity_metrics` lets `explore-exploit-protocol`
prefer uncorrelated keeps without a separate code path; the leaderboard's
`--group-by model_origin` / `--show-family` are read-only views over the same
fields. Goal-driven termination reads `goals`/`termination_suggestions` from
`loop.yaml`; pre/post-checks (`pre_check_command`/`post_check_command`) are
documented as derived from `goals`/`success_criteria`.

## Responsibility

- **Pack manifest + context injection** satisfy REQ-AUTORESE-d684 ACs 6–8
  (SKILL references CLI backends; `context_snippet` + idempotent injection;
  `platforms.yaml.instruction_file`).
- **CLI subcommand tree** satisfies AC 5 (plan|run|review|leaderboard, multi-COMP
  via `--competition`/`--all`).
- **Schema extensibility + `--set` writer + domain-aware lint** satisfy REQ-035
  (schema extensions, protocol updates, CLI enforcement, goal-driven quality).
- **`auxiliary_metrics` + multi-criteria docs** satisfy REQ-AUTORESE-d684 ACs 1–4.

## Options considered

- **Core plugin, not a pack.** Rejected — would change the default experience
  for non-research projects and forgo the harness-agnostic install path
  (ARCH-022 establishes the pack-as-boundary decision).
- **Protocol inlined in the SKILL.** Rejected — non-reproducible across hosts;
  the CLI backend keeps behavior deterministic and testable (REQ-AUTORESE-d684 AC 6).

## Verification

- `tests/test_autoresearch_pack.py` covers schema fields, the CLI subcommand
  tree, context injection idempotency, and the domain-aware lint warnings.
- `_check_autoresearch_logging` is exercised via `artifact-lint --method programmatic`.
