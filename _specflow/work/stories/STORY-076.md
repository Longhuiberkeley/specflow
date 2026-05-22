---
id: STORY-076
title: Improve autoresearch EXPT logging, COMP objectives, and domain-aware checks
type: story
status: draft
priority: high
tags:
- autoresearch
- wave-4
- schema
- protocol
- logging
- domain-awareness
suspect: false
links:
- target: REQ-035
  role: implements
created: '2026-05-22'
---

# Improve autoresearch EXPT logging, COMP objectives, and domain-aware checks

## Outcome

The autoresearch pack supports richer experiment logging, flexible competition objectives, pre/post experiment checks, and domain-aware lint warnings. Users in quant, ML, NLP, and safety-critical domains get structured artifact fields and skill protocol guidance that matches their domain's needs.

## Acceptance criteria

1. All four autoresearch schemas are extended with new fields (objective_type, domain, goals, parameters, model_origin, sweep_results, checks, diversity_metrics, failure_analysis, termination_suggestions, deployability, safety_assessment)
2. All four skill reference documents are updated with new phases, logging requirements, domain-specific recommendations, and `family_of_good` mode behavior
3. `specflow autoresearch review` warns on missing FINDs, missing parameters, missing failure_analysis, and missing domain-recommended auxiliary metrics
4. `specflow autoresearch leaderboard` supports grouping by `model_origin` and showing family-of-good views
5. `specflow artifact-lint` warns on autoresearch logging gaps via a new `_check_autoresearch_logging` check
6. `tests/test_autoresearch_pack.py` covers all new schema fields and enforcement behaviors
7. All existing tests continue to pass
8. ROADMAP.md documents v1.6.1 with this feature set
9. `specflow create`/`update` accept a repeatable, JSON-aware `--set KEY=VALUE` flag, and all four skill protocols use `--set` for non-core fields so the documented loop runs from the CLI (COMP creates also use `--status active`)
10. `experiment.yaml` carries `hypothesis`/`hypothesis_outcome`; Phase 2 ideation is goal-driven and findings record honest (falsified/conditional/sensitive/inconclusive) outcomes
11. CLI-path tests exercise `create`/`update --set` round-trip and leaderboard `--group-by`/`--show-family` parsing (not just direct file writes)

## Subsystem references

- `src/specflow/packs/autoresearch/schemas/{competition,experiment,loop,finding}.yaml`
- `src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md`
- `src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/{autonomous-loop-protocol,competition-setup-protocol,explore-exploit-protocol,finding-generation-protocol}.md`
- `src/specflow/cli.py` (`--set` on create/update; leaderboard `--group-by`/`--show-family`)
- `src/specflow/commands/{create,update,autoresearch}.py`
- `src/specflow/lib/artifacts.py` (`parse_set_fields`)
- `src/specflow/commands/artifact_lint.py`
- `tests/test_autoresearch_pack.py`
