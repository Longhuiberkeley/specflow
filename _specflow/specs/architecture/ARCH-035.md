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
fingerprint: sha256:d9570f45e353
modified: '2026-10-08'
thinking_techniques:
- premortem
- dependency_shock
---

# Practice spine: BP anatomy, provenance, lifecycle, and deterministic validation

## Responsibility
Own the best-practice data model: the five-section anatomy (Practice / Applies when / Work products / Verification / Rationale), optional provenance (bundled | standard | synthesized | learned), source, confidence, strength, applicability, tailoring, verification_method; the collapsed status lifecycle with the transitional map; seed practices; and the practices validate / practices migrate / practices seed CLI surface (handbook generate kept as a deprecated alias).

## Public interface
- lib/practices.py: anatomy rendering, applicability matching (circumstance and lifecycle moment before tag fallback), supersession lineage walk
- lib/practices_seed.py: stable SEED-<domain>-NN entries with applicability predicates
- commands/practices.py: validate, migrate (--dry-run, idempotent, folded into refresh/init/apply_pack), seed
- load_active_best_practices rewrite lives here; consumers (checklists, ci, brief) keep their signatures

## Dependencies
Downstream of artifact schema loading; upstream of guidance application (ARCH-034), profile (later increment), and all skill surfaces. No LLM inference anywhere in this component.

## Data flow
best-practice.yaml schema -> create/update -> practices validate (anatomy, taxonomy, provenance resolvability, lineage) -> practices migrate stamps provenance on legacy BPs -> applicability-first loader feeds checklists/ci/brief.
