---
id: ARCH-035
title: 'Practice spine: BP anatomy, provenance, lifecycle, and deterministic validation'
type: architecture
status: implemented
suspect: false
links:
- target: REQ-044
  role: derives_from
- target: DEC-085
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:4085389f4cc1
modified: '2026-10-08'
thinking_techniques:
- premortem
- dependency_shock
version: 2
---

# Practice spine: BP anatomy, provenance, lifecycle, and deterministic validation

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-111); earlier text cross-referenced ARCH-034 for guidance application (it is ARCH-036) and listed brief as a `load_active_best_practices` consumer.

## Responsibility
Own the best-practice data model: the five-section anatomy (`PRACTICE_SECTIONS`: Practice / Applies when / Work products / Verification / Rationale), optional provenance (`PROVENANCE_VALUES`: bundled | standard | synthesized | learned), source, confidence, strength, applicability, tailoring, verification_method; the collapsed status lifecycle (`best-practice.yaml`: draft → approved → superseded, with legacy `active` kept as a transitional predecessor, and `_repair_legacy_bp_status_map` replacing the exact pre-collapse map); seed practices; and the `specflow practices validate` / `practices migrate` / `practices seed` CLI surface (`handbook generate` kept as a deprecated alias that delegates to `practices seed`).

## Public interface
- lib/practices.py: `render_practice_body` / `validate_anatomy` (anatomy), `applicability_matches` (applicability predicate over domains, tags, artifact_types and moments, before the legacy applies_to/tag fallback), `validate_practices` (anatomy, taxonomy, provenance resolvability, `supersedes` lineage), `migrate_practices(root, *, dry_run=False)`, `in_scope_bindings`
- lib/practices_seed.py: stable `SEED-<DOMAIN>-NN` entries (e.g. `SEED-GENERIC-01`; 6 generic plus 3 for each of 8 domains) with applicability predicates; `generate_handbook(root)`, `get_practices(domain)`
- commands/practices.py: validate, migrate (`--dry-run`, idempotent, also run by `refresh`, `init` and pack apply in lib/scaffold.py), seed (`--create`, `--verbose`)
- `load_active_best_practices(root, artifact)` and its pure counterpart `applicable_best_practices` live in lib/practices.py; `lib/ci.py` keeps a same-signature wrapper that checklists and artifact-review call, and brief and the bp-application lint read `in_scope_bindings`

## Dependencies
Downstream of artifact schema loading; upstream of guidance application (ARCH-036), profile (later increment), and all skill surfaces. No LLM inference anywhere in this component.

## Data flow
best-practice.yaml schema -> create/update -> practices validate (anatomy, taxonomy, provenance resolvability, lineage) -> practices migrate stamps provenance on legacy BPs -> applicability-first loader feeds checklists and artifact-review (via lib/ci.py), while brief and bp-application lint read `in_scope_bindings`.
