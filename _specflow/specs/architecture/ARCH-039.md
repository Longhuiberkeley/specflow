---
id: ARCH-039
title: Core ontology, fact model and graph views
type: architecture
status: draft
tags:
- ontology
- core
suspect: false
links:
- target: REQ-052
  role: derives_from
- target: REQ-053
  role: derives_from
- target: REQ-054
  role: derives_from
- target: DEC-090
  role: guided_by
- target: BP-003
  role: guided_by
- target: BP-004
  role: guided_by
- target: BP-005
  role: guided_by
- target: BP-006
  role: guided_by
- target: BP-007
  role: guided_by
created: '2026-09-30'
thinking_techniques:
- assumption_surfacing
- premortem
- devils_advocate
fingerprint: sha256:54ef276c8143
modified: '2026-10-08'
---

# Core ontology, fact model and graph views

## Responsibility
Own SpecFlow's semantics in one place. `core/ontology.yaml` declares types, kinds, lifecycles, roles with a single orientation, the role-target matrix and normative fields; `core/ontology.py` compiles it with consumer schema overlays and pack schemas into a frozen registry that fails loud on conflict; `core/facts.py` turns artifacts and explicit environment inputs into a typed FactSet; `core/graph.py` builds one adjacency index per invocation with read-time canonical edges (both `verified_by` spellings become `verifies(Test, Subject)`; `REQ refined_by ARCH` and `ARCH derives_from REQ` become `refines(ARCH, REQ)`), closure, acyclicity and true longest-path chain depth; `core/views.py` defines every named view once; `core/findings.py` and `core/policy.py` make findings typed and exit codes a pure function of findings plus the committed findings baseline; `core/explain.py` renders derivations (`why`) and missing premises (`why-not`).

## Public interface
- `specflow rules check` (meta-properties of the compiled ontology), `specflow rules diff --against <ref>` (findings delta for a rule or ontology change)
- `specflow facts --json` (read-only FactSet export for differential tests and external tooling)
- `specflow why <finding-id>`, `specflow why-not <view> <ID>`
- Named views consumed by artifact-lint, project-audit, status, rtm, trace and brief: coverage.story_anchored (REQ-012 metric 1), coverage.spec_vpair (REQ-012 metric 2 / REQ-013), coverage.rtm_row, coverage.status_percentages, chain_depth, suspect, approval_stale, verified_contradiction
- Finding(rule_id, subjects, severity, klass, args, derivation) with byte-identical rendering for existing rule ids

## Constraints
- Zero new runtime dependencies (pyyaml only); no file moves, prefix renames or fingerprint algorithm changes; the D-18 surface link vocabulary stays frozen and is canonicalised at read time only.
- Environment inputs (clock, filesystem, git, lint history) enter only as explicit facts.
- Heuristic checks (text quality regexes, AC observability, dedup similarity, numeric conflicts) are extern fact producers; they never decide exit codes.
- A Datalog rule layer (`core/datalog.py`, `rules/*.dl`) is built only if the REQ-055 pilot shows packs need user-authored quantified rules.

## Anti-drift guards
- `tests/test_ontology_equivalence.py`: derived tables equal the old literals until the literals are deleted, then a round-trip test.
- `tests/test_no_ontology_literals.py`: architecture test with a shrink-only allowlist.
- `tests/test_ontology_meta.py`: reachability, entry state, one orientation per role, declared targets, no pack redefinition of core roles.
- Golden findings snapshot over the dogfood corpus; Hypothesis order-independence and idempotence tests.

## Migration order
P2 registry and guards → P3 typed findings, explicit inputs, findings-baseline ratchet → P4 one graph, named views, why/why-not, new accounting invariants → P5 approval and link stamps with derived suspect. Each phase is additive and independently releasable.
