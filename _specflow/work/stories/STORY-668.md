---
id: STORY-668
title: Practices validate, practices migrate, applicability-first loader (REQ-044)
type: story
status: implemented
suspect: false
links:
- target: REQ-044
  role: implements
- target: ARCH-035
  role: guided_by
- target: DDD-032
  role: specified_by
created: '2026-09-25'
fingerprint: sha256:87a1e6ff20fc
thinking_techniques:
- premortem
- dependency_shock
- worst_case_user
- composition
modified: '2026-10-08'
---

# Practices validate, practices migrate, applicability-first loader (REQ-044)

## Story
Ship the practices CLI: validate (anatomy, verification-method taxonomy, provenance resolvability, supersession lineage — deterministic), migrate (idempotent provenance stamping, --dry-run writes nothing, folded into refresh/init/apply_pack), and the applicability-first rewrite of load_active_best_practices. Completes the DEC-089 coupling with STORY-666: loader rewrite and status map ship together.

## Acceptance Criteria
1. Given valid and malformed BPs, when practices validate runs, then failures are deterministic with file-and-reason output and no network or model calls.
2. Given legacy BPs without provenance, when practices migrate runs twice, then the second run changes nothing and --dry-run leaves the tree untouched.
3. Given BPs with applicability and tag-only BPs, when the loader runs, then applicability matches first, tags fall back, and legacy resolution is equivalent to the old path on the dogfood set.
